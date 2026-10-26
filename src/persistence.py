"""Per-user launcher registration; no services, elevation or machine settings."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
RUN_NAME = 'DiscordUnbound'


def read(state):
    path = Path(state) / 'managed.json'
    if not path.exists():
        return {'schema': 1, 'roots': {}, 'run': None}
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema') != 1 or not isinstance(value.get('roots'), dict):
        raise RuntimeError('Unsupported launcher registration')
    return value


def save(state, value):
    state = Path(state)
    state.mkdir(parents=True, exist_ok=True)
    from patcher import _atomic, _json
    _atomic(state / 'managed.json', _json(value))


def key(root):
    return str(Path(root).resolve()).casefold()


def durable_runner(state):
    """Content-addressed copies survive ZIP-folder removal and EXE updates."""
    if getattr(sys, 'frozen', False):
        source = Path(sys.executable)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()[:20]
        target = Path(state) / 'launcher' / digest / 'DiscordUnbound.exe'
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
        if hashlib.sha256(target.read_bytes()).hexdigest()[:20] != digest:
            raise RuntimeError('Stored launcher integrity mismatch')
        return [str(target)]
    sources = sorted(p for p in Path(__file__).parent.iterdir() if p.suffix in ('.py', '.cjs'))
    digest = hashlib.sha256(b''.join(p.name.encode() + p.read_bytes() for p in sources)).hexdigest()[:20]
    folder = Path(state) / 'launcher' / digest
    folder.mkdir(parents=True, exist_ok=True)
    for source in sources:
        target = folder / source.name
        if not target.exists():
            shutil.copy2(source, target)
        if target.read_bytes() != source.read_bytes():
            raise RuntimeError('Stored launcher source mismatch')
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    return [str(pythonw if pythonw.exists() else Path(sys.executable)), str(folder / 'app.py')]


def get_run(name):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as handle:
        try:
            value, kind = winreg.QueryValueEx(handle, name)
            return {'value': value, 'kind': kind}
        except FileNotFoundError:
            return None


def set_run(name, value):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as handle:
        if value is None:
            try:
                winreg.DeleteValue(handle, name)
            except FileNotFoundError:
                pass
        else:
            winreg.SetValueEx(handle, name, 0, value['kind'], value['value'])


def _string(command):
    return {'value': subprocess.list2cmdline(command), 'kind': 1}


def enable(state, root):
    root = Path(root).resolve()
    if root.name not in ('Discord', 'DiscordCanary', 'DiscordPTB'):
        raise RuntimeError('Unsupported Discord channel root')
    value = read(state)
    runner = durable_runner(state)
    resume = _string(runner + ['--resume'])
    previous = get_run(RUN_NAME)
    owned = value.get('run')
    if previous and (not owned or previous != owned['installed']):
        raise RuntimeError('DiscordUnbound startup entry belongs to another installation')
    if not owned:
        value['run'] = {'previous': previous, 'installed': resume}
    else:
        value['run']['installed'] = resume
    identity = key(root)
    entry = value['roots'].get(identity, {'root': str(root), 'startup': None})
    # Preserve Discord's existing startup preference; route it through preparation.
    existing = get_run(root.name)
    prior = entry.get('startup')
    startup_update = False
    if existing and ((prior and existing == prior['installed']) or
                     (not prior and str(root / 'Update.exe').casefold() in existing['value'].casefold())):
        command = _string(runner + ['--managed-root', str(root)])
        entry['startup'] = {'previous': prior['previous'] if prior else existing, 'installed': command}
        startup_update = True
    entry['runner'] = runner
    value['roots'][identity] = entry
    # Journal before registry mutation, so interrupted installs retain recovery data.
    save(state, value)
    set_run(RUN_NAME, resume)
    if startup_update:
        set_run(root.name, entry['startup']['installed'])
    return runner


def disable(state, root):
    value = read(state)
    entry = value['roots'].pop(key(root), None)
    if entry and entry.get('startup'):
        saved = entry['startup']
        if get_run(Path(root).name) == saved['installed']:
            set_run(Path(root).name, saved['previous'])
    if not value['roots'] and value.get('run'):
        saved = value['run']
        if get_run(RUN_NAME) == saved['installed']:
            set_run(RUN_NAME, saved['previous'])
        value['run'] = None
    save(state, value)


def spawn(command):
    env = os.environ.copy()
    if getattr(sys, 'frozen', False):
        env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    return subprocess.Popen(command, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                            close_fds=True, env=env)
