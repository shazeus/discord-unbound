"""Conservative, reversible Discord ASAR entry-point adapter.

The caller MUST ensure all Discord processes are closed before patch/restore.
Only positively identified Electron executables without embedded ASAR integrity
are supported. No executable fuses are modified. Unknown versions fail closed.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import tempfile

MAX_ARCHIVE = 512 * 1024 * 1024
MAX_HEADER = 16 * 1024 * 1024
BLOCK_SIZE = 4 * 1024 * 1024
FUSE_SENTINEL = b"dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX"
SCHEMA = 1
MARKER = "bridge-manifest.json"
RESERVED = {MARKER, "bridge-entry.cjs", "bridge-hook.cjs"}


class PatchError(RuntimeError):
    pass


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _json(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _load_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PatchError("Ambiguous duplicate JSON key")
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=unique)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise PatchError("Invalid or excessively nested JSON") from exc


def _safe_name(name):
    return isinstance(name, str) and bool(name) and name not in (".", "..") and not any(c in name for c in ("/", "\\", ":", "\x00"))


def _read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise PatchError("Expected a regular, non-symlink file: " + str(path))
    if path.stat().st_size > MAX_ARCHIVE:
        raise PatchError("File exceeds archive size limit")
    return path.read_bytes()


def _decode(data):
    if len(data) < 16:
        raise PatchError("Truncated ASAR")
    size_pickle, header_size, payload_size, json_size = struct.unpack_from("<IIII", data)
    if size_pickle != 4 or header_size < 8 or header_size > MAX_HEADER:
        raise PatchError("Invalid ASAR header size")
    if payload_size + 4 != header_size or json_size > payload_size - 4 or 8 + header_size > len(data):
        raise PatchError("Invalid ASAR pickle framing")
    try:
        header = _load_json(data[16:16 + json_size])
    except (ValueError, UnicodeError) as exc:
        raise PatchError("Invalid ASAR JSON") from exc
    payload = data[8 + header_size:]
    entries = {}

    def visit(node, prefix="", depth=0):
        if depth > 64 or not isinstance(node, dict) or not isinstance(node.get("files"), dict):
            raise PatchError("Invalid ASAR directory")
        for name, entry in node["files"].items():
            if not _safe_name(name) or not isinstance(entry, dict):
                raise PatchError("Unsafe ASAR path")
            key = prefix + name
            if "files" in entry:
                visit(entry, key + "/", depth + 1)
            elif "link" in entry:
                link = entry["link"]
                if not isinstance(link, str) or "\\" in link or ":" in link or PurePosixPath(link).is_absolute() or ".." in PurePosixPath(link).parts:
                    raise PatchError("Unsafe ASAR link")
                entries[key] = entry
            else:
                size = entry.get("size")
                if type(size) is not int or size < 0:
                    raise PatchError("Invalid ASAR file size")
                if not entry.get("unpacked"):
                    offset = entry.get("offset")
                    if not isinstance(offset, str) or not offset.isdecimal() or int(offset) + size > len(payload):
                        raise PatchError("Invalid ASAR file offset")
                entries[key] = entry
            if len(entries) > 100000:
                raise PatchError("Too many ASAR entries")
    visit(header)
    return header, payload, entries


def _encode(header, payload):
    raw = _json(header)
    padding = (-len(raw)) % 4
    header_payload = struct.pack("<I", len(raw)) + raw + b"\0" * padding
    header_pickle = struct.pack("<I", len(header_payload)) + header_payload
    if len(header_pickle) > MAX_HEADER or 8 + len(header_pickle) + len(payload) > MAX_ARCHIVE:
        raise PatchError("Patched archive exceeds size limit")
    return struct.pack("<II", 4, len(header_pickle)) + header_pickle + payload


def _content(entry, payload):
    if entry.get("unpacked") or "link" in entry or "offset" not in entry:
        raise PatchError("Entry must be a packed regular file")
    start = int(entry["offset"])
    return payload[start:start + entry["size"]]


def _main(package, entries):
    main = package.get("main")
    if not isinstance(main, str):
        raise PatchError("Package must declare an explicit main entry")
    if main.startswith("./"):
        main = main[2:]
    parts = main.split("/")
    if not all(_safe_name(x) for x in parts) or not main.endswith((".js", ".cjs")) or main not in entries or main in RESERVED:
        raise PatchError("Unsupported package main entry")
    if package.get("type") == "module":
        raise PatchError("ES module entry packages are unsupported")
    return main


def validate_fuses(asar_path):
    """Inspect the channel executable adjacent to resources, never change it."""
    app_dir = Path(asar_path).resolve().parent.parent
    candidates = [app_dir / name for name in ("Discord.exe", "DiscordCanary.exe", "DiscordPTB.exe") if (app_dir / name).is_file()]
    if len(candidates) != 1:
        raise PatchError("Cannot uniquely identify sibling Discord executable")
    binary = _read(candidates[0])
    if not binary.startswith(b"MZ") or binary.count(FUSE_SENTINEL) != 1:
        raise PatchError("Unknown Electron fuse layout")
    start = binary.index(FUSE_SENTINEL) + len(FUSE_SENTINEL)
    if start + 2 > len(binary):
        raise PatchError("Truncated Electron fuse layout")
    version, length = binary[start:start + 2]
    values = binary[start + 2:start + 2 + length]
    if version != 1 or length < 5 or len(values) != length or values[4] != ord("0"):
        raise PatchError("Embedded ASAR integrity enabled or fuse state unknown")
    return {"executable": str(candidates[0]), "embedded_asar_integrity": False}


def _paths(path):
    path = Path(path).absolute()
    current = (path.with_name(path.name + ".discordunbound.original"), path.with_name(path.name + ".discordunbound.json"))
    legacy = (path.with_name(path.name + ".discordbridge.original"), path.with_name(path.name + ".discordbridge.json"))
    if any(item.exists() for item in legacy):
        if any(item.exists() for item in current):
            raise PatchError("Conflicting current and legacy backups; refusing mutation")
        return path, *legacy
    return path, *current


@contextlib.contextmanager
def _lock(path):
    lock = path.with_name(path.name + ".discordbridge.lock")
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise PatchError("Another operation or interrupted operation owns the patch lock") from exc
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def _atomic(path, data):
    if path.is_symlink():
        raise PatchError("Refusing to replace symlink")
    fd, temporary = tempfile.mkstemp(prefix=".discordunbound-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def inspect(asar_path):
    """Read archive metadata without mutating the installation."""
    data = _read(asar_path)
    _, payload, entries = _decode(data)
    if "package.json" not in entries:
        raise PatchError("Missing package.json")
    try:
        package = _load_json(_content(entries["package.json"], payload))
    except (ValueError, UnicodeError) as exc:
        raise PatchError("Invalid package.json") from exc
    if not isinstance(package, dict):
        raise PatchError("Invalid package.json object")
    marker = None
    if MARKER in entries:
        try:
            marker = _load_json(_content(entries[MARKER], payload))
        except (ValueError, UnicodeError) as exc:
            raise PatchError("Invalid patch marker") from exc
    return {"path": str(Path(asar_path).absolute()), "sha256": _sha(data), "main": package.get("main"), "patched": marker is not None, "manifest": marker, "entry_count": len(entries)}


def patch(asar_path, hook_source):
    """Install a hook entry point. Caller must first close every Discord process."""
    path, backup, state_path = _paths(asar_path)
    hook = hook_source.encode("utf-8") if isinstance(hook_source, str) else bytes(hook_source)
    if not hook or len(hook) > 2 * 1024 * 1024:
        raise PatchError("Invalid hook size")
    with _lock(path):
        validate_fuses(path)
        original = _read(path)
        header, payload, entries = _decode(original)
        if state_path.exists():
            state = _load_json(_read(state_path))
            if not isinstance(state, dict):
                raise PatchError("Invalid patch state")
            if state.get("schema") != SCHEMA or _sha(original) != state.get("patched_sha256") or _sha(_read(backup)) != state.get("original_sha256"):
                raise PatchError("Patch state or backup does not match current archive")
            if state.get("hook_sha256") != _sha(hook):
                raise PatchError("Restore before changing the installed hook")
            return {"status": "already_patched", **state}
        if backup.exists() or any(name in entries for name in RESERVED):
            raise PatchError("Unrecognized backup or existing bridge entries; refusing overwrite")
        if "package.json" not in entries:
            raise PatchError("Missing package.json")
        package_bytes = _content(entries["package.json"], payload)
        try:
            package = _load_json(package_bytes)
        except (ValueError, UnicodeError) as exc:
            raise PatchError("Invalid package.json") from exc
        if not isinstance(package, dict):
            raise PatchError("Invalid package.json object")
        main = _main(package, entries)
        _content(entries[main], payload)
        manifest = {"schema": SCHEMA, "original_main": main, "original_package": package, "original_sha256": _sha(original), "hook_sha256": _sha(hook)}
        wrapper = ("'use strict';\nrequire('./bridge-hook.cjs').ready.then(() => require(" + json.dumps("./" + main) + ")).catch(error => { console.error('DiscordUnbound startup failed', error); require('electron').app.exit(1); });\n").encode()
        package = copy.deepcopy(package)
        package["main"] = "bridge-entry.cjs"
        changed = {"package.json": _json(package), "bridge-entry.cjs": wrapper, "bridge-hook.cjs": hook, MARKER: _json(manifest)}
        new_header = copy.deepcopy(header)
        chunks = [payload]
        offset = len(payload)
        for name, content in changed.items():
            previous = copy.deepcopy(new_header["files"].get(name, {}))
            previous.update({"size": len(content), "offset": str(offset), "integrity": {"algorithm": "SHA256", "hash": _sha(content), "blockSize": BLOCK_SIZE, "blocks": [_sha(content[i:i + BLOCK_SIZE]) for i in range(0, len(content), BLOCK_SIZE)]}})
            previous.pop("unpacked", None)
            previous.pop("link", None)
            new_header["files"][name] = previous
            chunks.append(content)
            offset += len(content)
        patched = _encode(new_header, b"".join(chunks))
        _decode(patched)
        state = {**manifest, "patched_sha256": _sha(patched)}
        # Exclusive creation ensures an unknown backup is never overwritten.
        with backup.open("xb") as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
        _atomic(state_path, _json(state))
        if _sha(_read(path)) != state["original_sha256"]:
            raise PatchError("Archive changed during patch preparation; backup retained")
        _atomic(path, patched)
        return {"status": "patched", **state}


def restore(asar_path):
    """Restore exact original bytes only when archive AND backup hashes match."""
    path, backup, state_path = _paths(asar_path)
    with _lock(path):
        if not state_path.exists():
            raise PatchError("No patch state available")
        state = _load_json(_read(state_path))
        if not isinstance(state, dict):
            raise PatchError("Invalid patch state")
        current, original = _read(path), _read(backup)
        if state.get("schema") != SCHEMA or _sha(current) != state.get("patched_sha256") or _sha(original) != state.get("original_sha256"):
            raise PatchError("Archive or backup changed; refusing restore")
        _decode(original)
        _atomic(path, original)
        state_path.unlink()
        backup.unlink()
        return {"status": "restored", "sha256": _sha(original)}


def discover(root=None):
    """Find numeric app versions under LOCALAPPDATA channels or explicit root.

    Explicit root may be a Discord channel folder, app-X.Y.Z folder, or a
    parent containing Discord/DiscordCanary/DiscordPTB channel folders.
    Discovery never patches and ignores symlink directories.
    """
    base = Path(root) if root is not None else Path(os.environ.get("LOCALAPPDATA", ""))
    if root is None and not os.environ.get("LOCALAPPDATA"):
        return []
    channels = ("Discord", "DiscordCanary", "DiscordPTB")
    roots = [base] if base.name in channels or re.fullmatch(r"app-\d+(?:\.\d+){2,3}", base.name) else [base / name for name in channels]
    result = []
    for channel in roots:
        if not channel.is_dir() or channel.is_symlink():
            continue
        versions = [channel] if channel.name.startswith("app-") else list(channel.glob("app-*"))
        for version in versions:
            match = re.fullmatch(r"app-(\d+(?:\.\d+){2,3})", version.name)
            archive = version / "resources" / "app.asar"
            if match and not version.is_symlink() and archive.is_file() and not archive.is_symlink():
                result.append({"channel": version.parent.name, "version": match.group(1), "asar_path": str(archive.absolute())})
    return sorted(result, key=lambda item: (item["channel"], tuple(int(x) for x in item["version"].split("."))), reverse=True)
