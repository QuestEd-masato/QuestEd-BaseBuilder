#!/usr/bin/env python3
import requests
import sys
import re

# セッションを作成
session = requests.Session()

# ログインページからCSRFトークンを取得
login_page = session.get('http://localhost:5000/login')
if login_page.status_code != 200:
    print(f'Error accessing login page: {login_page.status_code}')
    sys.exit(1)

# CSRFトークンを抽出
csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', login_page.text)
if not csrf_match:
    print('Could not find CSRF token')
    sys.exit(1)

csrf_token = csrf_match.group(1)

# ログインデータ
login_data = {
    'username': 'teacher01',
    'password': 'teacher01',
    'csrf_token': csrf_token
}

# ログイン実行
login_response = session.post('http://localhost:5000/login', data=login_data)
print(f'Login response status: {login_response.status_code}')

# BaseBuilder機能をテスト
endpoints = [
    '/basebuilder/',
    '/basebuilder/problems',
    '/basebuilder/categories',
    '/basebuilder/dashboard',
    '/basebuilder/problem/create',
    '/basebuilder/texts',
    '/basebuilder/sessions',
    '/basebuilder/progress',
    '/basebuilder/analytics'
]

print("Testing BaseBuilder endpoints:")
for endpoint in endpoints:
    response = session.get(f'http://localhost:5000{endpoint}')
    print(f'{endpoint}: {response.status_code}')
    if response.status_code >= 400:
        print(f'  Error: {response.text[:200]}...')