from datetime import datetime

from extensions import db


class EmailLog(db.Model):
    """メール送信ログテーブル"""

    __tablename__ = "email_logs"

    id = db.Column(db.Integer, primary_key=True, comment="ログID")
    recipient_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, comment="受信者ID"
    )
    recipient_email = db.Column(db.String(100), nullable=False, comment="受信者メールアドレス")
    sender_email = db.Column(
        db.String(100), default="noreply@quested.com", comment="送信者メールアドレス"
    )
    email_type = db.Column(
        db.Enum("verification", "reset_password", "notification", "reminder", "report"),
        nullable=False,
        comment="メール種類",
    )
    subject = db.Column(db.String(200), nullable=False, comment="件名")
    body = db.Column(db.Text, comment="本文")
    template_name = db.Column(db.String(100), comment="使用テンプレート名")
    template_variables = db.Column(db.JSON, comment="テンプレート変数")
    status = db.Column(
        db.Enum("pending", "sent", "failed", "bounced"),
        default="pending",
        comment="送信状況",
    )
    error_message = db.Column(db.Text, comment="エラーメッセージ")
    smtp_message_id = db.Column(db.String(255), comment="SMTP メッセージID")
    retry_count = db.Column(db.Integer, default=0, comment="リトライ回数")
    max_retries = db.Column(db.Integer, default=3, comment="最大リトライ回数")
    scheduled_at = db.Column(db.DateTime, nullable=True, comment="送信予定日時")
    sent_at = db.Column(db.DateTime, nullable=True, comment="送信日時")
    opened_at = db.Column(db.DateTime, nullable=True, comment="開封日時")
    clicked_at = db.Column(db.DateTime, nullable=True, comment="クリック日時")
    bounced_at = db.Column(db.DateTime, nullable=True, comment="バウンス日時")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="作成日時")
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新日時"
    )

    # インデックス
    __table_args__ = (
        db.Index("idx_recipient_email", "recipient_email"),
        db.Index("idx_email_type", "email_type"),
        db.Index("idx_status", "status"),
        db.Index("idx_scheduled_at", "scheduled_at"),
        db.Index("idx_sent_at", "sent_at"),
        db.Index("idx_created_at", "created_at"),
        db.Index("idx_recipient_id", "recipient_id"),
    )

    # リレーションシップ
    recipient = db.relationship(
        "User", backref=db.backref("email_logs", cascade="all, delete-orphan")
    )

    def to_dict(self):
        """辞書形式に変換"""
        return {
            "id": self.id,
            "recipient_id": self.recipient_id,
            "recipient_email": self.recipient_email,
            "sender_email": self.sender_email,
            "email_type": self.email_type,
            "subject": self.subject,
            "body": self.body,
            "template_name": self.template_name,
            "template_variables": self.template_variables,
            "status": self.status,
            "error_message": self.error_message,
            "smtp_message_id": self.smtp_message_id,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "scheduled_at": self.scheduled_at.isoformat()
            if self.scheduled_at
            else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "clicked_at": self.clicked_at.isoformat() if self.clicked_at else None,
            "bounced_at": self.bounced_at.isoformat() if self.bounced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def mark_as_sent(self, smtp_message_id=None):
        """送信完了としてマーク"""
        self.status = "sent"
        self.sent_at = datetime.utcnow()
        if smtp_message_id:
            self.smtp_message_id = smtp_message_id
        self.updated_at = datetime.utcnow()

    def mark_as_failed(self, error_message):
        """送信失敗としてマーク"""
        self.retry_count += 1
        self.error_message = error_message
        self.updated_at = datetime.utcnow()

        if self.retry_count >= self.max_retries:
            self.status = "failed"
        else:
            self.status = "pending"
            # リトライ用の遅延時間を設定（指数バックオフ）
            from datetime import timedelta

            delay_minutes = 2**self.retry_count
            self.scheduled_at = datetime.utcnow() + timedelta(minutes=delay_minutes)

    def mark_as_bounced(self):
        """バウンスとしてマーク"""
        self.status = "bounced"
        self.bounced_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_as_opened(self):
        """開封としてマーク"""
        if not self.opened_at:
            self.opened_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    def mark_as_clicked(self):
        """クリックとしてマーク"""
        if not self.clicked_at:
            self.clicked_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

        # 開封もマーク（クリックは開封を含意）
        self.mark_as_opened()

    def is_deliverable(self):
        """再送信可能かチェック"""
        return (
            self.status in ["pending", "failed"] and self.retry_count < self.max_retries
        )

    def get_delivery_rate(self):
        """配信率を計算（同一受信者の統計）"""
        total_emails = EmailLog.query.filter_by(
            recipient_email=self.recipient_email
        ).count()
        delivered_emails = EmailLog.query.filter_by(
            recipient_email=self.recipient_email, status="sent"
        ).count()

        if total_emails > 0:
            return (delivered_emails / total_emails) * 100
        return 0.0

    def get_open_rate(self):
        """開封率を計算（同一受信者の統計）"""
        sent_emails = EmailLog.query.filter_by(
            recipient_email=self.recipient_email, status="sent"
        ).count()
        opened_emails = EmailLog.query.filter(
            EmailLog.recipient_email == self.recipient_email,
            EmailLog.status == "sent",
            EmailLog.opened_at.isnot(None),
        ).count()

        if sent_emails > 0:
            return (opened_emails / sent_emails) * 100
        return 0.0

    @classmethod
    def create_verification_email(cls, user, token):
        """メール認証用ログエントリを作成"""
        return cls(
            recipient_id=user.id,
            recipient_email=user.email,
            email_type="verification",
            subject="QuestEd - メールアドレス認証",
            template_name="email_verification",
            template_variables={
                "user_name": user.get_display_name(),
                "verification_token": token,
                "verification_url": f"/auth/verify_email/{token}",
            },
        )

    @classmethod
    def create_password_reset_email(cls, user, token):
        """パスワードリセット用ログエントリを作成"""
        return cls(
            recipient_id=user.id,
            recipient_email=user.email,
            email_type="reset_password",
            subject="QuestEd - パスワードリセット",
            template_name="password_reset",
            template_variables={
                "user_name": user.get_display_name(),
                "reset_token": token,
                "reset_url": f"/auth/reset_password/{token}",
            },
        )

    @classmethod
    def create_notification_email(cls, user, notification_type, data):
        """通知用ログエントリを作成"""
        subject_map = {
            "new_assignment": "QuestEd - 新しい課題が追加されました",
            "grade_posted": "QuestEd - 成績が投稿されました",
            "class_announcement": "QuestEd - クラスからのお知らせ",
            "reminder": "QuestEd - リマインダー",
        }

        return cls(
            recipient_id=user.id,
            recipient_email=user.email,
            email_type="notification",
            subject=subject_map.get(notification_type, "QuestEd - 通知"),
            template_name=f"notification_{notification_type}",
            template_variables={
                "user_name": user.get_display_name(),
                "notification_data": data,
            },
        )

    def __repr__(self):
        return f"<EmailLog {self.id}: {self.email_type} to {self.recipient_email}>"
