# Verification — 21 October 2026

- 30 Python tests passed: ASAR parsing and restoration, tamper detection,
  fuse checks, version discovery, open-process protection, hook migration,
  browser PAC composition, settings ownership and local proxy framing.
- 14 Node tests passed: TLS framing, PAC scope, ports, native updater adapter,
  manifest URL rewriting, preserved hashes and binary streaming.
- Public HTTPS / Gateway A/B probes passed with GoodbyeDPI stopped:
  direct Discord requests reset; bridge API, app page and avatar returned 200.
  Gateway WebSocket upgraded with 101 and returned HELLO opcode 10.
- The observed voice signaling endpoint on `discord.media:2053` upgraded with
  HTTP 101 and returned voice HELLO opcode 8 with a verified TLS certificate.
  The user subsequently confirmed working messages and voice in the installed
  client with GoodbyeDPI stopped. UDP is direct; no remote relay was added.
- A private copy of the installed Electron runtime loaded the hook before
  app readiness, fetched the Discord API and downloaded an official 19,137-byte
  update module. Its SHA-256 matched the public manifest.
- The installed Discord 1.0.9264 was patched and restarted. The native updater
  adapter handled two manifest requests, reported zero bridge failures and
  the main window title became Friends / Discord.
- The packaged Windows x64 EXE's installation discovery command succeeded.
  Tkinter controls were constructed successfully in a GUI smoke test.

Video, screen sharing, a new host-version installation and other PCs
still require verification. Automated tests do not log in, send messages or
read account tokens. Original ASAR bytes are backed up beside the installation.

See `live-result.json` for public network probe details and `RESEARCH.md` for
artifact identities, analysis scope and the native updater investigation.

## 0.1.1 compatibility patch

The original plain-HTTP proxy path returned 404 for a Discord navigation; the
patched handler returns an HTTPS 307 upgrade. Gift and support short links now
have exact-host scope. Tests verify payment-provider domains remain DIRECT and
that POST bodies are not forwarded by the HTTP navigation handler.

In a private Electron runtime, the public Nitro page and Stripe SDK returned 200;
the official update module retained its expected hash. This does not verify a
purchase, subscription, gift redemption or 3-D Secure transaction. See
`COMPATIBILITY.md` and `checkout-connectivity.json` for scope and results.

## 0.2.0 local browser access

The Windows PAC resolver selected the loopback helper for Discord, returning
HTTP 200 with normal certificate validation. Cloudflare and Stripe remained
DIRECT and also returned HTTP 200. Reloading an existing normal Brave tab
rendered the Discord homepage after its earlier connection-reset error.

Both source and packaged Windows executables passed normal shutdown and forced
worker termination tests: the previous WinINet flags, proxy server, bypass and
PAC URL were restored exactly. The packaged helper was then enabled again.
GUI controls were constructed successfully, and the packaged helper started
without a separately installed Python or Node runtime.

These checks did not log in, submit payments or verify browser voice/video.
See `WEB-ACCESS.md` and `web-connectivity.json`. Private settings snapshots and
control credentials are deliberately excluded from published test reports.

## 0.3.0 — 26 October 2026

- 39 Python tests and 14 Node tests passed. New scenarios cover numeric newest-version launch with exact EXE selection, synthetic version arrival, active-client protection, verified active-patch recognition, persistent state reload, multi-channel isolation, existing-startup preference and ownership-preserving removal.
- Packaged 0.3.0 launched the installed Discord Stable1.0.9265. The user confirmed loaded messages, voice channel connection and a working stream/screen share on Turkcell after relaunch.
- The content-addressed durable EXE matched the built binary, returned version0.3.0 independently, and the current-user Run value matched the saved command. Discord had no existing recognized Run command on this PC; Discord autolaunch was not enabled.
- Türk Telekom basic desktop operation is a user report; no separate browser/screen-share proof. Provider test scope is in both READMEs.
- A physical reboot and a real new host-version download/install were not performed. Web startup is still session-only. Payment and camera-video tests remain unverified.
