# Discord Unbound: evidence and compatibility limits

Investigation date: 21 October 2026. Target examined: Windows Discord stable
1.0.9264. This report contains observations and short interface descriptions;
Discord source, executables, native addons, credentials and private logs are
not included in this project.

## Artifact identity

| Original artifact | SHA-256 |
| --- | --- |
| `resources/app.asar` | `0025c02c7241045a12464309604ec4d5b8ec7ed2ce43cce05d5dacb8f253f672` |
| `Discord.exe` | `a3b0cf011eb75f568963fd0942648455e125b030b4b578fec652dc0b4e747561` |
| `updater.node` | `c25eca24e0b53f591608c12f7bcb04bc14c5f6099547fb88316567d01527a196` |

The original package declares `bundle.js` as its main entry. Selected static
package/bundle analysis is recorded as REA evidence
`ev_f69406651efa6458fe135a08d5323a7fa198cc9271a3699c6c0e71b58e0189d5`.
Coverage is partial: this is not an audit of every bundled dependency or native
component, and static analysis alone does not demonstrate runtime behavior.

## Electron fuse compatibility

REA evidence
`ev_6465af39e5f53f8733b55d4f4833cf39b06528ac06917fce2896cad6aa28eacd`
records the examined executable's fuse state. An independent bounded local
read found fuse format version 1, nine fuse entries, and
`EnableEmbeddedAsarIntegrityValidation` at index 4 disabled. This permits testing
an ASAR entry-point change on this specific artifact without changing executable
fuses. Discord Unbound refuses patching when the integrity fuse is enabled or the
fuse state cannot be established. Other versions and channels require their own
compatibility check.

## Bootstrap patch boundaries

The patch redirects the package main field to an added CommonJS entry that waits
for the connection hook's ready promise before requiring the original main.
Original archive payload bytes and unpacked entry metadata are retained; changed
and added entries receive SHA-256 integrity records. Exact original archive bytes
are backed up outside the archive, with a state record containing original and
patched hashes. Restore refuses to overwrite an archive or use a backup whose
hash no longer matches its recorded state.

Synthetic tests cover round-trip restoration, repeated application, tampered
archives/backups, unsafe paths, numeric version discovery, unknown/enabled fuses,
nested CommonJS entry points, integrity hashes and operation locks. They establish
these adapter properties, not universal Discord connectivity.

## Native updater boundary

Static inspection of the original bundle establishes that the Windows bootstrap
loads `updater.node` adjacent to the channel executable. Its native `Updater`
constructor receives a response callback plus release channel, platform,
repository URL, root directory, OS architecture and user-data directory. The
default repository origin is `https://updates.discord.com/`; the bootstrap also
recognizes the settings key `NEW_UPDATE_ENDPOINT`.

The wrapper communicates using serialized request IDs and command objects.
`UpdateToLatest` performs an update operation; it is not a manifest-only probe.
No manifest-only public command was established from the inspected JavaScript
wrapper. The native addon was not loaded independently during this static
inspection, because initialization may create logs or state.

The native binary contains reqwest 0.11.9 proxy implementation strings and
`HTTPS_PROXY`, `https_proxy`, `HTTP_PROXY`, `http_proxy`, `NO_PROXY` and `no_proxy`
names, together with HTTPS proxy tunneling messages. This supports trying
process-local proxy environment variables before native updater initialization.
Strings do not prove that every updater request uses those variables; runtime
verification remains necessary. Chromium proxy configuration by itself does not
establish native updater routing.

## Observed runtime result and remaining verification

The initial installed-client run started the connection hook, then displayed
“Update Failed”. Sanitized updater logs confirmed a native updater network
failure. This observation establishes a remaining native-network boundary; it
does not establish that the patch solved end-to-end Discord access.

The subsequent installed-client test with proxy variables set inside the hook
still produced a native updater connection reset; its requests were not observed
entering the local bridge. Proxy-related binary strings therefore did not establish
usable routing for this installed native updater configuration.

A separate unauthenticated public manifest request through the bridge succeeded
with HTTP 200. Its JSON contains `modules`, `full`, `deltas` and `required_modules`.
The observed artifact records contain absolute HTTPS URLs on
`stable.dl2.discordapp.net`, version information and `package_sha256` hashes. No
manifest signature field was observed; this does not establish the absence of
other signature or package authenticity mechanisms. Changing only the repository
origin would leave these absolute artifact URLs pointing directly at the CDN.
Any further adapter must preserve artifact bytes and existing verification.

The final adapter intercepts only the exact sibling `updater.node` module's
`Updater` construction and changes its repository URL to a tokenized loopback
route. That route fetches the official source using Electron's verified HTTPS
transport and rewrites artifact URL fields while preserving SHA-256 fields and
downloaded package bytes. Existing proxy environment variables are preserved.

In the installed-client retest, one native updater constructor was adapted,
two manifest requests were handled and the client opened its Friends window.
GoodbyeDPI remained stopped. This establishes bootstrap/update-check progress
on the examined installation, rather than just successful standalone HTTP probes.

A separate controlled Electron harness downloaded the actual 19,137-byte
`discord_notifications` package through the update adapter. Its SHA-256 matched
the official manifest. This establishes byte preservation for that package; it
does not establish successful installation of an unseen future host release.

The initial voice test failed at a `discord.media` TLS signaling endpoint on
port 2053. The connection adapter was extended to retain voice-media TLS ports
while restricting other Discord domains to port 443. An unauthenticated voice
WebSocket probe then returned HTTP 101 and HELLO opcode 8. The user confirmed
working messaging and actual voice after the installed-client restart, with
GoodbyeDPI still stopped. UDP packets are not relayed by this adapter.

This report does not claim successful automatic host updates,
screen sharing, operation on every PC, or compatibility with future Discord
releases. Updating is retained; the investigation does not disable or skip
Discord's update checks.

Private installation paths, installation identifiers, account data and raw logs
are deliberately omitted. The investigation used selected local artifacts;
conclusions should not be generalized to unrelated Discord builds or networks.
