# Verification — 21 October 2026

- 19 Python tests passed: ASAR parsing and restoration, tamper detection,
  fuse checks, version discovery, open-process protection and hook migration.
- 12 Node tests passed: TLS framing, PAC scope, ports, native updater adapter,
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
