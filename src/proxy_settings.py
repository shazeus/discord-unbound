"""Current-user WinINet LAN settings, exact snapshots and ownership-aware restore."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import tempfile

KEYS = ('flags', 'server', 'bypass', 'url')


class WindowsProxy:
    def __init__(self):
        if os.name != 'nt': raise RuntimeError('Windows kullanıcı proxy ayarları gerekiyor.')
        class Value(ctypes.Union):
            _fields_ = [('number', wintypes.DWORD), ('pointer', ctypes.c_void_p), ('time', wintypes.FILETIME)]
        class Option(ctypes.Structure):
            _fields_ = [('option', wintypes.DWORD), ('value', Value)]
        class Options(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('connection', ctypes.c_void_p),
                        ('count', wintypes.DWORD), ('error', wintypes.DWORD), ('items', ctypes.POINTER(Option))]
        self.Option, self.Options = Option, Options
        self.api = ctypes.WinDLL('wininet', use_last_error=True)
        self.api.InternetQueryOptionW.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
        self.api.InternetQueryOptionW.restype = wintypes.BOOL
        self.api.InternetSetOptionW.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        self.api.InternetSetOptionW.restype = wintypes.BOOL
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.GlobalFree.argtypes = [ctypes.c_void_p]
        self.kernel.GlobalFree.restype = ctypes.c_void_p

    def read(self):
        items = (self.Option * 4)()
        for i in range(4): items[i].option = i + 1
        values = self.Options(ctypes.sizeof(self.Options), None, 4, 0, items)
        length = wintypes.DWORD(ctypes.sizeof(values))
        if not self.api.InternetQueryOptionW(None, 75, ctypes.byref(values), ctypes.byref(length)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return {'flags': int(items[0].value.number), **{
                key: ctypes.wstring_at(items[i].value.pointer) if items[i].value.pointer else ''
                for i, key in enumerate(KEYS[1:], 1)}}
        finally:
            for item in items[1:]:
                if item.value.pointer: self.kernel.GlobalFree(item.value.pointer)

    def write(self, snapshot):
        if set(snapshot) != set(KEYS) or type(snapshot['flags']) is not int:
            raise ValueError('Geçersiz proxy yedeği.')
        items = (self.Option * 4)()
        buffers = []
        for i, key in enumerate(KEYS):
            items[i].option = i + 1
            if i == 0: items[i].value.number = snapshot[key]
            else:
                if not isinstance(snapshot[key], str): raise ValueError('Geçersiz proxy değeri.')
                buffer = ctypes.create_unicode_buffer(snapshot[key]); buffers.append(buffer)
                items[i].value.pointer = ctypes.cast(buffer, ctypes.c_void_p)
        values = self.Options(ctypes.sizeof(self.Options), None, 4, 0, items)
        if not self.api.InternetSetOptionW(None, 75, ctypes.byref(values), ctypes.sizeof(values)):
            raise ctypes.WinError(ctypes.get_last_error())
        # Notify Windows and proxy-aware applications. Do not alter WinHTTP machine settings.
        for option in (39, 37): self.api.InternetSetOptionW(None, option, None, 0)


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.web-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def active_settings(previous, url):
    # Keep static proxy values intact as fallback. The PAC preserves their behavior.
    return {**previous, 'flags': 1 | 4 | (previous['flags'] & 2), 'url': url}


def restore_owned(backend, previous, installed):
    current = backend.read()
    if current['url'] != installed['url']:
        return 'external_change_preserved'
    # Only fields this utility changed are restored. A new manual proxy configured
    # by another app while Unbound runs is never overwritten.
    restored = {**current, 'url': previous['url']}
    if current['flags'] == installed['flags']: restored['flags'] = previous['flags']
    backend.write(restored)
    return 'restored'
