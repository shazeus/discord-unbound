"""Opt-in browser access worker and independent Windows crash recovery guard."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import secrets
import subprocess
import threading
import time
from urllib.request import Request, build_opener, ProxyHandler
from proxy_settings import WindowsProxy, atomic_json, active_settings, restore_owned
from web_proxy import LocalProxy, compose_pac, previous_script

STATE = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'DiscordUnbound'
JOURNAL = STATE / 'web-state.json'


def load():
    try:
        data = json.loads(JOURNAL.read_text(encoding='utf-8'))
        if data.get('schema') != 1: raise ValueError('Web erişimi durum şeması geçersiz.')
        return data
    except FileNotFoundError: return None


def kernel():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]; k.OpenProcess.restype = wintypes.HANDLE
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]; k.WaitForSingleObject.restype = wintypes.DWORD
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    return k


def alive(pid):
    if type(pid) is not int or pid <= 0: return False
    k = kernel(); handle = k.OpenProcess(0x100000, False, pid)
    if not handle: return False
    try: return k.WaitForSingleObject(handle, 0) == 258
    finally: k.CloseHandle(handle)


def direct_request(url, method='GET'):
    request = Request(url, method=method)
    with build_opener(ProxyHandler({})).open(request, timeout=3) as response:
        return response.read(65536)


def status():
    state = load()
    if not state: return {'active': False, 'phase': 'inactive'}
    active = state['phase'] == 'active' and alive(state['pid'])
    result = {'active': active, 'phase': state['phase'], 'mode': state.get('mode'), 'port': state.get('port')}
    if active:
        try:
            result['counters'] = json.loads(direct_request(state['control'] + '/status'))
            result['owns_settings'] = WindowsProxy().read()['url'] == state['installed']['url']
        except (OSError, ValueError): result['active'] = False
    return result


def recover(state, backend=None):
    backend = backend or WindowsProxy()
    if state and state['phase'] in ('preparing', 'active', 'stopping'):
        result = restore_owned(backend, state['previous'], state['installed'])
        state = {**state, 'phase': 'inactive', 'restoration': result}
        atomic_json(JOURNAL, state)
        return result
    return 'already_inactive'


def child(command):
    env = os.environ.copy(); env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    return subprocess.Popen(command, env=env, creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)


def start(runner):
    current = load()
    if current and current['phase'] == 'active' and alive(current['pid']): return status()
    if current and not alive(current.get('pid')): recover(current)
    worker = child([*runner, '--web-worker'])
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        state = load()
        if state and state['phase'] == 'active' and alive(state['pid']): return status()
        if worker.poll() is not None:
            if state and state.get('error'): raise RuntimeError(state['error'])
            raise RuntimeError('Web yardımcısı başlatılamadı; proxy ayarları korunuyor.')
        time.sleep(.1)
    raise RuntimeError('Web yardımcısı hazırlanıyor; durumunu yeniden kontrol edin.')


def stop():
    state = load()
    if not state: return {'active': False, 'phase': 'inactive'}
    if alive(state.get('pid')) and state['phase'] == 'active':
        direct_request(state['control'] + '/stop', 'POST')
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            current = load()
            if current['phase'] == 'inactive': return status()
            time.sleep(.1)
        raise RuntimeError('Web yardımcısı kapanıyor; durumunu yeniden kontrol edin.')
    if not alive(state.get('pid')): recover(state)
    return status()


def guard(pid):
    state = load()
    if not state or state['pid'] != pid: return
    k = kernel(); handle = k.OpenProcess(0x100000, False, pid)
    if not handle: recover(state); return
    ready = STATE / ('guard-' + state['token'] + '.ready')
    try:
        atomic_json(ready, {'pid': os.getpid()})
        k.WaitForSingleObject(handle, 0xffffffff)
        latest = load()
        if latest and latest.get('token') == state['token']: recover(latest)
    finally:
        k.CloseHandle(handle); ready.unlink(missing_ok=True)


def worker(runner):
    k = kernel()
    k.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]; k.CreateMutexW.restype = wintypes.HANDLE
    mutex = k.CreateMutexW(None, False, 'Local\\DiscordUnbound.WebAccess.v1')
    if not mutex: raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183: k.CloseHandle(mutex); return
    proxy = None; state = None; backend = WindowsProxy()
    try:
        old = load()
        if old and not alive(old.get('pid')): recover(old, backend)
        previous = backend.read()
        prior, mode = previous_script(previous)
        event = threading.Event(); token = secrets.token_hex(24)
        proxy = LocalProxy(token, event)
        proxy.pac = compose_pac(proxy.port, previous, prior); proxy.start()
        installed = active_settings(previous, proxy.url)
        state = {'schema': 1, 'phase': 'preparing', 'pid': os.getpid(), 'token': token,
                 'port': proxy.port, 'control': 'http://127.0.0.1:' + str(proxy.port) + '/' + token,
                 'previous': previous, 'installed': installed, 'mode': mode}
        atomic_json(JOURNAL, state)
        ready = STATE / ('guard-' + token + '.ready')
        watcher = child([*runner, '--web-guard', str(os.getpid())])
        deadline = time.monotonic() + 8
        while not ready.exists():
            if watcher.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError('Kurtarma gözeticisi hazırlanamadı; ayarlar değiştirilmedi.')
            time.sleep(.05)
        backend.write(installed)
        if backend.read() != installed: raise RuntimeError('Windows proxy ayarı doğrulanamadı.')
        state['phase'] = 'active'; atomic_json(JOURNAL, state)
        event.wait()
    except Exception as exc:
        if state:
            recover(state, backend)
            failed = load(); failed['error'] = str(exc); atomic_json(JOURNAL, failed)
        else:
            atomic_json(JOURNAL, {'schema': 1, 'phase': 'inactive', 'pid': os.getpid(), 'error': str(exc)})
    finally:
        if state: recover(load(), backend)
        if proxy: proxy.close()
        k.CloseHandle(mutex)
