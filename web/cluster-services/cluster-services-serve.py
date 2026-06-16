#!/usr/bin/env python3
"""Static server for cluster-services index page."""
import http.server
import socketserver
import os

PORT = 8092
DIRECTORY = os.path.expanduser("~/cluster-services")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

if __name__ == '__main__':
    os.chdir(DIRECTORY)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Serving cluster-services from {DIRECTORY} at http://0.0.0.0:{PORT}")
        httpd.serve_forever()
