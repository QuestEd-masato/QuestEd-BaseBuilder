#!/usr/bin/env python3
"""
WSL2接続テスト用のシンプルHTTPサーバー
"""
import http.server
import socketserver
import threading
import time

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        print(f"Received request: {self.path}")
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = """
        <html>
        <head><title>WSL2 Test Server</title></head>
        <body>
            <h1>WSL2 Connection Test - SUCCESS!</h1>
            <p>This server is running on WSL2</p>
            <p>IP: 172.20.251.113</p>
            <p>Port: 8090</p>
            <p>Time: """ + str(time.ctime()) + """</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

PORT = 8090
Handler = MyHandler

print(f"Starting HTTP server on port {PORT}")
print(f"Access URLs:")
print(f"  - http://localhost:{PORT}")
print(f"  - http://127.0.0.1:{PORT}")
print(f"  - http://172.20.251.113:{PORT}")

with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    print(f"Server running at http://0.0.0.0:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")