"""Bundle the checksum-pinned official JavaScript runtime and its notices."""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildEdge(build_py):
    def run(self):
        super().run()
        pin = json.loads(Path("upstream.json").read_text(encoding="utf-8"))
        archive = os.environ.get("CODEX_EDGE_MCP_ARCHIVE")
        if archive:
            data = Path(archive).read_bytes()
        else:
            with urllib.request.urlopen(pin["url"], timeout=60) as response:
                data = response.read(10_000_001)
        if len(data) > 10_000_000 or hashlib.sha256(data).hexdigest() != pin["sha256"]:
            raise ValueError("Official Edge MCP runtime checksum mismatch")
        target = Path(self.build_lib) / "edge_devtools_mcp"
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as package:
            metadata = json.loads(package.extractfile("package/package.json").read())
            if metadata["name"] != pin["name"] or metadata["version"] != pin["version"] or metadata.get("dependencies"):
                raise ValueError("Unexpected upstream runtime metadata or dependencies")
            for member in package.getmembers():
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts or "\\" in member.name or not path.parts or path.parts[0] != "package" or not (member.isfile() or member.isdir()):
                    raise ValueError("Unsafe official runtime archive member")
                if member.size > 30_000_000:
                    raise ValueError("Official runtime member exceeds the size limit")
            package.getmember("package/build/src/bin/chrome-devtools-mcp.js")
            (target / "THIRD_PARTY_LICENSE").write_bytes(package.extractfile("package/LICENSE").read())
            (target / "THIRD_PARTY_NOTICES").write_bytes(package.extractfile("package/build/src/third_party/THIRD_PARTY_NOTICES").read())
        (target / "runtime.tgz").write_bytes(data)
        (target / "upstream.json").write_text(json.dumps(pin, indent=2) + "\n", encoding="utf-8")


setup(cmdclass={"build_py": BuildEdge})
