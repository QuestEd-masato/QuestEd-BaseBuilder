"""
ログ記録機能付きEmailSenderラッパー
既存のEmailSenderクラスを拡張し、送信履歴をデータベースに記録

使用方法:
    from app.utils.logged_email_sender import LoggedEmailSender
    sender = LoggedEmailSender()
    sender.send(recipients, subject, html_body)
"""
import os
import logging
from datetime import datetime
from typing import List, Tuple, Optional

from app.utils.email_sender import EmailSender
from app.models.email_log import EmailLog
from extensions import db

logger = logging.getLogger(__name__)


class LoggedEmailSender(EmailSender):
    """EmailSenderのログ記録対応ラッパークラス"""
    
    def __init__(self):
        super().__init__()
        # ログ記録を有効にするかどうかを環境変数で制御
        self.log_enabled = os.getenv("EMAIL_LOG_ENABLED", "true").lower() == "true"
    
    def send(self, recipients: List[str], subject: str, html_body: str, 
             email_type: str = "notification", user_id: Optional[int] = None,
             template_name: Optional[str] = None, template_variables: Optional[dict] = None,
             **kwargs) -> Tuple[bool, str]:
        """
        メール送信（ログ記録付き）
        
        Args:
            recipients: 受信者メールアドレスのリスト
            subject: 件名
            html_body: HTML形式の本文
            email_type: メール種別 (verification/reset_password/notification/reminder/report)
            user_id: 受信者のユーザーID（オプション）
            template_name: 使用テンプレート名（オプション）
            template_variables: テンプレート変数（オプション）
            **kwargs: その他のオプション引数
            
        Returns:
            (success: bool, message: str) のタプル
        """
        email_log = None
        
        try:
            # ログ記録が有効で、アプリケーションコンテキスト内の場合のみログを作成
            if self.log_enabled and self._is_in_app_context():
                email_log = self._create_log_entry(
                    recipients, subject, html_body, email_type,
                    user_id, template_name, template_variables
                )
            
            # 基底クラスのsendメソッドを呼び出し
            success, message = super().send(recipients, subject, html_body, **kwargs)
            
            # ログの更新
            if email_log:
                self._update_log_entry(email_log, success, message)
            
            return success, message
            
        except Exception as e:
            logger.error(f"Email sending error: {str(e)}")
            if email_log:
                self._update_log_entry(email_log, False, str(e))
            return False, str(e)
    
    def _is_in_app_context(self) -> bool:
        """Flaskアプリケーションコンテキスト内かどうかを確認"""
        try:
            from flask import current_app
            return current_app is not None
        except:
            return False
    
    def _create_log_entry(self, recipients: List[str], subject: str, html_body: str,
                         email_type: str, user_id: Optional[int],
                         template_name: Optional[str], template_variables: Optional[dict]) -> Optional[EmailLog]:
        """EmailLogエントリを作成"""
        try:
            # 複数受信者の場合、それぞれログエントリを作成
            email_logs = []
            for recipient in recipients:
                email_log = EmailLog(
                    recipient_email=recipient,
                    recipient_id=user_id,
                    sender_email=os.getenv("SMTP_USER", "noreply@quested.com"),
                    email_type=email_type,
                    subject=subject,
                    body=html_body[:1000] if len(html_body) > 1000 else html_body,  # 本文は最初の1000文字のみ保存
                    template_name=template_name,
                    template_variables=template_variables,
                    status="pending",
                    created_at=datetime.utcnow()
                )
                db.session.add(email_log)
                email_logs.append(email_log)
            
            # トランザクションをコミット
            db.session.commit()
            
            # 簡単のため、最初のログエントリを返す
            return email_logs[0] if email_logs else None
            
        except Exception as e:
            logger.error(f"Failed to create email log: {str(e)}")
            db.session.rollback()
            return None
    
    def _update_log_entry(self, email_log: EmailLog, success: bool, message: str) -> None:
        """EmailLogエントリを更新"""
        if not email_log:
            return
            
        try:
            if success:
                # メッセージからSMTP IDを抽出（可能な場合）
                smtp_id = None
                if "Message Id:" in message:
                    smtp_id = message.split("Message Id:")[1].strip()
                email_log.mark_as_sent(smtp_id)
            else:
                email_log.mark_as_failed(message)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update email log: {str(e)}")
            db.session.rollback()


