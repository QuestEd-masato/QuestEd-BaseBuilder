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

# BaseBuilderメインページにアクセス
bb_response = session.get('http://localhost:5000/basebuilder/')
print(f'BaseBuilder response status: {bb_response.status_code}')
if bb_response.status_code >= 400:
    print('BaseBuilder error response:', bb_response.text[:500])
    
# BaseBuilder problemsページにアクセス
bb_problems = session.get('http://localhost:5000/basebuilder/problems')
print(f'BaseBuilder problems response status: {bb_problems.status_code}')
if bb_problems.status_code >= 400:
    print('Problems error response:', bb_problems.text[:500])