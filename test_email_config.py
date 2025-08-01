#!/usr/bin/env python3
"""
メール設定テストスクリプト
実際にメールを送信する前に設定を確認
"""
import os
import sys
from dotenv import load_dotenv

# プロジェクトルートをPATHに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# .envファイルを読み込み
load_dotenv()

def check_email_configuration():
    """メール設定の確認（送信なし）"""
    print("=== QuestEd メール設定確認 ===\n")
    
    # 環境変数の確認
    email_vars = {
        'EMAIL_METHOD': os.getenv('EMAIL_METHOD'),
        'SMTP_SERVER': os.getenv('SMTP_SERVER'),
        'SMTP_PORT': os.getenv('SMTP_PORT'),
        'SMTP_USER': os.getenv('SMTP_USER'),
        'SMTP_PASSWORD': os.getenv('SMTP_PASSWORD'),
        'TEST_EMAIL': os.getenv('TEST_EMAIL')
    }
    
    all_set = True
    for var, value in email_vars.items():
        if value and value not in ['your_email@gmail.com', 'your_16_char_app_password', 'test_recipient@example.com']:
            # 機密情報は部分表示
            if 'PASSWORD' in var:
                display_value = value[:4] + '*' * (len(value) - 8) + value[-4:]
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: 未設定または初期値のまま")
            all_set = False
    
    print("\n=== 設定手順 ===")
    if not all_set:
        print("1. .envファイルを開いて以下を設定してください:")
        print("   - SMTP_USER: あなたのGmailアドレス")
        print("   - SMTP_PASSWORD: Gmailアプリパスワード（16文字）")
        print("   - TEST_EMAIL: テストメールの送信先")
        print("\n2. Gmailアプリパスワードの取得方法:")
        print("   a. Googleアカウントにログイン")
        print("   b. セキュリティ設定で2段階認証を有効化")
        print("   c. https://myaccount.google.com/apppasswords でアプリパスワード生成")
        print("   d. 生成された16文字のパスワードをSMTP_PASSWORDに設定")
    else:
        print("✅ すべての環境変数が設定されています！")
        print("\n次のステップ:")
        print("1. 実際にテストメールを送信する場合:")
        print("   python -c \"from app.utils.email_sender import test_email_configuration; test_email_configuration()\"")
        print("\n2. または、このスクリプトに --send オプションを付けて実行:")
        print("   python test_email_config.py --send")
    
    return all_set

def send_test_email():
    """テストメール送信"""
    try:
        # ログ機能が有効な場合はLoggedEmailSenderを使用
        email_log_enabled = os.getenv("EMAIL_LOG_ENABLED", "false").lower() == "true"
        
        if email_log_enabled:
            print("📝 ログ記録機能が有効です - データベースに送信履歴を記録します")
            try:
                from app.utils.logged_email_sender import LoggedEmailSender
                sender = LoggedEmailSender()
            except ImportError:
                print("⚠️ LoggedEmailSender が利用できません - 通常のEmailSenderを使用します")
                from app.utils.email_sender import EmailSender
                sender = EmailSender()
        else:
            print("📧 通常のメール送信モードです")
            from app.utils.email_sender import EmailSender
            sender = EmailSender()
        test_recipient = os.getenv('TEST_EMAIL', 'test@example.com')
        
        print(f"\n📧 テストメールを {test_recipient} に送信中...")
        
        success, message = sender.send(
            recipients=[test_recipient],
            subject="QuestEd メールテスト",
            html_body="""
            <html>
            <body>
                <h2>QuestEd メールテスト</h2>
                <p>このメールは、QuestEdのメール設定テストとして送信されています。</p>
                <p>正常に受信できた場合、メール設定は正しく構成されています。</p>
                <hr>
                <p><small>QuestEd - 学習管理システム</small></p>
            </body>
            </html>
            """
        )
        
        if success:
            print(f"✅ 成功: {message}")
            print(f"📬 {test_recipient} の受信トレイを確認してください。")
        else:
            print(f"❌ 失敗: {message}")
            
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        print("\nFlaskアプリケーションのコンテキストが必要な場合:")
        print("from app import create_app; app = create_app(); app.app_context().push()")

if __name__ == "__main__":
    import sys
    
    # 設定確認
    config_ok = check_email_configuration()
    
    # --send オプションがある場合はメール送信
    if '--send' in sys.argv and config_ok:
        send_test_email()
    elif '--send' in sys.argv and not config_ok:
        print("\n❌ 環境変数が正しく設定されていません。上記の手順に従って設定してください。")