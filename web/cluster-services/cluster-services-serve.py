#!/usr/bin/env python3
"""Service directory and cached live inventory of two standalone Proxmox hosts."""
import concurrent.futures
import copy
import datetime
import http.server
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from urllib.parse import unquote, urlsplit

DIRECTORY = Path(os.environ.get('CLUSTER_SERVICES_DIRECTORY', '~/cluster-services')).expanduser()
PORT = int(os.environ.get('CLUSTER_SERVICES_PORT', '8092'))
HOSTS = {'sefer': '192.168.20.10', 'seykhl': '192.168.20.202'}
REFRESH_SECONDS = 10
STALE_SECONDS = 90
CPU_STALE_SECONDS = 30
KEY = Path('~/.ssh/proxmox-dashboard').expanduser()


def service_labels(guest, catalog):
    placement = catalog.get(guest['key'])
    if placement and guest['name'] in placement['names']:
        return placement['services']
    for prefix, label in (
        ('yesod-controller-', 'Yesod controller'), ('yesod-runner-', 'Yesod runner'),
        ('yesod-gate-', 'Yesod gate'), ('test-db-', 'PostgreSQL test database'),
        ('testdb-', 'PostgreSQL test database'), ('ysg-', 'Semantic graph experiment'),
        ('makor-runner-', 'GitLab runner'),
    ):
        if guest['name'].startswith(prefix):
            return [label]
    return []


def fetch_host(host, address):
    result = subprocess.run(
        ['ssh', '-i', str(KEY), '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
         '-o', 'ConnectTimeout=5', '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=1',
         '-o', 'StrictHostKeyChecking=yes', '-o', f'UserKnownHostsFile={DIRECTORY / "proxmox_known_hosts"}',
         f'root@{address}', 'inventory'],
        capture_output=True, text=True, timeout=25,
    )
    if result.returncode:
        raise RuntimeError('Host inventory could not be reached')
    data = json.loads(result.stdout)
    if data.get('host') != host or not isinstance(data.get('guests'), list):
        raise ValueError('Host returned an invalid inventory')
    datetime.datetime.fromisoformat(data['observed_at'])
    for guest in data['guests']:
        if guest.get('host') != host or guest.get('type') not in ('qemu', 'lxc'):
            raise ValueError('Guest identity does not match host')
        if guest.get('key') != f'{host}:{guest["type"]}:{int(guest["vmid"])}':
            raise ValueError('Guest inventory key is invalid')
    return data


class Fleet:
    def __init__(self, catalog, fetch=fetch_host):
        self.catalog = catalog
        self.fetch = fetch
        self.lock = threading.Lock()
        self.wakeup = threading.Event()
        self.hosts = {name: {'host': name, 'address': address, 'state': 'loading', 'guests': [],
                             'observed_at': None, 'error': None} for name, address in HOSTS.items()}

    def refresh(self):
        def collect(host, address):
            try:
                data = self.fetch(host, address)
                for guest in data['guests']:
                    guest['services'] = service_labels(guest, self.catalog)
                with self.lock:
                    self.hosts[host] = {**data, 'address': address, 'state': 'ok', 'error': None}
            except Exception as exc:
                print(f'Inventory refresh failed for {host}: {type(exc).__name__}', flush=True)
                with self.lock:
                    old = self.hosts[host]
                    self.hosts[host] = {**old, 'state': 'stale' if old['observed_at'] else 'unavailable',
                                        'error': 'Unable to refresh this host. Retained readings may be out of date.'}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda pair: collect(*pair), HOSTS.items()))

    def snapshot(self):
        with self.lock:
            hosts = copy.deepcopy(list(self.hosts.values()))
        now = datetime.datetime.now(datetime.timezone.utc)
        for host in hosts:
            if host['observed_at']:
                age = (now - datetime.datetime.fromisoformat(host['observed_at'])).total_seconds()
                if age > STALE_SECONDS and host['state'] == 'ok':
                    host['state'] = 'stale'
                    host['error'] = 'This host inventory has not refreshed recently.'
            for guest in host['guests']:
                if guest.get('cpu'):
                    guest['cpu']['state'] = 'ok' if (host['state'] == 'ok' and
                        0 <= now.timestamp() - guest['cpu']['sampled_at'] <= CPU_STALE_SECONDS) else 'stale'
        return {'hosts': hosts, 'complete': all(host['state'] == 'ok' for host in hosts),
                'refresh_seconds': REFRESH_SECONDS, 'stale_seconds': STALE_SECONDS,
                'cpu_window_seconds': 60, 'cpu_stale_seconds': CPU_STALE_SECONDS}

    def run(self):
        while True:
            started = time.monotonic()
            self.refresh()
            self.wakeup.wait(max(1, REFRESH_SECONDS - (time.monotonic() - started)))
            self.wakeup.clear()


def make_handler(fleet, directory=DIRECTORY):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def public_path(self):
            path = unquote(urlsplit(self.path).path)
            if path in ('/', '/index.html', '/fleet.js', '/fleet.css'):
                return True
            parts = [part for part in path.split('/') if part]
            if not parts or any(part.startswith('.') or '\\' in part for part in parts):
                return False
            # Existing demo apps are public subdirectories, often symlinks to
            # versioned releases. Keep their index pages and nested assets working
            # without exposing the root catalog, host pins, or server source.
            app = Path(directory) / parts[0]
            return app.is_dir() and app.joinpath(*parts[1:]).resolve().is_relative_to(app.resolve())

        def list_directory(self, path):
            self.send_error(404)
            return None

        def do_GET(self):
            if urlsplit(self.path).path == '/_fleet.json':
                data = json.dumps(fleet.snapshot(), separators=(',', ':')).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(data)
                return
            if not self.public_path():
                self.send_error(404)
                return
            super().do_GET()

        def do_HEAD(self):
            if not self.public_path():
                self.send_error(404)
                return
            super().do_HEAD()

        def end_headers(self):
            self.send_header('X-Content-Type-Options', 'nosniff')
            if urlsplit(self.path).path != '/_fleet.json':
                self.send_header('Cache-Control', 'no-cache')
            super().end_headers()

    return Handler


if __name__ == '__main__':
    catalog = json.loads((DIRECTORY / 'placements.json').read_text())
    fleet = Fleet(catalog)
    threading.Thread(target=fleet.run, daemon=True).start()
    server = http.server.ThreadingHTTPServer(('0.0.0.0', PORT), make_handler(fleet))
    print(f'Serving cluster services and fleet inventory on :{PORT}', flush=True)
    server.serve_forever()
