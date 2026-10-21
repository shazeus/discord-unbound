"""Build a Windows x64 executable and release archive from the project root."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    if os.name != 'nt': raise SystemExit('The packaged executable must be built on Windows x64.')
    dist = ROOT / 'dist'
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed',
               '--name', 'DiscordUnbound', '--distpath', str(dist), '--workpath', str(ROOT / 'build/pyinstaller'),
               '--specpath', str(ROOT / 'build'), '--add-data', str(ROOT / 'src/bridge-hook.cjs') + ';.',
               '--add-data', str(ROOT / 'assets/discord-unbound-icon.png') + ';assets',
               '--icon', str(ROOT / 'assets/discord-unbound.ico'), str(ROOT / 'src/app.py')]
    subprocess.run(command, cwd=ROOT, check=True)
    version_report = ROOT / 'build/packaged-version.json'
    subprocess.run([str(dist / 'DiscordUnbound.exe'), '--version', '--report', str(version_report)], check=True, timeout=20)
    report = json.loads(version_report.read_text(encoding='utf-8'))
    expected = hashlib.sha256((ROOT / 'src/bridge-hook.cjs').read_text(encoding='utf-8').encode()).hexdigest()
    if report['hook_sha256'] != expected: raise SystemExit('Embedded hook does not match source')
    archive = dist / 'DiscordUnbound-windows-x64.zip'
    included = [dist / 'DiscordUnbound.exe', ROOT / 'README.md', ROOT / 'README.en.md', ROOT / 'LICENSE']
    included.extend(p for p in (ROOT / 'third-party').rglob('*') if p.is_file())
    included.extend(p for p in (ROOT / 'assets').rglob('*') if p.is_file() and p.suffix.lower() in ('.png', '.ico'))
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for source in included:
            relative = source.name if source.parent == dist else source.relative_to(ROOT).as_posix()
            bundle.write(source, 'DiscordUnbound/' + relative)
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip(): raise SystemExit('Archive verification failed')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (dist / 'DiscordUnbound.exe', archive)}
    (dist / 'SHA256SUMS.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    print(json.dumps({'version': report['version'], 'embedded_hook_matches_source': True, 'sha256': hashes}, indent=2))


if __name__ == '__main__': main()