# 既存の関数との互換性維持のためのヘルパー関数
def send_confirmation_email_with_log(user_email: str, user_id: int, token: str, username: str) -> bool:
    """
    確認メールを送信（ログ記録付き）
    既存のsend_confirmation_emailとの互換性維持
    """
    from flask import url_for
    
    sender = LoggedEmailSender()
    
    # 確認URLを構築
    confirm_url = url_for(
        "auth.verify_email", user_id=user_id, token=token, _external=True
    )
    
    # HTML形式のメール本文
    html_body = f"""
    <html>
        <body>
            <h2>QuestEd - メールアドレスの確認</h2>
            <p>{username} 様</p>
            <p>QuestEdへのご登録ありがとうございます。</p>
            <p>以下のボタンをクリックして、メールアドレスの確認を完了してください。</p>
            <p style="margin: 20px 0;">
                <a href="{confirm_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    メールアドレスを確認
                </a>
            </p>
            <p>または、以下のURLをコピーしてブラウザのアドレスバーに貼り付けてください：</p>
            <p style="font-size: 12px; color: #666; word-break: break-all;">{confirm_url}</p>
            <p><small>このリンクは24時間有効です。</small></p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                ※このメールに心当たりがない場合は無視してください。
            </p>
            <p>QuestEd運営チーム</p>
        </body>
    </html>
    """
    
    success, message = sender.send(
        recipients=[user_email],
        subject="QuestEd - メールアドレスの確認",
        html_body=html_body,
        email_type="verification",
        user_id=user_id,
        template_name="email_verification",
        template_variables={
            "username": username,
            "token": token,
            "confirm_url": confirm_url
        }
    )
    
    if not success:
        logger.error(f"メール送信エラー: {message}")
    
    return success


def send_reset_password_email_with_log(user_email: str, user_id: int, token: str, username: str) -> bool:
    """
    パスワードリセットメールを送信（ログ記録付き）
    既存のsend_reset_password_emailとの互換性維持
    """
    from flask import url_for
    
    sender = LoggedEmailSender()
    
    # リセットURLを構築
    reset_url = url_for(
        "auth.reset_password", user_id=user_id, token=token, _external=True
    )
    
    # HTML形式のメール本文
    html_body = f"""
    <html>
        <body>
            <h2>QuestEd - パスワードリセット</h2>
            <p>{username} 様</p>
            <p>QuestEdのパスワードリセットリクエストを受け付けました。</p>
            <p>以下のボタンをクリックして、新しいパスワードを設定してください。</p>
            <p style="margin: 20px 0;">
                <a href="{reset_url}" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    パスワードをリセット
                </a>
            </p>
            <p>または、以下のURLをコピーしてブラウザのアドレスバーに貼り付けてください：</p>
            <p style="font-size: 12px; color: #666; word-break: break-all;">{reset_url}</p>
            <p><small>このリンクは1時間のみ有効です。</small></p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                ※このメールに心当たりがない場合は無視してください。<br>
                リクエストしていない場合、アカウントセキュリティを確認することをお勧めします。
            </p>
            <p>QuestEd運営チーム</p>
        </body>
    </html>
    """
    
    success, message = sender.send(
        recipients=[user_email],
        subject="QuestEd - パスワードリセット",
        html_body=html_body,
        email_type="reset_password",
        user_id=user_id,
        template_name="password_reset",
        template_variables={
            "username": username,
            "token": token,
            "reset_url": reset_url
        }
    )
    
    if not success:
        logger.error(f"メール送信エラー: {message}")
    
    return success