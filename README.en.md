<p align="center">
  <img width="1774" height="887" alt="ChatGPT Görseli 26 Eki 2026 13_45_10" src="https://github.com/user-attachments/assets/3664d1e6-602d-4220-917e-fa33f4f5149e" />
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
- **No remote VPN server:** it does not tunnel general traffic. The desktop transport leaves DNS/proxy/routes unchanged; **Patch and launch** manages current-user startup entries; optional web mode temporarily changes and restores only the current user's automatic proxy/PAC setting.
- **TLS record splitting:** it preserves the bytes of the initial `ClientHello` while splitting its TLS records. Messaging TLS remains encrypted end to end; certificate verification stays enabled.
- **Native updater integration:** official manifest and package requests use the same transport, preserving package bytes and manifest SHA-256 fields.
- **Voice signaling:** it retains the TLS port supplied for `discord.media` voice-control connections; port 2053 has been tested. UDP audio remains direct.
- **Reversible patching:** exact original backups, hash checks, operation locking and restoration are included.
- **Persistent version observer:** resumes at Windows sign-in and watches only explicitly enrolled channels for eligible inactive versions.

## Download and run

**[Download the latest release](https://github.com/shazeus/discord-unbound/releases/latest)**

1. Download `DiscordUnbound-windows-x64.zip` from the release page and extract it.
2. **Fully quit Discord** using its system-tray icon.
3. Open `DiscordUnbound.exe`.
4. Select your installation and click **Yamala ve aç** — “Patch and launch.”

The packaged executable needs no separate Python or Node.js. **Yamala ve aç** stores a verified launcher copy in `%LOCALAPPDATA%\DiscordUnbound\launcher` and adds the current-user `DiscordUnbound` startup entry. The observer resumes at Windows sign-in even if the extracted ZIP folder moves or is removed. No administrator access, service or scheduled task is needed.

If Discord was already configured to start with Windows, its command is backed up and routed through preparation of the newest version. Otherwise Discord autostart is not enabled; only the observer resumes. For manual launches use **Discord Unbound → Yamala ve aç**: a normal Discord shortcut can bypass preparation. **Yalnızca yamala** does not enroll startup.

**Başlangıç kaydını ve kalıcı izlemeyi kapat** disables startup/observation without changing the archive. Later third-party startup changes are preserved. Fully quit Discord and choose **Orijinale dön** to restore the original archive and unregister that channel.

## Discord in your normal browser

Click **Web erişimini aç** — “Enable web access” — then visit `https://discord.com` in Brave, Chrome, Edge or a browser that follows Windows proxy settings. No extension, separate profile or remote server is required. **Discord sitesini aç** enables the helper and opens the default browser. Web mode does not require the Discord desktop client to be installed.

- The helper listens only on `127.0.0.1` and routes only Discord targets through its local transport.
- Other sites retain the previous direct/manual proxy/PAC route. A reachable existing PAC script is fetched at startup and composed with the Discord rule.
- **Web erişimini kapat** or closing the window restores previous settings. A helper started from the CLI stays in the background until explicitly stopped.
- An independent guard restores settings if the worker unexpectedly exits. A PAC URL subsequently changed by another application is not overwritten.
- Web mode does not automatically resume at sign-in. The desktop observer uses a per-user startup entry; no service/task is installed. Machine-level WinHTTP, system DNS, routing, firewall and certificate settings are unchanged.

This version uses the current user's default LAN internet settings. Browsers with their own proxy settings or extensions may ignore Windows configuration. WPAD-only policies are refused when they cannot be composed safely. If a previous PAC points to an unreachable loopback service, its address is backed up, its manual/direct fallback is retained while enabled and its original setting is restored afterwards. Restart the helper if the previous PAC script changes on its server.

TLS certificate validation remains enabled. Payment providers remain direct; a real payment or 3-D Secure transaction is still unverified.

## Uninstalling

Discord Unbound is portable; it does not register an installation in Control Panel or **Settings → Apps**. To remove it completely:

1. **Fully quit Discord** using its system-tray icon.
2. Open Discord Unbound, select the installation you patched and click **Orijinale dön** — “Restore original.” Repeat for each installation if you patched more than one. Skip this step if you only used web mode.
3. Click **Başlangıç kaydını ve kalıcı izlemeyi kapat** to remove any remaining desktop enrollment, even if the patch archive has disappeared. Then click **Web erişimini kapat** — “Disable web access” — and confirm that it is disabled. This stops the web helper and restores the previous Windows proxy/PAC settings.
4. Close the Discord Unbound window, then delete the application folder extracted from the ZIP and any shortcuts you created.
5. After the observer stops and the previous proxy settings are restored, press `Win + R`, open `%LOCALAPPDATA%\DiscordUnbound` and remove remaining files, including durable launcher copies.

**Restore before deleting:** if restoring the original or disabling web access fails, resolve the error before deleting the application, backups or state files. In particular, `web-state.json` contains the previous proxy settings and must be retained until those settings have been restored. These steps do not delete your Discord account or uninstall the official Discord application.

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

The observer checks enrolled channels about once per second. Archives must remain stable across two checks and must not be used by running Discord processes. Observation continues while enrollment is enabled, even after Discord closes. A current-user `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` entry resumes it at sign-in.

**Patch and launch** sorts versions numerically, discovers the newest version again, validates and patches it, then opens **that exact executable**. Previously `Update.exe` could choose a different version from the one just patched. The client's native update and package-integrity checks still run.

**Future-version compatibility is not guaranteed.** If an updater launches the new version first, the observer does not modify the active archive or force-close Discord. Fully quit and launch through Unbound to prepare the newest version first. Unknown integrity/fuse layouts, changed archives/backups and unsupported updaters remain rejected. Physical reboot and an actual new host upgrade still need separate verification.

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
| Automated tests | 39 Python + 14 Node.js tests, including release migration checks |

**Purchase coverage:** The public Nitro page and Stripe's public SDK loaded in an isolated Electron test. No real purchase, subscription or 3-D Secure transaction was attempted. Payment providers remain direct. The desktop patch does not cover external browsers; optional web mode covers Discord URLs in browsers following Windows proxy settings. See the [compatibility audit](docs/COMPATIBILITY.md).

These results apply to the tested machine and network. They do not guarantee the same result with other providers or Discord versions. Windows ARM64/32-bit, macOS and Linux are unverified. The user confirmed screen sharing/streaming on Turkcell. Camera video calls and installing a real new Discord host version end to end remain untested. This release's executable is not code-signed.

IP-level blocking or filtering that reassembles TLS records can require a different technique. Local processing and DNS have a cost; there is no zero-latency claim.

## Internet provider tests

**✓ = tested and successful · blank = untested / no separate verification.** Results do not guarantee every subscriber, region or access type. Türk Telekom is a user report; Turkcell is the developer connection used for this project. Its access type was not identified as Superonline, Superbox or mobile, so the result must not be generalized to all three. Latest report: **26 October 2026**.

| Provider | Status | Client launch | Messages | Voice | Browser web access | Screen sharing / stream |
| --- | --- | :---: | :---: | :---: | :---: | :---: |
| Türk Telekom (access type unspecified) | ✓ Tested — user report | ✓ | ✓ | ✓ | | |
| Turkcell (access type unspecified) | ✓ Tested — developer connection | ✓ | ✓ | ✓ | ✓ | ✓ |
| Vodafone Net / Ev İnterneti | Untested | | | | | |
| Türksat Kablonet | Untested | | | | | |
| TurkNet | Untested | | | | | |
| Millenicom | Untested | | | | | |
| D-Smart Net (Andromeda) | Untested | | | | | |
| Netspeed | Untested | | | | | |
| GıbırNet | Untested | | | | | |
| Comnet | Untested | | | | | |
| Fixnet | Untested | | | | | |
| Extranet | Untested | | | | | |
| Sadenet | Untested | | | | | |
| Poyraz WiFi | Untested | | | | | |
| Vodafone mobil | Untested | | | | | |
| Türk Telekom mobil | Untested | | | | | |

The Türk Telekom report covers basic desktop use; no separate browser test was documented. Turkcell web status comes from the earlier normal-browser test. This covers major providers and additional community test candidates, not all licensed operators or a market ranking. [BTK market data](https://btk.tr/elektronik-haberlesme-pazar-verileri).

**The provider check marks do not cover these additional stages:**

| Stage | Status |
| --- | --- |
| Update manifest and sample official module | ✓ Previously checked on Turkcell; package hash matched |
| 0.3.0 persistent registration / prepare newest version | ✓ Automated scenarios; live launch documented separately |
| Physical power-off and reboot | Untested — sign-in continuity testing is not a physical reboot |
| Download and install of a real new Discord host version | Untested — synthetic version changes are not real upgrades |
| Screen sharing / stream | ? Turkcell ? user confirmed after the live relaunch on 26 October 2026 |
| Camera video call | Untested |
| Real Nitro purchase / subscription / 3-D Secure | Untested |

Report provider, access type, Unbound/Discord versions and the exact successful stages. Do not share a full address, account details or tokens.

## Backups and troubleshooting

- Original backup: `resources/app.asar.discordunbound.original`
- Patch state and hashes: `resources/app.asar.discordunbound.json`
- Runtime status: `%LOCALAPPDATA%\DiscordUnbound\runtime.json`
- Persistent enrollment / startup backup: `%LOCALAPPDATA%\DiscordUnbound\managed.json` — retain until startup is disabled.
- Observer status: `%LOCALAPPDATA%\DiscordUnbound\watcher.json`
- Web-mode backup: `%LOCALAPPDATA%\DiscordUnbound\web-state.json` — contains prior proxy settings and a local control secret; do not include this file in issue reports.

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
.\DiscordUnbound.exe --web-start --report web-status.json
.\DiscordUnbound.exe --web-stop
.\DiscordUnbound.exe --web-status
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
