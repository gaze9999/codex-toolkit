"""Bind GUI confirmation to the concrete single-tool plan that was reviewed."""
import hashlib
import json


def plan_sha256(plan):
    # Volatile diagnostics do not authorize changes. Versions, commands, scope,
    # package identity and the registration/config fingerprint do.
    fields = ('tool', 'interface', 'platform', 'steps', 'blocked', 'server',
              'config', 'config_sha256', 'package', 'read_roots', 'feeds_path',
              'mcp_executable', 'wheel_file', 'manual_setup')
    selected = {key: plan[key] for key in fields if key in plan}
    return hashlib.sha256(json.dumps(selected, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode('utf-8')).hexdigest()


def require_same_plan(plan, expected):
    if expected is not None and plan_sha256(plan) != expected:
        raise ValueError('The selected plan changed after preview; review it again before applying')
