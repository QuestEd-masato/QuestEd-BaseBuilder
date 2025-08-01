#!/usr/bin/env python3
"""
Webルートの動作テスト
実際のHTTPリクエストをシミュレート
"""
import os
from app import create_app
from app.models import User

app = create_app()

# テストクライアントを作成
client = app.test_client()

with app.app_context():
    # テスト用の教師ユーザーを取得（または作成）
    teacher = User.query.filter_by(role='teacher').first()
    
    if teacher:
        print(f"テスト用教師ユーザー: {teacher.username} (ID: {teacher.id})")
        
        # ログインなしでアクセス
        print("\n=== ログインなしでのアクセステスト ===")
        response = client.get('/teacher/curriculums/8')
        print(f"ステータスコード: {response.status_code}")
        if response.status_code == 500:
            print("500エラーが発生")
            # エラーページの内容を確認
            if response.data:
                data_str = response.data.decode('utf-8')
                if 'Internal Server Error' in data_str:
                    print("内部サーバーエラーページが表示されました")
        elif response.status_code == 302:
            print(f"リダイレクト先: {response.headers.get('Location')}")
        
        # Flask-Loginの正式なログインフローを使用
        print("\n=== 正式ログインフローでのテスト ===")
        login_response = client.post('/login', data={
            'username': teacher.username,
            'password': 'testpassword'  # 実際のパスワード設定が必要
        }, follow_redirects=False)
        print(f"ログイン試行結果: {login_response.status_code}")
        
        # 教師のクラスを検索
        print("\n=== 教師のクラス権限確認 ===")
        from app.models import Class
        teacher_classes = Class.query.filter_by(teacher_id=teacher.id).all()
        if teacher_classes:
            print(f"教師のクラス一覧:")
            for cls in teacher_classes:
                print(f"  - クラス{cls.id}: {cls.name}")
            # 最初のクラスを使用
            test_class_id = teacher_classes[0].id
            print(f"\nテスト用クラスID: {test_class_id}")
        else:
            print("教師にクラスが割り当てられていません")
            test_class_id = 8  # デフォルト
        
        # クラス8の詳細確認
        class_8 = Class.query.get(8)
        if class_8:
            print(f"クラス8: {class_8.name} (教師ID: {class_8.teacher_id})")
            if class_8.teacher_id == teacher.id:
                print("✓ 教師はクラス8にアクセス可能")
            else:
                print(f"✗ 教師はクラス8にアクセス不可 (権限なし: 教師ID {class_8.teacher_id} vs {teacher.id})")
        else:
            print("✗ クラス8が存在しません")
        
        # 教師のクラスでテスト
        if teacher_classes:
            print(f"\n=== 教師のクラス{test_class_id}でのテスト ===")
            response = client.get(f'/teacher/curriculums/{test_class_id}')
            print(f"ステータスコード: {response.status_code}")
            if response.status_code == 500:
                print("✗ 500エラーが発生 - テンプレート修正が未完了")
            elif response.status_code == 302:
                print(f"リダイレクト先: {response.headers.get('Location')} (ログイン必要)")
            elif response.status_code == 200:
                print("✓ 正常応答（権限があれば表示される）")
        
        # 直接的なテスト（認証なし）
        print("\n=== 直接ルートテスト（クラス8）===")
        response = client.get('/teacher/curriculums/8')
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 302:
            print(f"リダイレクト先: {response.headers.get('Location')}")
            print("リダイレクトの理由を調査...")
        elif response.status_code == 200:
            print("✓ 正常にページが表示されました")
        elif response.status_code == 500:
            print("✗ 500エラーが発生")
            # デバッグモードでエラーの詳細を取得
            app.config['TESTING'] = True
            app.config['DEBUG'] = True
            response = client.get('/teacher/curriculums/8')
            if response.data:
                data_str = response.data.decode('utf-8')
                # エラーメッセージを探す
                import re
                error_pattern = r'<pre[^>]*>(.*?)</pre>'
                matches = re.findall(error_pattern, data_str, re.DOTALL)
                if matches:
                    print("\nエラー詳細:")
                    for match in matches[:2]:  # 最初の2つのエラーメッセージを表示
                        print(match.strip())
    else:
        print("教師ユーザーが見つかりません")