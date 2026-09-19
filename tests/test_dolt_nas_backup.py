"""Exercise delivery/retry behavior against a fake guest and local NAS."""
import gzip
import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


class BackupDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.nas = self.root / 'nas'
        self.destination = self.nas / 'doltsvr/native'
        self.destination.mkdir(parents=True)
        self.state = self.root / 'state'
        self.state.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.name = 'doltsvr-20260914T120500Z.tar.gz'
        self.payload = gzip.compress(b'backup payload\n' * 100, mtime=0)
        self.digest = hashlib.sha256(self.payload).hexdigest()
        (self.root / 'guest').write_bytes(self.payload)
        (self.state / 'pending').write_text(self.name + '\n')
        script = (Path(__file__).resolve().parents[1] / 'scripts/backup-dolt-to-nas').read_text()
        script = script.replace('readonly nas_mount=/mnt/proxmox-backups', f'readonly nas_mount={self.nas}')
        script = script.replace('readonly state=/var/lib/dolt-nas-backup', f'readonly state={self.state}')
        script = script.replace('export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin', 'export PATH=' + shlex.quote(f'{self.bin}:{os.environ["PATH"]}'))
        self.script = self.root / 'backup'
        self.script.write_text(script)
        self.command('mountpoint', '#!/bin/sh\nexit 0\n')
        self.command('flock', '#!/bin/sh\nexit 0\n')
        self.command('df', '#!/bin/sh\nprintf "Filesystem 1024-blocks Used Available Capacity Mounted\\nfixture 999999999 0 999999999 0%% /\\n"\n')
        self.command('sha256sum', '''#!/usr/bin/env python3
import hashlib, sys
for name in sys.argv[1:]:
    with open(name, 'rb') as stream:
        print(hashlib.sha256(stream.read()).hexdigest() + '  ' + name)
''')
        self.command('ssh', '''#!/usr/bin/env python3
import hashlib, os, pathlib, sys
root = pathlib.Path(os.environ['FAKE_BACKUP_ROOT'])
action = 'create' if sys.argv[-1] == 'create' else sys.argv[-2]
with (root / 'calls').open('a') as log:
    log.write(action + '\\n')
if action == 'create':
    print('doltsvr-20260914T120500Z.tar.gz')
elif action == 'sha256':
    print(hashlib.sha256((root / 'guest').read_bytes()).hexdigest())
elif action == 'read':
    data = (root / 'guest').read_bytes()
    sys.stdout.buffer.write(data[:10] if os.environ.get('FAKE_TRUNCATE') else data)
elif action == 'ack':
    (root / 'guest').unlink()
    (root / 'acknowledged').touch()
else:
    sys.exit(2)
''')

    def command(self, name, text):
        path = self.bin / name
        path.write_text(text)
        path.chmod(0o755)

    def run_backup(self, **extra):
        return subprocess.run(['bash', str(self.script)], capture_output=True, text=True,
                              env=dict(os.environ, FAKE_BACKUP_ROOT=str(self.root), **extra), timeout=15)

    def assert_delivered(self, result, name):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.destination / name).read_bytes(), self.payload)
        self.assertEqual((self.destination / (name + '.sha256')).read_text(), f'{self.digest}  {name}\n')
        self.assertTrue((self.root / 'acknowledged').exists())
        self.assertFalse((self.state / 'pending').exists())
        self.assertIn(name, (self.state / 'last-success').read_text())

    def test_normal_delivery(self):
        self.assert_delivered(self.run_backup(), self.name)

    def test_corrupt_existing_archive_is_preserved_and_recovered(self):
        (self.destination / self.name).write_bytes(b'corrupt NAS object')
        recovery = self.name.removesuffix('.tar.gz') + '.sha256-' + self.digest + '.tar.gz'
        self.assert_delivered(self.run_backup(), recovery)
        self.assertEqual((self.destination / self.name).read_bytes(), b'corrupt NAS object')

    def test_existing_verified_recovery_is_reused_without_transfer(self):
        (self.destination / self.name).write_bytes(b'corrupt')
        recovery = self.name.removesuffix('.tar.gz') + '.sha256-' + self.digest + '.tar.gz'
        (self.destination / recovery).write_bytes(self.payload)
        self.assert_delivered(self.run_backup(), recovery)
        self.assertNotIn('read', (self.root / 'calls').read_text().splitlines())

    def test_bad_transfer_keeps_guest_and_pending_without_ack(self):
        result = self.run_backup(FAKE_TRUNCATE='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum mismatch', result.stderr)
        self.assertTrue((self.root / 'guest').exists())
        self.assertTrue((self.state / 'pending').exists())
        self.assertFalse((self.destination / self.name).exists())
        self.assertFalse((self.root / 'acknowledged').exists())

    def test_corrupt_checksum_sidecar_is_preserved(self):
        (self.destination / self.name).write_bytes(self.payload)
        sidecar = self.destination / (self.name + '.sha256')
        sidecar.write_text('bad checksum\n')
        recovery = self.name.removesuffix('.tar.gz') + '.sha256-' + self.digest + '.tar.gz'
        self.assert_delivered(self.run_backup(), recovery)
        self.assertEqual(sidecar.read_text(), 'bad checksum\n')

    def test_corrupt_deterministic_recovery_uses_new_name(self):
        (self.destination / self.name).write_bytes(b'bad canonical')
        recovery = self.name.removesuffix('.tar.gz') + '.sha256-' + self.digest + '.tar.gz'
        (self.destination / recovery).write_bytes(b'bad recovery')
        result = self.run_backup()
        self.assertEqual(result.returncode, 0, result.stderr)
        delivered = (self.state / 'last-success').read_text().split()[2]
        self.assertIn('.retry-', delivered)
        self.assert_delivered(result, delivered)
        self.assertEqual((self.destination / recovery).read_bytes(), b'bad recovery')


if __name__ == '__main__':
    unittest.main()
