"""DiscordUnbound experimental Windows launcher. No third party runtime dependencies."""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

HERE = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
STATE = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'DiscordUnbound'
STATE.mkdir(parents=True, exist_ok=True)


def discord_processes():
    """Get executable paths without command lines, account data or tokens."""
    if os.name != 'nt':
        return []
    class ENTRY(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_size_t),
                    ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG),
                    ('dwFlags', wintypes.DWORD), ('szExeFile', wintypes.WCHAR * 260)]
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k.Process32FirstW.argtypes = k.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ENTRY)]
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.OpenProcess.restype = wintypes.HANDLE
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    snapshot = k.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise OSError('Islem listesi okunamadi; guvenli yama uygulanmadi.')
    result = []
    try:
        e = ENTRY(); e.dwSize = ctypes.sizeof(e)
        more = k.Process32FirstW(snapshot, ctypes.byref(e))
        while more:
            if e.szExeFile.lower() in ('discord.exe', 'discordcanary.exe', 'discordptb.exe'):
                handle = k.OpenProcess(0x1000, False, e.th32ProcessID)
                path = None
                if handle:
                    try:
                        buf = ctypes.create_unicode_buffer(32768); length = wintypes.DWORD(len(buf))
                        if k.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(length)):
                            path = buf.value
                    finally:
                        k.CloseHandle(handle)
                result.append({'pid': e.th32ProcessID, 'path': path})
            more = k.Process32NextW(snapshot, ctypes.byref(e))
    finally:
        k.CloseHandle(snapshot)
    return result


def assert_closed(asar):
    app_dir = Path(asar).parent.parent.resolve()
    for proc in discord_processes():
        if proc['path'] is None or Path(proc['path']).resolve().parent == app_dir:
            raise RuntimeError('Bu Discord surumu acik. Tepsi simgesinden Discord\'u tamamen kapatip tekrar deneyin.')


def find_asars():
    base = Path(os.environ.get('LOCALAPPDATA', ''))
    result = []
    for channel in ('Discord', 'DiscordCanary', 'DiscordPTB'):
        root = base / channel
        if not root.is_dir():
            continue
        versions = []
        for app in root.glob('app-*'):
            try:
                version = tuple(int(n) for n in app.name[4:].split('.'))
            except ValueError:
                continue
            asar = app / 'resources' / 'app.asar'
            if asar.is_file(): versions.append((version, asar))
        for _, asar in sorted(versions, reverse=True):
            result.append(asar)
    return result


def hook_source():
    return (HERE / 'bridge-hook.cjs').read_text(encoding='utf-8')


def disabled_marker(asar):
    installation_root = Path(asar).resolve().parent.parent.parent
    key = hashlib.sha256(str(installation_root).casefold().encode('utf-8')).hexdigest()
    return STATE / ('disabled-' + key + '.json')


def apply_to(asar, explicit=True):
    import patcher
    assert_closed(asar)
    hook = hook_source()
    current = patcher.inspect(asar)
    if current['patched'] and current['manifest'].get('hook_sha256') != hashlib.sha256(hook.encode('utf-8')).hexdigest():
        # Only our exact, hash-verified previous patch can be migrated.
        patcher.restore(asar)
    result = patcher.patch(Path(asar), hook)
    if explicit: disabled_marker(asar).unlink(missing_ok=True)
    return result


def restore_from(asar):
    import patcher
    assert_closed(asar)
    # A running observer must not immediately reapply a deliberately removed patch.
    disabled_marker(asar).write_text('{"disabled":true}', encoding='utf-8')
    return patcher.restore(asar)


def run_watcher():
    """Only monitor installations while this launcher session is alive; no autostart."""
    # Named mutex prevents multiple supervisors applying the same patch.
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    k.CreateMutexW.restype = wintypes.HANDLE
    handle = k.CreateMutexW(None, False, 'Local\\DiscordBridge.UpdateWatcher.v1')
    if ctypes.get_last_error() == 183:
        return
    idle_since = time.monotonic()
    seen = {}
    pending = {}
    try:
        while time.monotonic() - idle_since < 180:
            if discord_processes(): idle_since = time.monotonic()
            for asar in find_asars():
                try:
                    if disabled_marker(asar).exists(): continue
                    sig = (asar.stat().st_size, asar.stat().st_mtime_ns)
                    if seen.get(str(asar)) == sig: continue
                    # An updater may still be writing a newly discovered archive.
                    if pending.get(str(asar)) != sig:
                        pending[str(asar)] = sig
                        continue
                    assert_closed(asar)
                    apply_to(asar, explicit=False)
                    seen[str(asar)] = (asar.stat().st_size, asar.stat().st_mtime_ns)
                    (STATE / 'watcher.json').write_text(json.dumps({'status': 'patched', 'version': asar.parent.parent.name}), encoding='utf-8')
                except RuntimeError:
                    continue
                except Exception as exc:
                    # Save class only: exception messages from third-party artifacts can contain private paths.
                    (STATE / 'watcher.json').write_text(json.dumps({'status': 'unsupported', 'error_type': type(exc).__name__}), encoding='utf-8')
            time.sleep(3)
    finally:
        k.CloseHandle.argtypes = [wintypes.HANDLE]; k.CloseHandle(handle)


