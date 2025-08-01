#!/usr/bin/env python3
"""
シンプルなテストサーバー
QuestEdアプリケーションの起動問題を診断するため
"""
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1>QuestEd Test Server</h1><p>Flask is working properly!</p>'

@app.route('/test')
def test():
    return {'status': 'ok', 'message': 'Test endpoint working'}

if __name__ == '__main__':
    print("Starting test server on http://127.0.0.1:5002")
    app.run(host='127.0.0.1', port=5002, debug=True)