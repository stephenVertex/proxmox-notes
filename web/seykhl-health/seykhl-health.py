#!/usr/bin/env python3
"""Seykhl health dashboard - serves live cluster metrics."""
import http.server
import socketserver
import json
import subprocess
import os

PORT = 8093

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>Seykhl Health Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            line-height: 1.6;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #fff; margin-bottom: 8px; font-size: 2rem; }
        .subtitle { color: #888; margin-bottom: 20px; }
        .timestamp { color: #666; font-size: 0.85rem; margin-bottom: 30px; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }
        .card {
            background: #16213e;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #0f3460;
        }
        .card h2 {
            font-size: 1.1rem;
            color: #e94560;
            margin-bottom: 15px;
            border-bottom: 1px solid #0f3460;
            padding-bottom: 8px;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #1a1a3e;
        }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #888; font-size: 0.9rem; }
        .metric-value {
            font-family: 'Courier New', monospace;
            font-weight: 600;
            color: #fff;
        }
        .metric-value.good { color: #4CAF50; }
        .metric-value.warn { color: #FFC107; }
        .metric-value.danger { color: #e94560; }
        .vm-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }
        .vm-table th {
            text-align: left;
            padding: 8px;
            color: #e94560;
            border-bottom: 1px solid #0f3460;
        }
        .vm-table td {
            padding: 8px;
            border-bottom: 1px solid #1a1a3e;
        }
        .vm-table tr:hover { background: #1a1a3e; }
        .status-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 6px;
        }
        .status-running { background: #4CAF50; }
        .status-stopped { background: #e94560; }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #1a1a3e;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 5px;
        }
        .progress-fill {
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s;
        }
        .progress-fill.good { background: #4CAF50; }
        .progress-fill.warn { background: #FFC107; }
        .progress-fill.danger { background: #e94560; }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #0f3460;
            color: #666;
            font-size: 0.85rem;
            text-align: center;
        }
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #e94560;
            text-decoration: none;
            font-size: 0.9rem;
        }
        .back-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <a href="http://dertog:8092" class="back-link">← Back to Cluster Services</a>
        <h1>Seykhl Health Dashboard</h1>
        <p class="subtitle">Proxmox node health and cluster metrics</p>
        <p class="timestamp">Last updated: {{timestamp}} | Auto-refreshes every 30s</p>

        <div class="grid">
            <div class="card">
                <h2>Node Status</h2>
                <div class="metric">
                    <span class="metric-label">Hostname</span>
                    <span class="metric-value">{{hostname}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">CPU</span>
                    <span class="metric-value">{{cpuinfo}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Kernel</span>
                    <span class="metric-value">{{kernel}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Uptime</span>
                    <span class="metric-value">{{uptime}}</span>
                </div>
            </div>

            <div class="card">
                <h2>Load & Memory</h2>
                <div class="metric">
                    <span class="metric-label">Load (1m)</span>
                    <span class="metric-value {{load_class}}">{{load1}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Load (5m)</span>
                    <span class="metric-value">{{load5}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Load (15m)</span>
                    <span class="metric-value">{{load15}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Memory Used</span>
                    <span class="metric-value {{mem_class}}">{{mem_used}} / {{mem_total}} ({{mem_pct}}%)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill {{mem_class}}" style="width: {{mem_pct}}%"></div>
                </div>
            </div>

            <div class="card">
                <h2>Storage</h2>
                <div class="metric">
                    <span class="metric-label">Thin Pool</span>
                    <span class="metric-value">{{pool_name}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Size</span>
                    <span class="metric-value">{{pool_size}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Used</span>
                    <span class="metric-value {{pool_class}}">{{pool_used}} ({{pool_pct}}%)</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Available</span>
                    <span class="metric-value good">{{pool_free}}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill {{pool_class}}" style="width: {{pool_pct}}%"></div>
                </div>
            </div>

            <div class="card">
                <h2>VM Summary</h2>
                <div class="metric">
                    <span class="metric-label">Total VMs</span>
                    <span class="metric-value">{{vm_count}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Running</span>
                    <span class="metric-value good">{{vm_running}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Stopped</span>
                    <span class="metric-value {{stopped_class}}">{{vm_stopped}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total RAM Allocated</span>
                    <span class="metric-value">{{total_ram}} GB</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Disk Allocated</span>
                    <span class="metric-value">{{total_disk}} GB</span>
                </div>
            </div>
        </div>

        <div class="card" style="margin-top: 20px;">
            <h2>Virtual Machines</h2>
            <table class="vm-table">
                <thead>
                    <tr>
                        <th>VMID</th>
                        <th>Name</th>
                        <th>Status</th>
                        <th>RAM</th>
                        <th>Disk</th>
                        <th>IP</th>
                    </tr>
                </thead>
                <tbody>
                    {{vm_rows}}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Seykhl Health Dashboard | Proxmox node: seykhl (192.168.0.202)</p>
            <p>Data fetched live via SSH from Proxmox host</p>
        </div>
    </div>
</body>
</html>'''


def run_ssh_command(cmd):
    """Run a command on seykhl via SSH."""
    try:
        result = subprocess.run(
            ['ssh', 'root@seykhl', cmd],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        return None


def run_ssh_json(cmd):
    """Run a command on seykhl via SSH and parse JSON."""
    try:
        result = subprocess.run(
            ['ssh', 'root@seykhl', cmd],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        return None


def get_status_data():
    """Fetch all status data from seykhl."""
    data = {}
    
    # Node status
    status = run_ssh_json('pvesh get /nodes/seykhl/status --output-format json')
    if status:
        data['hostname'] = 'seykhl'
        data['cpuinfo'] = f"{status['cpuinfo']['cpus']} cores @ {status['cpuinfo']['mhz'][:4]}MHz"
        data['kernel'] = status['current-kernel']['release']
        data['load1'] = status['loadavg'][0]
        data['load5'] = status['loadavg'][1]
        data['load15'] = status['loadavg'][2]
        
        # Memory (in bytes, convert to GB)
        mem = status.get('memory', {})
        mem_used = mem.get('used', 0) / (1024**3)
        mem_total = mem.get('total', 0) / (1024**3)
        data['mem_used'] = f"{mem_used:.1f}"
        data['mem_total'] = f"{mem_total:.1f}"
        data['mem_pct'] = int((mem_used / mem_total) * 100) if mem_total > 0 else 0
    else:
        data['hostname'] = 'seykhl (unreachable)'
        data['cpuinfo'] = 'N/A'
        data['kernel'] = 'N/A'
        data['load1'] = 'N/A'
        data['load5'] = 'N/A'
        data['load15'] = 'N/A'
        data['mem_used'] = '0'
        data['mem_total'] = '0'
        data['mem_pct'] = 0
    
    # Load class
    try:
        load1 = float(data['load1'])
        data['load_class'] = 'danger' if load1 > 4.0 else 'warn' if load1 > 2.0 else 'good'
    except:
        data['load_class'] = 'good'
    
    # Memory class
    mem_pct = data['mem_pct']
    data['mem_class'] = 'danger' if mem_pct > 90 else 'warn' if mem_pct > 70 else 'good'
    
    # Uptime
    uptime = run_ssh_command("uptime -p | sed 's/up //'")
    data['uptime'] = uptime or 'N/A'
    
    # Storage
    storage = run_ssh_command("pvesm status | grep local-lvm | awk '{print $3, $4, $5, $6}'")
    if storage:
        parts = storage.split()
        data['pool_name'] = 'local-lvm'
        data['pool_size'] = parts[0] if len(parts) > 0 else 'N/A'
        data['pool_used'] = parts[1] if len(parts) > 1 else 'N/A'
        data['pool_free'] = parts[2] if len(parts) > 2 else 'N/A'
        try:
            data['pool_pct'] = int(parts[3].replace('%', '')) if len(parts) > 3 else 0
        except:
            data['pool_pct'] = 0
    else:
        data['pool_name'] = 'N/A'
        data['pool_size'] = 'N/A'
        data['pool_used'] = 'N/A'
        data['pool_free'] = 'N/A'
        data['pool_pct'] = 0
    
    pool_pct = data['pool_pct']
    data['pool_class'] = 'danger' if pool_pct > 85 else 'warn' if pool_pct > 60 else 'good'
    
    # VMs
    vms = run_ssh_json('pvesh get /nodes/seykhl/qemu --output-format json')
    if vms:
        data['vm_count'] = len(vms)
        data['vm_running'] = sum(1 for vm in vms if vm.get('status') == 'running')
        data['vm_stopped'] = sum(1 for vm in vms if vm.get('status') != 'running')
        
        total_ram = sum(vm.get('maxmem', 0) for vm in vms) / (1024**3)
        total_disk = sum(vm.get('maxdisk', 0) for vm in vms) / (1024**3)
        data['total_ram'] = f"{total_ram:.0f}"
        data['total_disk'] = f"{total_disk:.0f}"
        
        # Build VM rows
        rows = []
        for vm in sorted(vms, key=lambda x: x.get('vmid', 0)):
            vmid = vm.get('vmid', 'N/A')
            name = vm.get('name', 'N/A')
            status = vm.get('status', 'unknown')
            ram = vm.get('maxmem', 0) / (1024**3)
            disk = vm.get('maxdisk', 0) / (1024**3)
            ip = vm.get('net0', 'N/A')
            
            status_dot = 'status-running' if status == 'running' else 'status-stopped'
            
            rows.append(f'<tr><td>{vmid}</td><td>{name}</td>'
                       f'<td><span class="status-dot {status_dot}"></span>{status}</td>'
                       f'<td>{ram:.0f}GB</td><td>{disk:.0f}GB</td><td>{ip}</td></tr>')
        data['vm_rows'] = '\n'.join(rows)
    else:
        data['vm_count'] = 0
        data['vm_running'] = 0
        data['vm_stopped'] = 0
        data['total_ram'] = '0'
        data['total_disk'] = '0'
        data['vm_rows'] = '<tr><td colspan="6">Unable to fetch VM data</td></tr>'
    
    data['stopped_class'] = 'danger' if data['vm_stopped'] > 0 else 'good'
    
    return data


class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            data = get_status_data()
            data['timestamp'] = subprocess.run(['date'], capture_output=True, text=True).stdout.strip()
            
            html = HTML_TEMPLATE
            for key, value in data.items():
                html = html.replace('{{' + key + '}}', str(value))
            
            self.wfile.write(html.encode())
        elif self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            data = get_status_data()
            data['timestamp'] = subprocess.run(['date'], capture_output=True, text=True).stdout.strip()
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with socketserver.TCPServer(("0.0.0.0", PORT), HealthHandler) as httpd:
        print(f"Serving seykhl health dashboard at http://0.0.0.0:{PORT}")
        httpd.serve_forever()
