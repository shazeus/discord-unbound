import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / 'src'
sys.path.insert(0, str(SRC))
import app


class LauncherTests(unittest.TestCase):
    def test_open_installation_is_never_patched(self):
        with tempfile.TemporaryDirectory() as tmp:
            asar = Path(tmp) / 'app-1.2.3/resources/app.asar'
            with patch.object(app, 'discord_processes', return_value=[{'pid': 1, 'path': str(asar.parent.parent / 'Discord.exe')}]):
                with patch('patcher.patch') as mutate:
                    with self.assertRaises(RuntimeError): app.apply_to(asar)
                    mutate.assert_not_called()

    def test_unknown_process_path_blocks_modification(self):
        with patch.object(app, 'discord_processes', return_value=[{'pid': 1, 'path': None}]):
            with self.assertRaises(RuntimeError): app.assert_closed(Path('fake/resources/app.asar'))

    def test_inactive_new_version_can_be_patched(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / 'app-1.0.1/Discord.exe'
            new = Path(tmp) / 'app-1.0.2/resources/app.asar'
            with patch.object(app, 'discord_processes', return_value=[{'pid': 1, 'path': str(old)}]):
                app.assert_closed(new)

    def test_restore_disables_observer_and_explicit_patch_reenables(self):
        with tempfile.TemporaryDirectory() as tmp:
            asar = Path(tmp) / 'app-1.2.3/resources/app.asar'
            with patch.object(app, 'STATE', Path(tmp)), patch.object(app, 'discord_processes', return_value=[]):
                with patch('patcher.restore', return_value={'status': 'restored'}):
                    app.restore_from(asar)
                self.assertTrue(app.disabled_marker(asar).exists())
                with patch('patcher.patch', return_value={'status': 'patched'}), patch('patcher.inspect', return_value={'patched': False}), patch.object(app, 'hook_source', return_value='test'):
                    app.apply_to(asar)
                self.assertFalse(app.disabled_marker(asar).exists())

    def test_new_hook_migrates_only_through_verified_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            asar = Path(tmp) / 'app-1.2.3/resources/app.asar'
            with patch.object(app, 'STATE', Path(tmp)), patch.object(app, 'discord_processes', return_value=[]), patch.object(app, 'hook_source', return_value='new hook'):
                with patch('patcher.inspect', return_value={'patched': True, 'manifest': {'hook_sha256': 'old'}}), patch('patcher.restore', side_effect=RuntimeError('hash mismatch')) as restore, patch('patcher.patch') as mutate:
                    with self.assertRaises(RuntimeError): app.apply_to(asar)
                    restore.assert_called_once()
                    mutate.assert_not_called()


if __name__ == '__main__': unittest.main()
