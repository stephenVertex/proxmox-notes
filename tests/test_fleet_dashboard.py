import datetime
import importlib.machinery
import importlib.util
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


dashboard = load('fleet_dashboard', ROOT / 'web/cluster-services/cluster-services-serve.py')
collector = load('fleet_collector', ROOT / 'scripts/proxmox-dashboard-read')
CATALOG = json.loads((ROOT / 'web/cluster-services/placements.json').read_text())


def host_data(host, name=None):
    return {'host': host, 'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'guests': [{'host': host, 'key': f'{host}:qemu:101', 'vmid': 101, 'type': 'qemu',
                        'name': name or ('litellm-gateway' if host == 'sefer' else 'jeffrey-dev'),
                        'status': 'running'}]}


class InventoryTests(unittest.TestCase):
    def test_same_vmid_on_two_hosts_has_distinct_identity_and_labels(self):
        fleet = dashboard.Fleet(CATALOG, lambda host, address: host_data(host))
        fleet.refresh()
        result = fleet.snapshot()
        self.assertTrue(result['complete'])
        guests = [h['guests'][0] for h in result['hosts']]
        self.assertEqual(len({g['key'] for g in guests}), 2)
        self.assertEqual(guests[0]['services'], ['LiteLLM gateway'])
        self.assertEqual(guests[1]['services'], ['Development VM'])

    def test_reused_id_does_not_inherit_old_service(self):
        guest = host_data('sefer', 'something-else')['guests'][0]
        self.assertEqual(dashboard.service_labels(guest, CATALOG), [])

    def test_host_failure_retains_and_marks_its_last_inventory(self):
        fleet = dashboard.Fleet(CATALOG, lambda host, address: host_data(host))
        fleet.refresh()
        def fail_sefer(host, address):
            if host == 'sefer':
                raise TimeoutError()
            return host_data(host)
        fleet.fetch = fail_sefer
        fleet.refresh()
        result = fleet.snapshot()
        self.assertFalse(result['complete'])
        self.assertEqual(result['hosts'][0]['state'], 'stale')
        self.assertEqual(len(result['hosts'][0]['guests']), 1)
        self.assertEqual(result['hosts'][1]['state'], 'ok')

    def test_first_connection_failure_is_unavailable_not_empty_success(self):
        def fail(host, address):
            raise TimeoutError()
        fleet = dashboard.Fleet(CATALOG, fail)
        fleet.refresh()
        self.assertFalse(fleet.snapshot()['complete'])
        for host in fleet.snapshot()['hosts']:
            self.assertEqual(host['state'], 'unavailable')
            self.assertIsNone(host['observed_at'])

    def test_old_success_expires_and_snapshot_is_independent(self):
        fleet = dashboard.Fleet(CATALOG, lambda host, address: host_data(host))
        fleet.refresh()
        fleet.hosts['sefer']['observed_at'] = '2020-01-01T00:00:00+00:00'
        result = fleet.snapshot()
        self.assertEqual(result['hosts'][0]['state'], 'stale')
        result['hosts'][0]['guests'].clear()
        self.assertEqual(len(fleet.snapshot()['hosts'][0]['guests']), 1)

    def test_host_identity_mismatch_is_rejected(self):
        response = type('Result', (), {'returncode': 0, 'stdout': json.dumps(host_data('seykhl'))})()
        with patch.object(dashboard.subprocess, 'run', return_value=response):
            with self.assertRaises(ValueError):
                dashboard.fetch_host('sefer', '192.168.20.10')

    def test_guest_identity_mismatch_is_rejected(self):
        data = host_data('sefer')
        data['guests'][0]['key'] = 'seykhl:qemu:101'
        response = type('Result', (), {'returncode': 0, 'stdout': json.dumps(data)})()
        with patch.object(dashboard.subprocess, 'run', return_value=response):
            with self.assertRaises(ValueError):
                dashboard.fetch_host('sefer', '192.168.20.10')


class DiskCapacityTests(unittest.TestCase):
    def test_multiple_disks_exclude_cloudinit_and_iso(self):
        config = '\n'.join(['scsi0: vmdata:vm-119-disk-0,size=80G',
                            'scsi1: vmdata:vm-119-disk-1,size=300G',
                            'ide2: vmdata:vm-119-cloudinit,size=4M',
                            'ide0: local:iso/debian.iso,media=cdrom,size=4G'])
        self.assertEqual(collector.configured_disks(config, 0), (380 * 2**30, ['vmdata']))

    def test_container_mounts_and_linked_clones(self):
        config = 'rootfs: vmdata:subvol-241-disk-0,size=16G\nmp0: scratch:subvol-241-disk-1,size=0.5T'
        self.assertEqual(collector.configured_disks(config, 0), (528 * 2**30, ['scratch', 'vmdata']))
        self.assertEqual(collector.configured_disks('scsi0: vmdata:base-9120-disk-0/vm-125-disk-0,size=120G', 0), (120 * 2**30, ['vmdata']))

    def test_missing_config_retains_reported_capacity(self):
        self.assertEqual(collector.configured_disks('', 1024), (1024, []))


class StaticRoutesTests(unittest.TestCase):
    def test_existing_release_symlinks_and_assets_remain_public(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'site'
            root.mkdir()
            (root / 'index.html').write_text('services')
            (root / 'placements.json').write_text('private catalog')
            release = Path(temp) / 'release'
            (release / 'assets').mkdir(parents=True)
            (release / 'index.html').write_text('existing demo')
            (release / 'assets/app.js').write_text('existing asset')
            (root / 'demo').symlink_to(release, target_is_directory=True)
            (release / 'escape').symlink_to(root)
            fleet = dashboard.Fleet({})
            server = dashboard.http.server.ThreadingHTTPServer(
                ('127.0.0.1', 0), dashboard.make_handler(fleet, root))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = http.client.HTTPConnection(*server.server_address)
                for method, path, status, expected in [
                    ('GET', '/', 200, b'services'),
                    ('GET', '/demo/', 200, b'existing demo'),
                    ('GET', '/demo/assets/app.js?v=1', 200, b'existing asset'),
                    ('HEAD', '/demo/assets/app.js', 200, b''),
                    ('GET', '/placements.json', 404, None),
                    ('GET', '/demo/%2e%2e/placements.json', 404, None),
                    ('GET', '/demo/escape/placements.json', 404, None),
                    ('GET', '/demo/assets/', 404, None),
                ]:
                    with self.subTest(method=method, path=path):
                        connection.request(method, path)
                        response = connection.getresponse()
                        body = response.read()
                        self.assertEqual(response.status, status)
                        if expected is not None:
                            self.assertEqual(body, expected)
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
