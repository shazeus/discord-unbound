<p align="center">
  <img src="assets/discord-unbound-logo.png" alt="Discord Unbound" width="760">
</p>

<p align="center"><a href="README.md">Türkçe</a> · <strong>English</strong></p>

# Discord Unbound

> Ben ezelden beridir hür yaşadım, hür yaşarım.  
> Hangi çılgın bana zincir vuracakmış? Şaşarım!  
> Kükremiş sel gibiyim; bendimi çiğner, aşarım;  
> Yırtarım dağları, enginlere sığmam, taşarım.
>
> — Mehmet Âkif Ersoy, *İstiklal Marşı* — the Turkish national anthem

**English translation preserving the meaning:**

> Since time immemorial I have lived free, and free I shall live.  
> What madman would put me in chains? I am astonished!  
> I am like a roaring torrent; I trample my dam and break through;  
> I tear through mountains; the open seas cannot contain me; I overflow.

## Why these lines?

Discord Unbound began with the belief that people in Türkiye should be able to communicate freely, just like everyone else. This stanza is not included as decoration: it expresses the freedom and independence at the project's foundation. Refusing chains and breaking through a dam reflect my belief that technical barriers should not determine people's ability to communicate.

**Unbound** means released from restraints or no longer confined. The project turns that idea into a practical tool: using the familiar Discord application with its familiar interface.

## What it does

Discord Unbound is an open-source Windows launcher and reversible patching utility for the **official installed Discord desktop client**. It adds an in-process transport adapter intended to work around TLS traffic filtering observed on the tested connection.

Discord provides the interface, accounts, servers and messaging features. This repository does not distribute Discord's proprietary source, installers or native modules. It adds a small startup wrapper to the user's own official installation.

### Features

- **Discord-specific routing:** Discord domains use the local adapter inside Electron sessions; other domains remain direct.
- **No remote VPN server:** it does not tunnel the computer's general traffic or change system routing, DNS, proxy, firewall or certificate settings.
- **TLS record splitting:** it preserves the bytes of the initial `ClientHello` while splitting its TLS records. Messaging TLS remains encrypted end to end; certificate verification stays enabled.
- **Native updater integration:** official manifest and package requests use the same transport, preserving package bytes and manifest SHA-256 fields.
- **Voice signaling:** it retains the TLS port supplied for `discord.media` voice-control connections; port 2053 has been tested. UDP audio remains direct.
- **Reversible patching:** exact original backups, hash checks, operation locking and restoration are included.
- **Version observer:** watches new installation directories and attempts to reapply the adapter to eligible inactive versions.

## Download and run

