#!/usr/bin/env python3
"""Database details dashboard for PostgreSQL and Dolt."""
import http.server
import socketserver
import json
import subprocess
import os
import configparser
import urllib.parse
from datetime import datetime

PORT = 8094

BASE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>{title}</title>
    <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E🗄️%3C/text%3E%3C/svg%3E">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #fff; margin-bottom: 8px; font-size: 2rem; }}
        .subtitle {{ color: #888; margin-bottom: 10px; }}
        .timestamp {{ color: #666; font-size: 0.85rem; margin-bottom: 25px; }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #e94560;
            text-decoration: none;
            font-size: 0.9rem;
        }}
        .back-link:hover {{ text-decoration: underline; }}
        .nav {{
            margin-bottom: 25px;
            display: flex;
            gap: 15px;
        }}
        .nav a {{
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
            border: 1px solid #0f3460;
            color: #888;
        }}
        .nav a.active {{
            background: #16213e;
            color: #e94560;
            border-color: #e94560;
        }}
        .nav a:hover {{ background: #16213e; }}
        .card {{
            background: #16213e;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #0f3460;
            margin-bottom: 20px;
        }}
        .card h2 {{
            font-size: 1.2rem;
            color: #e94560;
            margin-bottom: 15px;
            border-bottom: 1px solid #0f3460;
            padding-bottom: 8px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .summary-item {{
            background: #1a1a3e;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .summary-value {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #4CAF50;
            font-family: 'Courier New', monospace;
        }}
        .summary-label {{
            color: #888;
            font-size: 0.85rem;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        th {{
            text-align: left;
            padding: 10px;
            color: #e94560;
            border-bottom: 1px solid #0f3460;
            font-weight: 600;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #1a1a3e;
        }}
        tr:hover {{ background: #1a1a3e; }}
        .metric-value {{
            font-family: 'Courier New', monospace;
            color: #fff;
        }}
        .size-bar {{
            width: 100%;
            height: 8px;
            background: #1a1a3e;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }}
        .size-fill {{
            height: 100%;
            background: #e94560;
            border-radius: 4px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #0f3460;
            color: #666;
            font-size: 0.85rem;
            text-align: center;
        }}
        .status-ok {{ color: #4CAF50; }}
        .status-warn {{ color: #FFC107; }}
        .status-error {{ color: #e94560; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="http://dertog:8092" class="back-link">← Back to Cluster Services</a>
        <h1>{title}</h1>
        <p class="subtitle">{subtitle}</p>
        <p class="timestamp">Last updated: {timestamp}</p>
        
        <div class="nav">
            <a href="/">Overview</a>
            <a href="/postgres" class="{pg_active}">PostgreSQL</a>
            <a href="/dolt" class="{dolt_active}">Dolt</a>
        </div>
        
        {content}
        
        <div class="footer">
            <p>Database Details Dashboard | Self-hosted on dertog</p>
        </div>
    </div>
</body>
</html>'''


def read_config():
    """Read database credentials from existing config files."""
    config = {}
    
    def strip_quotes(value):
        """Strip surrounding quotes from TOML-style config values."""
        if value:
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
        return value
    
    # PostgreSQL from ~/.config/yesod/database.toml
    pg_config = configparser.ConfigParser()
    pg_config.read(os.path.expanduser('~/.config/yesod/database.toml'))
    if pg_config.has_section('database'):
        dsn = strip_quotes(pg_config.get('database', 'dsn', fallback=''))
        if dsn:
            parsed = urllib.parse.urlparse(dsn)
            config['postgres'] = {
                'host': parsed.hostname or 'yesod-postgres-server',
                'port': parsed.port or 5432,
                'user': parsed.username or 'stephen',
                'password': parsed.password or '',
                'database': parsed.path.lstrip('/') or 'postgres'
            }
    
    # Dolt from ~/.config/yesod/dolt.toml
    dolt_config = configparser.ConfigParser()
    dolt_config.read(os.path.expanduser('~/.config/yesod/dolt.toml'))
    if dolt_config.has_section('server'):
        config['dolt'] = {
            'host': strip_quotes(dolt_config.get('server', 'host', fallback='192.168.0.150')),
            'port': dolt_config.getint('server', 'port', fallback=3306),
            'user': strip_quotes(dolt_config.get('server', 'user', fallback='yesoduser')),
            'password': strip_quotes(dolt_config.get('server', 'password', fallback='')),
        }
    
    return config


def format_bytes(size_bytes):
    """Format bytes to human readable."""
    if size_bytes == 0:
        return '0 B'
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size_bytes) < 1024.0:
            return f'{size_bytes:.1f} {unit}'
        size_bytes /= 1024.0
    return f'{size_bytes:.1f} PB'


def get_postgres_data():
    """Fetch PostgreSQL database details."""
    import psycopg2
    config = read_config().get('postgres', {})
    
    if not config:
        return {'error': 'No PostgreSQL config found'}
    
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database='postgres'
        )
        cur = conn.cursor()
        
        # Database list with sizes
        cur.execute('''
            SELECT datname, pg_database_size(datname), pg_size_pretty(pg_database_size(datname))
            FROM pg_database
            WHERE datistemplate = false
            ORDER BY pg_database_size(datname) DESC;
        ''')
        databases = []
        total_size = 0
        for row in cur.fetchall():
            databases.append({
                'name': row[0],
                'size_bytes': row[1],
                'size_pretty': row[2]
            })
            total_size += row[1]
        
        # Recent activity from pg_stat_database
        cur.execute('''
            SELECT datname, xact_commit, xact_rollback, tup_inserted, tup_updated, tup_deleted,
                   COALESCE(stats_reset, NOW()) as stats_reset
            FROM pg_stat_database
            WHERE datname NOT IN ('template0', 'template1', 'postgres')
            ORDER BY xact_commit DESC;
        ''')
        activity = []
        for row in cur.fetchall():
            activity.append({
                'name': row[0],
                'commits': row[1],
                'rollbacks': row[2],
                'inserted': row[3],
                'updated': row[4],
                'deleted': row[5],
                'stats_reset': row[6].strftime('%Y-%m-%d %H:%M') if row[6] else 'N/A'
            })
        
        # Get active connections
        cur.execute('''
            SELECT datname, COUNT(*) as count
            FROM pg_stat_activity
            WHERE datname IS NOT NULL
            GROUP BY datname
            ORDER BY count DESC;
        ''')
        connections = {row[0]: row[1] for row in cur.fetchall()}
        
        cur.close()
        conn.close()
        
        return {
            'databases': databases,
            'total_size': total_size,
            'total_size_pretty': format_bytes(total_size),
            'count': len(databases),
            'activity': activity,
            'connections': connections
        }
    except Exception as e:
        return {'error': str(e)}


def get_dolt_data():
    """Fetch Dolt database details."""
    import pymysql
    config = read_config().get('dolt', {})
    
    if not config:
        return {'error': 'No Dolt config found'}
    
    try:
        conn = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password']
        )
        cur = conn.cursor()
        
        # Database list
        cur.execute('SHOW DATABASES;')
        all_dbs = [row[0] for row in cur.fetchall()]
        # Filter out system databases
        system_dbs = {'information_schema', 'mysql', 'performance_schema'}
        databases = [db for db in all_dbs if db not in system_dbs]
        
        # Table counts per database
        db_details = []
        for db in databases:
            try:
                cur.execute(f'USE `{db}`;')
                cur.execute('''
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = %s AND table_type = 'BASE TABLE';
                ''', (db,))
                table_count = cur.fetchone()[0]
                
                # Recent activity from dolt_log
                cur.execute('SELECT commit_hash, committer, message, date FROM dolt_log LIMIT 1;')
                recent = cur.fetchone()
                
                db_details.append({
                    'name': db,
                    'tables': table_count,
                    'recent_commit': recent[2] if recent else 'N/A',
                    'recent_committer': recent[1] if recent else 'N/A',
                    'recent_date': recent[3].strftime('%Y-%m-%d %H:%M') if recent and recent[3] else 'N/A'
                })
            except Exception as e:
                db_details.append({
                    'name': db,
                    'tables': 0,
                    'recent_commit': 'Error',
                    'recent_committer': 'N/A',
                    'recent_date': str(e)[:50]
                })
        
        cur.close()
        conn.close()
        
        return {
            'databases': db_details,
            'count': len(databases),
            'total_tables': sum(db['tables'] for db in db_details)
        }
    except Exception as e:
        return {'error': str(e)}


def render_overview():
    """Render the overview page."""
    config = read_config()
    
    content = f'''
        <div class="card">
            <h2>Database Servers</h2>
            <div class="summary">
                <div class="summary-item">
                    <div class="summary-value status-ok">PostgreSQL</div>
                    <div class="summary-label">yesod-postgres-server:5432</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value status-ok">Dolt</div>
                    <div class="summary-label">doltsvr:3306</div>
                </div>
            </div>
        </div>
        <div class="card">
            <h2>Pages</h2>
            <table>
                <tr><th>Page</th><th>Description</th></tr>
                <tr><td><a href="/postgres" style="color:#e94560;text-decoration:none;">PostgreSQL Details</a></td>
                    <td>Database list, sizes, recent activity, and connections</td></tr>
                <tr><td><a href="/dolt" style="color:#e94560;text-decoration:none;">Dolt Details</a></td>
                    <td>Database list, table counts, and recent commits</td></tr>
            </table>
        </div>
    '''
    return content


def render_postgres():
    """Render PostgreSQL details page."""
    data = get_postgres_data()
    
    if 'error' in data:
        return f'<div class="card"><h2>Error</h2><p class="status-error">{data["error"]}</p></div>'
    
    max_size = max(db['size_bytes'] for db in data['databases']) if data['databases'] else 1
    
    db_rows = ''
    for db in data['databases']:
        pct = (db['size_bytes'] / max_size) * 100 if max_size > 0 else 0
        db_rows += f'''
            <tr>
                <td>{db['name']}</td>
                <td class="metric-value">{db['size_pretty']}</td>
                <td>
                    <div class="size-bar"><div class="size-fill" style="width: {pct}%"></div></div>
                </td>
            </tr>
        '''
    
    activity_rows = ''
    for act in data['activity'][:10]:
        conn_count = data['connections'].get(act['name'], 0)
        activity_rows += f'''
            <tr>
                <td>{act['name']}</td>
                <td class="metric-value">{act['commits']:,}</td>
                <td class="metric-value">{act['inserted']:,}</td>
                <td class="metric-value">{act['updated']:,}</td>
                <td class="metric-value">{act['deleted']:,}</td>
                <td class="metric-value">{conn_count}</td>
                <td>{act['stats_reset']}</td>
            </tr>
        '''
    
    content = f'''
        <div class="summary">
            <div class="summary-item">
                <div class="summary-value">{data['count']}</div>
                <div class="summary-label">Databases</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{data['total_size_pretty']}</div>
                <div class="summary-label">Total Size</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{sum(data['connections'].values())}</div>
                <div class="summary-label">Active Connections</div>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h2>Database Sizes</h2>
            <table>
                <tr><th>Database</th><th>Size</th><th>Relative</th></tr>
                {db_rows}
            </table>
        </div>
        
        <div class="card">
            <h2>Recent Activity</h2>
            <table>
                <tr>
                    <th>Database</th>
                    <th>Commits</th>
                    <th>Inserts</th>
                    <th>Updates</th>
                    <th>Deletes</th>
                    <th>Connections</th>
                    <th>Stats Reset</th>
                </tr>
                {activity_rows}
            </table>
        </div>
    '''
    return content


def render_dolt():
    """Render Dolt details page."""
    data = get_dolt_data()
    
    if 'error' in data:
        return f'<div class="card"><h2>Error</h2><p class="status-error">{data["error"]}</p></div>'
    
    db_rows = ''
    for db in data['databases']:
        db_rows += f'''
            <tr>
                <td>{db['name']}</td>
                <td class="metric-value">{db['tables']}</td>
                <td>{db['recent_commit']}</td>
                <td>{db['recent_committer']}</td>
                <td>{db['recent_date']}</td>
            </tr>
        '''
    
    content = f'''
        <div class="summary">
            <div class="summary-item">
                <div class="summary-value">{data['count']}</div>
                <div class="summary-label">Databases</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{data['total_tables']}</div>
                <div class="summary-label">Total Tables</div>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h2>Databases & Recent Activity</h2>
            <table>
                <tr>
                    <th>Database</th>
                    <th>Tables</th>
                    <th>Latest Commit</th>
                    <th>Committer</th>
                    <th>Date</th>
                </tr>
                {db_rows}
            </table>
        </div>
        
        <div class="card">
            <h2>Note</h2>
            <p style="color: #888; font-size: 0.9rem;">
                Dolt database sizes are not available via SQL query. Table counts and recent commit activity 
                are shown as activity proxies. For exact disk usage, filesystem access to /var/lib/doltdb is required.
            </p>
        </div>
    '''
    return content


class DBHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            title = 'Database Details'
            subtitle = 'PostgreSQL and Dolt database overview'
            content = render_overview()
            pg_active = ''
            dolt_active = ''
        elif self.path == '/postgres':
            title = 'PostgreSQL Details'
            subtitle = 'yesod-postgres-server (192.168.0.155:5432)'
            content = render_postgres()
            pg_active = 'active'
            dolt_active = ''
        elif self.path == '/dolt':
            title = 'Dolt Details'
            subtitle = 'doltsvr (192.168.0.150:3306)'
            content = render_dolt()
            pg_active = ''
            dolt_active = 'active'
        elif self.path == '/api/postgres':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_postgres_data()).encode())
            return
        elif self.path == '/api/dolt':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_dolt_data()).encode())
            return
        else:
            self.send_response(404)
            self.end_headers()
            return
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        html = BASE_HTML.format(
            title=title,
            subtitle=subtitle,
            timestamp=timestamp,
            pg_active=pg_active,
            dolt_active=dolt_active,
            content=content
        )
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), DBHandler) as httpd:
        print(f"Serving database details at http://0.0.0.0:{PORT}")
        httpd.serve_forever()