def launch(asar):
    # Launch via official updater to retain official update flow.
    app_dir = Path(asar).parent.parent
    root = app_dir.parent
    exe = next((p for p in app_dir.glob('*.exe') if p.name.lower() in ('discord.exe', 'discordcanary.exe', 'discordptb.exe')), None)
    if exe is None: raise RuntimeError('Discord calistirilabilir dosyasi bulunamadi.')
    for proc in discord_processes():
        if proc['path'] is None or root.resolve() in Path(proc['path']).resolve().parents:
            raise RuntimeError('Discord zaten acik. Yamayi kullanmak icin tamamen kapatip tekrar acin.')
    command = [sys.executable, '--watch'] if getattr(sys, 'frozen', False) else [sys.executable, str(Path(__file__).resolve()), '--watch']
    watcher_env = os.environ.copy()
    if getattr(sys, 'frozen', False): watcher_env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True, env=watcher_env)
    updater = root / 'Update.exe'
    args = [str(updater), '--processStart', exe.name] if updater.is_file() else [str(exe)]
    subprocess.Popen(args, cwd=str(root), close_fds=True)


def runner():
    return [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, str(Path(__file__).resolve())]


def gui():
    import tkinter as tk
    from tkinter import ttk
    import patcher
    root = tk.Tk(); root.title('Discord Unbound | Deneysel 0.2.0'); root.geometry('740x650'); root.minsize(680, 600)
    assets = HERE / 'assets' if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1] / 'assets'
    root._brand_icon = tk.PhotoImage(file=str(assets / 'discord-unbound-icon.png'))
    root.iconphoto(True, root._brand_icon)
    frame = ttk.Frame(root, padding=24); frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Discord Unbound', font=('Segoe UI', 23, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Orijinal Discord için yerel bağlantı yaması · Shazeus', font=('Segoe UI', 11)).pack(anchor='w', pady=(0, 15))
    ttk.Label(frame, text='Deneysel: Uyumluluk internet saglayicisina ve Discord surumune gore degisebilir.', wraplength=650).pack(anchor='w')
    choices = ttk.Combobox(frame, state='readonly'); choices.pack(fill='x', pady=16)
    log = tk.Text(frame, height=10, wrap='word', font=('Segoe UI', 10)); log.pack(fill='both', expand=True)
    controls = ttk.Frame(frame); controls.pack(fill='x', pady=(16, 0))
    paths = []
    def say(message):
        def write(): log.insert('end', str(message) + '\n'); log.see('end')
        root.after(0, write)
    def refresh():
        nonlocal paths
        paths = find_asars(); choices['values'] = [f'{p.parent.parent.parent.name} / {p.parent.parent.name}' for p in paths]
        if paths: choices.current(0); say('Kurulum bulundu. Yama icin Discord tamamen kapali olmali.')
        else: say('Standart kullanici kurulumunda Discord bulunamadi. CLI --asar ile ozel yol belirtilebilir.')
    def action(kind):
        if choices.current() < 0: return
        asar = paths[choices.current()]
        for b in buttons: b.config(state='disabled')
        def task():
            try:
                if kind == 'restore':
                    restore_from(asar); say('Orijinal dosya geri yuklendi.')
                else:
                    result = apply_to(asar); say('Yama hazir: ' + result.get('status', 'ok'))
                    if kind == 'launch': launch(asar); say('Discord baslatildi. Guncelleme gozlemcisi bu oturumda etkin.')
            except Exception as exc: say(f'Islem tamamlanmadi: {exc}')
            finally:
                root.after(0, lambda: [b.config(state='normal') for b in buttons])
        threading.Thread(target=task, daemon=True).start()
    buttons = []
    for label, kind in [('Yamala ve aç', 'launch'), ('Yalnızca yamala', 'patch'), ('Orijinale dön', 'restore')]:
        b = ttk.Button(controls, text=label, command=lambda k=kind: action(k)); b.pack(side='left', padx=(0, 10)); buttons.append(b)
    ttk.Separator(frame).pack(fill='x', pady=(18, 10))
    ttk.Label(frame, text='Normal tarayıcıda Discord', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Yalnızca Discord adresleri yerel yardımcıdan geçer. Kapatınca önceki Windows PAC ayarı geri yüklenir.', wraplength=670).pack(anchor='w', pady=(4, 8))
    web_status = tk.StringVar(value='Web erişimi durumu kontrol ediliyor…')
    ttk.Label(frame, textvariable=web_status).pack(anchor='w')
    web_controls = ttk.Frame(frame); web_controls.pack(fill='x', pady=(8, 0))
    web_buttons = []
    def web_action(kind):
        for button in web_buttons: button.config(state='disabled')
        def task():
            try:
                import web_access
                if kind == 'stop': result = web_access.stop()
                elif kind in ('start', 'open'):
                    result = web_access.start(runner())
                    if kind == 'open':
                        import webbrowser
                        webbrowser.open('https://discord.com/app')
                else: result = web_access.status()
                text = 'Web erişimi açık · yerel yardımcı çalışıyor' if result['active'] else 'Web erişimi kapalı'
                root.after(0, lambda: web_status.set(text))
                if result.get('mode') == 'previous-local-pac-unavailable' and kind != 'status':
                    say('Önceki yerel PAC erişilemiyordu. Adresi yedeklendi; kapatınca geri yüklenecek.')
            except Exception as exc: say(str(exc))
            finally: root.after(0, lambda: [button.config(state='normal') for button in web_buttons])
        threading.Thread(target=task, daemon=True).start()
    for label, kind in [('Web erişimini aç', 'start'), ('Web erişimini kapat', 'stop'), ('Discord sitesini aç', 'open')]:
        button = ttk.Button(web_controls, text=label, command=lambda k=kind: web_action(k)); button.pack(side='left', padx=(0, 10)); web_buttons.append(button)
    def close():
        def finish():
            try:
                import web_access
                web_access.stop()
            except Exception as exc:
                root.after(0, lambda message=str(exc): say('Web yardımcısı: ' + message))
            finally: root.after(0, root.destroy)
        for button in web_buttons: button.config(state='disabled')
        threading.Thread(target=finish, daemon=True).start()
    root.protocol('WM_DELETE_WINDOW', close)
    root.after(100, lambda: web_action('status'))
    refresh(); root.mainloop()


def main():
    parser = argparse.ArgumentParser(description='DiscordUnbound experimental Windows patcher')
    parser.add_argument('--watch', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--asar', type=Path)
    parser.add_argument('--patch', action='store_true')
    parser.add_argument('--restore', action='store_true')
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--web-start', action='store_true', help='Enable Discord-only Windows browser PAC')
    parser.add_argument('--web-stop', action='store_true', help='Disable web helper and restore previous PAC')
    parser.add_argument('--web-status', action='store_true', help='Show web helper status without private configuration')
    parser.add_argument('--web-worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--web-guard', type=int, help=argparse.SUPPRESS)
    parser.add_argument('--report', type=Path, help='Write CLI result as JSON (also works with windowed EXE)')
    args = parser.parse_args()
    def emit(value):
        data = json.dumps(value, indent=2, default=str)
        if args.report: args.report.write_text(data, encoding='utf-8')
        elif sys.stdout is not None: print(data)
    if args.watch: return run_watcher()
    if args.web_worker or args.web_guard is not None or args.web_start or args.web_stop or args.web_status:
        import web_access
        if args.web_worker: return web_access.worker(runner())
        if args.web_guard is not None: return web_access.guard(args.web_guard)
        if args.web_start: emit(web_access.start(runner()))
        elif args.web_stop: emit(web_access.stop())
        else: emit(web_access.status())
        return
    if args.version:
        emit({'version': '0.2.0', 'hook_sha256': hashlib.sha256(hook_source().encode('utf-8')).hexdigest()}); return
    if args.list:
        emit([str(p) for p in find_asars()]); return
    if args.asar:
        import patcher
        if args.restore:
            result = restore_from(args.asar)
        elif args.patch or args.launch:
            result = apply_to(args.asar)
            if args.launch: launch(args.asar)
        else: result = patcher.inspect(args.asar)
        emit(result); return
    gui()


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        if sys.stderr is not None: print(str(exc), file=sys.stderr)
        sys.exit(1)
