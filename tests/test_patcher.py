"""Synthetic fixtures only: tests never read or alter installed Discord."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("bridge_patcher", Path(__file__).parents[1] / "src" / "patcher.py")
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


class PatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.app = self.root / "Discord" / "app-1.0.10"
        self.path = self.app / "resources" / "app.asar"
        self.path.parent.mkdir(parents=True)
        self.exe = self.app / "Discord.exe"
        self.exe.write_bytes(b"MZfixture" + p.FUSE_SENTINEL + bytes([1, 8]) + b"00000000")
        self.original = self.fixture()
        self.path.write_bytes(self.original)
        self.hook = "exports.ready = Promise.resolve();"

    def fixture(self, main="bundle.js"):
        package = json.dumps({"name": "fixture", "main": main, "custom": {"value": 5}}).encode()
        source = b"module.exports = 'untouched';\x00\xff"
        header = {"files": {"package.json": {"size": len(package), "offset": "0"}, "bundle.js": {"size": len(source), "offset": str(len(package))}, "native.node": {"size": 100, "unpacked": True}}}
        return p._encode(header, package + source)

    def test_round_trip_preserves_original_payload_and_unpacked(self):
        before_header, before_payload, before_entries = p._decode(self.original)
        result = p.patch(self.path, self.hook)
        self.assertEqual(result["status"], "patched")
        after_header, after_payload, after_entries = p._decode(self.path.read_bytes())
        self.assertEqual(after_payload[:len(before_payload)], before_payload)
        self.assertEqual(after_entries["native.node"], before_entries["native.node"])
        self.assertEqual(after_entries["bundle.js"], before_entries["bundle.js"])
        package = json.loads(p._content(after_entries["package.json"], after_payload))
        self.assertEqual(package["main"], "bridge-entry.cjs")
        wrapper = p._content(after_entries["bridge-entry.cjs"], after_payload).decode()
        self.assertIn('.ready.then(() => require("./bundle.js"))', wrapper)
        for name in ("package.json", "bridge-entry.cjs", "bridge-hook.cjs", p.MARKER):
            content = p._content(after_entries[name], after_payload)
            self.assertEqual(after_entries[name]["integrity"]["hash"], p._sha(content))
        self.assertTrue(p.inspect(self.path)["patched"])
        p.restore(self.path)
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertFalse(p.inspect(self.path)["patched"])

    def test_idempotent_and_repeat_after_restore(self):
        p.patch(self.path, self.hook)
        first = self.path.read_bytes()
        self.assertEqual(p.patch(self.path, self.hook)["status"], "already_patched")
        self.assertEqual(self.path.read_bytes(), first)
        with self.assertRaises(p.PatchError):
            p.patch(self.path, self.hook + "// change")
        p.restore(self.path)
        p.patch(self.path, self.hook)
        self.assertEqual(self.path.read_bytes(), first)

    def test_corrupted_backup_never_restored(self):
        p.patch(self.path, self.hook)
        patched = self.path.read_bytes()
        _, backup, _ = p._paths(self.path)
        backup.write_bytes(b"corrupted")
        with self.assertRaises(p.PatchError):
            p.restore(self.path)
        self.assertEqual(self.path.read_bytes(), patched)

    def test_modified_current_never_overwritten(self):
        p.patch(self.path, self.hook)
        tampered = self.path.read_bytes() + b"tamper"
        self.path.write_bytes(tampered)
        for action in (lambda: p.restore(self.path), lambda: p.patch(self.path, self.hook)):
            with self.assertRaises(p.PatchError):
                action()
        self.assertEqual(self.path.read_bytes(), tampered)

    def test_unknown_backup_never_overwritten(self):
        _, backup, _ = p._paths(self.path)
        backup.write_bytes(b"operator data")
        with self.assertRaises(p.PatchError):
            p.patch(self.path, self.hook)
        self.assertEqual(backup.read_bytes(), b"operator data")
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_unsafe_main_and_paths_rejected(self):
        for main in ("../escape.js", "C:/escape.js", "\\escape.js", "bundle", "./../bundle.js"):
            self.path.write_bytes(self.fixture(main))
            with self.assertRaises(p.PatchError, msg=main):
                p.patch(self.path, self.hook)
        for name in ("../escape", "a/b", "a\\b", "C:evil", ".."):
            data = p._encode({"files": {name: {"size": 1, "offset": "0"}}}, b"x")
            with self.assertRaises(p.PatchError, msg=name):
                p._decode(data)

    def test_invalid_offsets_and_truncation_rejected(self):
        for data in (b"", self.original[:10], self.original[:18], p._encode({"files": {"x": {"size": 100, "offset": "0"}}}, b"x")):
            with self.assertRaises(p.PatchError):
                p._decode(data)

    def test_unknown_or_enabled_fuses_block_mutation(self):
        for suffix in (b"", bytes([1, 8]) + b"00001000", bytes([2, 8]) + b"00000000", bytes([1, 8]) + b"00002000"):
            self.exe.write_bytes(b"MZfixture" + p.FUSE_SENTINEL + suffix)
            with self.assertRaises(p.PatchError):
                p.patch(self.path, self.hook)
            self.assertEqual(self.path.read_bytes(), self.original)
            self.assertFalse(p._paths(self.path)[1].exists())

    def test_numeric_version_discovery(self):
        for version in ("1.0.9", "1.0.100", "bad", "1.0"):
            target = self.root / "Discord" / ("app-" + version) / "resources" / "app.asar"
            target.parent.mkdir(parents=True)
            target.write_bytes(self.original)
        found = p.discover(self.root)
        self.assertEqual([x["version"] for x in found], ["1.0.100", "1.0.10", "1.0.9"])
        self.assertEqual(len(p.discover(self.app)), 1)
        self.assertEqual(len(p.discover(self.app.parent)), 3)

    def test_nested_commonjs_main_and_integrity_blocks(self):
        package = b'{"main":"./bootstrap/start.cjs"}'
        source = b"module.exports = 7;"
        header = {"files": {"package.json": {"size": len(package), "offset": "0"}, "bootstrap": {"files": {"start.cjs": {"size": len(source), "offset": str(len(package))}}}}}
        self.path.write_bytes(p._encode(header, package + source))
        p.patch(self.path, self.hook)
        _, payload, entries = p._decode(self.path.read_bytes())
        self.assertIn(b'require("./bootstrap/start.cjs")', p._content(entries["bridge-entry.cjs"], payload))
        for name in p.RESERVED | {"package.json"}:
            content = p._content(entries[name], payload)
            integrity = entries[name]["integrity"]
            self.assertEqual(integrity["blocks"], [p._sha(content)])

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(p.PatchError):
            p._load_json(b'{"files":{},"files":{}}')

    def test_existing_operation_lock_blocks_mutation(self):
        lock = self.path.with_name(self.path.name + ".discordbridge.lock")
        lock.write_bytes(b"owned")
        with self.assertRaises(p.PatchError):
            p.patch(self.path, self.hook)
        self.assertEqual(lock.read_bytes(), b"owned")
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_legacy_backup_can_be_verified_and_restored(self):
        p.patch(self.path, self.hook)
        _, backup, state = p._paths(self.path)
        legacy_backup = self.path.with_name(self.path.name + '.discordbridge.original')
        legacy_state = self.path.with_name(self.path.name + '.discordbridge.json')
        backup.rename(legacy_backup)
        state.rename(legacy_state)
        self.assertEqual(p.patch(self.path, self.hook)['status'], 'already_patched')
        p.restore(self.path)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_conflicting_legacy_and_new_backups_are_not_overwritten(self):
        p.patch(self.path, self.hook)
        patched = self.path.read_bytes()
        self.path.with_name(self.path.name + '.discordbridge.original').write_bytes(b'legacy')
        with self.assertRaises(p.PatchError): p.restore(self.path)
        self.assertEqual(self.path.read_bytes(), patched)


if __name__ == "__main__":
    unittest.main()
