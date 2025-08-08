#!/usr/bin/env python3
"""
QuestEd DNS問題回避用リバースプロキシサーバー
================================================================

目的: quest-ed.jp の代わりに、localhost経由で3.115.238.137にアクセス可能にする
実行: python3 reverse_proxy_server.py
アクセス: http://localhost:8080 → https://3.115.238.137 にプロキシ

この方法により、DNSの問題を回避してQuestEdにアクセス可能になります。
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import urllib.error
import ssl
import json
from urllib.parse import urlparse, parse_qs
import threading
import time

# 設定
PROXY_PORT = 8080
TARGET_SERVER = "https://3.115.238.137"
BUFFER_SIZE = 8192

class QuestEdProxyHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        """ログメッセージの出力"""
        print(f"[{time.strftime('%H:%M:%S')}] {format % args}")
    
    def do_GET(self):
        """GET リクエストの処理"""
        self.proxy_request('GET')
    
    def do_POST(self):
        """POST リクエストの処理"""
        self.proxy_request('POST')
        
    def do_PUT(self):
        """PUT リクエストの処理"""
        self.proxy_request('PUT')
        
    def do_DELETE(self):
        """DELETE リクエストの処理"""
        self.proxy_request('DELETE')
    
    def proxy_request(self, method):
        """実際のプロキシ処理"""
        try:
            # リクエストURLの構築
            target_url = f"{TARGET_SERVER}{self.path}"
            
            # リクエストボディの読み取り（POST/PUT用）
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else None
            
            # プロキシ用ヘッダーの準備
            headers = {}
            for key, value in self.headers.items():
                if key.lower() not in ['host', 'connection']:
                    headers[key] = value
            
            # Host ヘッダーを正しく設定
            headers['Host'] = '3.115.238.137'
            
            # SSL証明書検証を無効化（自己署名証明書対応）
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # リクエストの作成
            req = urllib.request.Request(
                target_url, 
                data=post_data, 
                headers=headers,
                method=method
            )
            
            # HTTPS リクエストの実行
            with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
                # レスポンスヘッダーの転送
                self.send_response(response.status)
                
                for key, value in response.headers.items():
                    if key.lower() not in ['connection', 'transfer-encoding']:
                        self.send_header(key, value)
                
                self.end_headers()
                
                # レスポンスボディの転送
                while True:
                    chunk = response.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                
                self.log_message(f"{method} {self.path} -> {response.status}")
        
        except urllib.error.HTTPError as e:
            # HTTPエラーの転送
            self.send_response(e.code)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            
            error_html = f"""
            <html><head><title>QuestEd Proxy Error {e.code}</title></head>
            <body>
            <h1>Proxy Error {e.code}</h1>
            <p>Target server returned: {e.reason}</p>
            <p>Requested URL: {self.path}</p>
            <p>Target URL: {TARGET_SERVER}{self.path}</p>
            <hr>
            <p><small>QuestEd DNS回避プロキシサーバー</small></p>
            </body></html>
            """.encode('utf-8')
            
            self.wfile.write(error_html)
            self.log_message(f"{method} {self.path} -> ERROR {e.code}: {e.reason}")
        
        except Exception as e:
            # その他のエラー
            self.send_response(500)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            
            error_html = f"""
            <html><head><title>QuestEd Proxy Server Error</title></head>
            <body>
            <h1>プロキシサーバーエラー</h1>
            <p>エラー: {str(e)}</p>
            <p>リクエストURL: {self.path}</p>
            <p>対象URL: {TARGET_SERVER}{self.path}</p>
            <hr>
            <p><small>QuestEd DNS回避プロキシサーバー</small></p>
            </body></html>
            """.encode('utf-8')
            
            self.wfile.write(error_html)
            self.log_message(f"{method} {self.path} -> EXCEPTION: {str(e)}")


class QuestEdProxyServer:
    """QuestEd専用プロキシサーバー"""
    
    def __init__(self, port=PROXY_PORT):
        self.port = port
        self.server = None
        self.server_thread = None
    
    def start(self):
        """プロキシサーバーの開始"""
        try:
            self.server = socketserver.TCPServer(("", self.port), QuestEdProxyHandler)
            self.server.allow_reuse_address = True
            
            print(f"""
=== QuestEd DNS問題回避プロキシサーバー ===
ポート: {self.port}
対象サーバー: {TARGET_SERVER}
アクセスURL: http://localhost:{self.port}

🎓 QuestEdにアクセスするには：
   http://localhost:{self.port}

サーバーを停止するには Ctrl+C を押してください
================================================
""")
            
            # サーバーを別スレッドで開始
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            return True
            
        except Exception as e:
            print(f"サーバー開始エラー: {e}")
            return False
    
    def stop(self):
        """プロキシサーバーの停止"""
        if self.server:
            print("\nプロキシサーバーを停止中...")
            self.server.shutdown()
            self.server.server_close()
            if self.server_thread:
                self.server_thread.join(timeout=5)
            print("プロキシサーバーが停止しました")
    
    def test_connection(self):
        """対象サーバーへの接続テスト"""
        try:
            print(f"対象サーバー ({TARGET_SERVER}) への接続テスト中...")
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(TARGET_SERVER)
            req.add_header('User-Agent', 'QuestEd-Proxy-Test/1.0')
            
            with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
                status = response.status
                print(f"✅ 接続成功: HTTP {status}")
                return True
                
        except Exception as e:
            print(f"❌ 接続失敗: {e}")
            return False


def main():
    """メイン実行関数"""
    proxy = QuestEdProxyServer(PROXY_PORT)
    
    # 接続テスト
    if not proxy.test_connection():
        print("対象サーバーに接続できません。サーバーが停止している可能性があります。")
        return
    
    # プロキシサーバー開始
    if not proxy.start():
        print("プロキシサーバーの開始に失敗しました")
        return
    
    try:
        # メインスレッドでキーボード割り込みを待機
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        proxy.stop()


if __name__ == "__main__":
    main()