**[Download the latest release](https://github.com/shazeus/discord-unbound/releases/latest)**

1. Download `DiscordUnbound-windows-x64.zip` from the release page and extract it.
2. **Fully quit Discord** using its system-tray icon.
3. Open `DiscordUnbound.exe`.
4. Select your installation and click **Yamala ve aç** — “Patch and launch.”

The packaged executable requires no separate Python or Node.js installation. Your existing Discord shortcut can open the patched version afterwards. Launching through Discord Unbound is recommended when you want the version observer to run.

To restore the original, fully quit Discord and choose **Orijinale dön** — “Restore original.” This also prevents the observer from immediately reapplying the patch to that installation.

## Architecture

```text
DiscordUnbound.exe
  ├─ Installation discovery and running-process checks
  ├─ ASAR validation → original backup → startup wrapper
  └─ Official Discord launch flow + version observer

Discord main process
  ├─ Electron-session PAC rules
  │    └─ 127.0.0.1 → TLS record splitting → Discord
  └─ Native updater constructor adapter
       └─ Tokenized loopback endpoint → verified HTTPS → official repository/CDN
```

### Startup and archive patch

The utility resolves the `main` field in `package.json` inside `resources/app.asar`. It checks archive bounds, paths, entry-point type and Electron fuse state in the adjacent Discord executable. If embedded ASAR integrity enforcement is enabled or its state is unknown, patching stops. Executable fuse values are not changed.

The entry point is redirected to a small additional CommonJS file. Once the connection hook is ready, the original entry point runs. Added or changed archive entries receive updated SHA-256 integrity metadata. The exact original ASAR bytes are kept separately.

### Transport layer

The local listener binds only to `127.0.0.1`. PAC rules cover `discord.com`, `discord.gg`, `discordapp.com`, `discordapp.net` and `discord.media`, including their subdomains. Private and local resolved IP addresses are rejected. General Discord targets are restricted to TLS port 443; valid TCP ports are retained for voice servers under `discord.media`.

Hostnames are resolved through Google DNS-over-HTTPS first, with a bounded fallback to system DNS. Runtime status identifies the resolver path used. Google DNS can observe the queried hostnames and source IP address.

### Update flow

Discord's native Rust updater does not use Electron-session proxy settings in the examined configuration. The adapter therefore wraps only the `Updater` constructor exported by the exact `updater.node` beside the executable. Its repository URL is redirected to a loopback endpoint protected by a random session token.

The adapter fetches the official manifest using certificate-verified HTTPS. Package `url` fields are rewritten to the local transport; version fields, package SHA-256 values and downloaded package bytes are preserved. Update checks and native package verification are not disabled. No persistent proxy environment variables are added.

The observer checks version directories approximately every three seconds. An archive must remain unchanged across two checks, and no Discord process may be using that version, before patching proceeds. The observer exits within three minutes after Discord closes. No startup service or scheduled task is installed.

**Compatibility with every future version is not guaranteed.** The updater can launch a new version before the observer patches it. If that happens, quit Discord and launch it through Discord Unbound again. New archive layouts, updater interfaces or integrity enforcement can require code changes.

## Compatibility and verification

| Area | Verified result |
| --- | --- |
| Packaged build | Windows x64 |
| Examined client | Discord Stable 1.0.9264 / Electron 42.7.1 |
| Messaging and voice | Confirmed in the installed client with GoodbyeDPI stopped |
| Gateway | Valid TLS, WebSocket 101, HELLO opcode 10 |
| Voice signaling | `discord.media:2053`, WebSocket 101, HELLO opcode 8 |
| Update check | Native updater passed its manifest check and the main UI opened |
| Package integrity | Official 19,137-byte module downloaded; SHA-256 matched its manifest |
| Automated tests | 19 Python + 12 Node.js tests, including release migration checks |

These results apply to the tested machine and network. They do not guarantee the same result with other providers or Discord versions. Windows ARM64/32-bit, macOS and Linux are unverified. Video, screen sharing and installing a newer main Discord version end to end have not been tested. This release's executable is not code-signed.

IP-level blocking or filtering that reassembles TLS records can require a different technique. Local processing and DNS have a cost; there is no zero-latency claim.

## Backups and troubleshooting

- Original backup: `resources/app.asar.discordunbound.original`
- Patch state and hashes: `resources/app.asar.discordunbound.json`
- Runtime status: `%LOCALAPPDATA%\DiscordUnbound\runtime.json`
- Observer status: `%LOCALAPPDATA%\DiscordUnbound\watcher.json`

Legacy `.discordbridge.original` and `.discordbridge.json` files from the initial local prototype are also recognized. Restoration verifies both the current archive and backup hashes rather than overwriting an altered archive. Keep backup and state files if an operation is interrupted.

**Update failed:** fully quit Discord, then launch it through the latest Discord Unbound release. **Voice does not connect:** check voice signaling and UDP connectivity separately; successful signaling does not prove UDP reachability. Include your Discord version, OS and a sanitized error description when reporting an issue. Do not post account tokens or private messages.

Runtime records contain status and connection counters, not account tokens, message content or traffic bodies.

## Development

Use Python 3.10+ for the source launcher and Node.js 22+ for JavaScript tests. The packaged build does not require either runtime to be installed separately.

```powershell
python src/app.py
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/hook.test.cjs
```

Optional unauthenticated live connectivity probe:

```powershell
node tests/probe-live.cjs docs/live-result.json
```

Custom installation path and machine-readable output:

```powershell
.\DiscordUnbound.exe --list --report installations.json
.\DiscordUnbound.exe --asar 'D:\Discord\app-1.0.9264\resources\app.asar' --patch --report patch-result.json
.\DiscordUnbound.exe --version --report version.json
```

Build:

```powershell
python -m pip install -r requirements-build.txt
python scripts/build.py
```

The build writes the executable, distribution ZIP and SHA-256 checksums to `dist/`. Tests use synthetic archives and local connections without modifying installed Discord.

## Author and license

**Author: [Shazeus](https://github.com/shazeus)**

Project code is available under the [MIT license](LICENSE). Runtime component notices are included in `third-party/`. The Discord name and adapted Discord mark belong to their respective rights holders. This project is independent and is not endorsed by or affiliated with Discord. The project license grants no additional trademark rights.

[Technical investigation](docs/RESEARCH.md) · [Verification records](docs/TEST-RESULTS.md) · [Source for the anthem quotation](https://www.tbmm.gov.tr/milletvekili/UyeGenelKurulKonusmalariDetay?eid=143116)
