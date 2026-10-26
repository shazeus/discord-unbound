"""Synthetic registry and ASAR fixtures; no real startup or Discord changes."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import app
import patcher
import persistence


def fixture(root, version):
    archive = root / ('app-' + version) / 'resources/app.asar'
    archive.parent.mkdir(parents=True)
    files = {'package.json': json.dumps({'name': 'discord', 'main': 'main.js'}).encode(),
             'main.js': b'module.exports = 1;'}
    header, payload = {'files': {}}, b''
    for name, content in files.items():
        header['files'][name] = {'size': len(content), 'offset': str(len(payload))}
        payload += content
    archive.write_bytes(patcher._encode(header, payload))
    (archive.parent.parent / 'Discord.exe').write_bytes(b'MZ' + patcher.FUSE_SENTINEL + bytes([1, 8]) + b'00000000')
    return archive


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.state = self.base / 'state'
        self.root = self.base / 'Discord'
        self.registry = {}
        self.runner = [str(self.base / 'durable/DiscordUnbound.exe')]
        for name, value in [('get_run', lambda n: self.registry.get(n)),
                            ('set_run', self.set_run), ('durable_runner', lambda _: self.runner)]:
            mocked = patch.object(persistence, name, value)
            mocked.start(); self.addCleanup(mocked.stop)

    def set_run(self, name, value):
        if value is None:
            self.registry.pop(name, None)
        else:
            self.registry[name] = value

    def test_registration_survives_reloading_state_and_restores_original_startup(self):
        original = {'value': '"' + str(self.root / 'Update.exe') + '" --processStart Discord.exe', 'kind': 1}
        self.registry['Discord'] = original
        persistence.enable(self.state, self.root)
        self.assertIn('--resume', self.registry['DiscordUnbound']['value'])
        self.assertIn('--managed-root', self.registry['Discord']['value'])
        self.assertIn(persistence.key(self.root), persistence.read(self.state)['roots'])
        # Simulate next invocation: state/registry are the only continuity source.
        persistence.enable(self.state, self.root)
        persistence.disable(self.state, self.root)
        self.assertEqual(self.registry, {'Discord': original})

    def test_does_not_enable_discord_autolaunch_when_user_did_not_have_it(self):
        persistence.enable(self.state, self.root)
        self.assertNotIn('Discord', self.registry)
        self.assertIn('DiscordUnbound', self.registry)

    def test_external_startup_change_survives_enable_and_disable(self):
        self.registry['Discord'] = {'value': str(self.root / 'Update.exe'), 'kind': 1}
        persistence.enable(self.state, self.root)
        external = {'value': 'other-user-command', 'kind': 1}
        self.registry['Discord'] = external
        persistence.enable(self.state, self.root)
        self.assertEqual(self.registry['Discord'], external)
        persistence.disable(self.state, self.root)
        self.assertEqual(self.registry['Discord'], external)

    def test_unknown_own_startup_name_is_not_overwritten(self):
        self.registry['DiscordUnbound'] = {'value': 'foreign-command', 'kind': 1}
        with self.assertRaises(RuntimeError): persistence.enable(self.state, self.root)
        self.assertEqual(self.registry['DiscordUnbound']['value'], 'foreign-command')

    def test_removing_one_channel_keeps_other_channel_registered(self):
        persistence.enable(self.state, self.root)
        other = self.base / 'DiscordCanary'
        persistence.enable(self.state, other)
        persistence.disable(self.state, self.root)
        self.assertIn('DiscordUnbound', self.registry)
        self.assertEqual(len(persistence.read(self.state)['roots']), 1)

    def test_latest_numeric_version_is_patched_before_exact_executable_launch(self):
        old = fixture(self.root, '1.0.9')
        new = fixture(self.root, '1.0.12')
        (self.root / 'Update.exe').write_bytes(b'fixture')
        with patch.object(app, 'STATE', self.state), patch.object(app, 'discord_processes', return_value=[]), patch.object(app, 'hook_source', return_value='exports.ready=Promise.resolve();'), patch.object(persistence, 'spawn'), patch.object(app.subprocess, 'Popen') as spawn:
            app.launch(old)
        self.assertFalse(patcher.inspect(old)['patched'])
        self.assertTrue(patcher.inspect(new)['patched'])
        self.assertEqual(spawn.call_args.args[0], [str(new.parent.parent / 'Discord.exe')])

    def test_resume_observer_waits_for_stable_file_then_patches_only_enrolled_root(self):
        archive = fixture(self.root, '1.0.20')
        other = fixture(self.base / 'other' / 'Discord', '1.0.30')
        persistence.enable(self.state, self.root)
        seen, pending = {}, {}
        with patch.object(app, 'STATE', self.state), patch.object(app, 'find_asars', return_value=[archive, other]), patch.object(app, 'discord_processes', return_value=[]), patch.object(app, 'hook_source', return_value='exports.ready=Promise.resolve();'):
            app.watcher_step(seen, pending)
            self.assertFalse(patcher.inspect(archive)['patched'])
            app.watcher_step(seen, pending)
            self.assertTrue(patcher.inspect(archive)['patched'])
            self.assertFalse(patcher.inspect(other)['patched'])

    def test_active_new_version_waits_until_closed_without_mutation(self):
        archive = fixture(self.root, '1.0.20')
        persistence.enable(self.state, self.root)
        seen, pending = {}, {}
        with patch.object(app, 'STATE', self.state), patch.object(app, 'find_asars', return_value=[archive]), patch.object(app, 'discord_processes', return_value=[{'path': str(archive.parent.parent / 'Discord.exe')}]), patch.object(app, 'hook_source', return_value='exports.ready=Promise.resolve();'):
            app.watcher_step(seen, pending); app.watcher_step(seen, pending)
            self.assertFalse(patcher.inspect(archive)['patched'])
            with patch.object(app, 'discord_processes', return_value=[]):
                app.watcher_step(seen, pending)
            self.assertTrue(patcher.inspect(archive)['patched'])

    def test_active_verified_patch_is_recognized_without_rewriting(self):
        archive = fixture(self.root, '1.0.20')
        hook = 'exports.ready=Promise.resolve();'
        patcher.patch(archive, hook)
        before = archive.read_bytes()
        persistence.enable(self.state, self.root)
        seen, pending = {}, {}
        with patch.object(app, 'STATE', self.state), patch.object(app, 'find_asars', return_value=[archive]), patch.object(app, 'discord_processes', return_value=[{'path': str(archive.parent.parent / 'Discord.exe')}]), patch.object(app, 'hook_source', return_value=hook), patch.object(app, 'apply_to') as mutate:
            app.watcher_step(seen, pending); app.watcher_step(seen, pending)
            mutate.assert_not_called()
        self.assertIn(str(archive), seen)
        self.assertEqual(archive.read_bytes(), before)


if __name__ == '__main__': unittest.main()
