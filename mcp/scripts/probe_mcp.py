"""Inspect an explicitly selected MCP without calling its application tools."""
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def probe(server, *, timeout=15):
    if server.get('enabled',True) is False:
        return {'status':'disabled','message':'工具已停用, 未建立連線'}
    init={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'codex-setup-manager','version':'0.3.0'}}}
    if server.get('url'):
        url=urlsplit(server['url'])
        if url.scheme not in {'http','https'} or not url.hostname or url.username or url.password:
            return {'status':'invalid_configuration'}
        headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream',**server.get('http_headers',{})}
        for key,name in server.get('env_http_headers',{}).items():
            if name in os.environ:headers[key]=os.environ[name]
        token=server.get('bearer_token_env_var')
        if token and token in os.environ:headers['Authorization']='Bearer '+os.environ[token]
        try:
            request=urllib.request.Request(server['url'],data=json.dumps(init).encode(),headers=headers,method='POST')
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=timeout) as response:
                data=response.read(65537)
            if len(data)>65536:return {'status':'response_too_large'}
            text=data.decode('utf-8')
            if text.startswith('event:') or text.startswith('data:'):
                messages=[json.loads(line[5:].strip()) for line in text.splitlines() if line.startswith('data:')]
                result=next((item for item in messages if isinstance(item,dict) and item.get('id')==1),{})
            else:result=json.loads(text)
            if not isinstance(result,dict) or not isinstance(result.get('result',{}),dict):return {'status':'protocol_error'}
            value=result.get('result',{})
            return {'status':'connected','protocol':value['protocolVersion'],'transport':'HTTP','checked':'initialize'} if value.get('protocolVersion') else {'status':'protocol_error'}
        except urllib.error.HTTPError as exc:
            status='authorization_required' if exc.code in {401,403} else 'redirect_blocked' if 300<=exc.code<400 else 'http_error'
            return {'status':status,'http_status':exc.code}
        except (OSError,ValueError):return {'status':'connection_failed','message':'無法完成 HTTP initialize, OAuth 請從 Codex 授權後再實際呼叫'}
    command=server.get('command')
    args=server.get('args',[])
    if not isinstance(command,str) or not isinstance(args,list) or not all(isinstance(arg,str) for arg in args):
        return {'status':'invalid_configuration'}
    env=os.environ.copy()
    env.update(server.get('env',{}))
    env.update(PYTHONUTF8='1',JEV_TELEMETRY='0',RTK_TELEMETRY_DISABLED='1')
    process=None
    reader=None
    messages=queue.Queue(maxsize=128)
    try:
        process=subprocess.Popen([command,*args],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env,cwd=server.get('cwd'),shell=False,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0, start_new_session=os.name!='nt')
        def read():
            for line in iter(lambda:process.stdout.readline(65537),b''):
                if len(line)>65536 or messages.full():break
                messages.put(line)
        reader=threading.Thread(target=read,daemon=True);reader.start()
        def rpc(message):process.stdin.write((json.dumps(message)+'\n').encode());process.stdin.flush()
        rpc(init)
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:line=messages.get(timeout=min(.5,max(.01,deadline-time.monotonic())))
            except queue.Empty:
                if process.poll() is not None:break
                continue
            try:response=json.loads(line)
            except ValueError:continue
            if not isinstance(response,dict) or not isinstance(response.get('result',{}),dict):continue
            if response.get('id')==1 and response.get('result',{}).get('protocolVersion'):
                return {'status':'connected','protocol':response['result']['protocolVersion'],'transport':'stdio','checked':'initialize'}
            if response.get('id')==1 and 'error' in response:return {'status':'protocol_error'}
        return {'status':'connection_failed','message':'未在時間內收到 initialize 回覆'}
    except (OSError,ValueError,TypeError):return {'status':'connection_failed','message':'無法啟動選定 server, 請檢查 command 與相依'}
    finally:
        if process:
            # Closing stdin lets stdio servers and venv launchers release their children.
            if process.stdin:
                try:process.stdin.close()
                except OSError:pass
            if process.poll() is None:
                try:process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    if os.name=='nt':
                        taskkill=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/taskkill.exe'
                        subprocess.run([str(taskkill),'/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5,check=False)
                    else:
                        try:os.killpg(process.pid,signal.SIGKILL)
                        except ProcessLookupError:pass
                    if process.poll() is None:process.kill()
                    process.wait(timeout=5)
            if reader:reader.join(timeout=1)
            for stream in (process.stdin,process.stdout):
                if stream:stream.close()
