from datetime import date, datetime

from extensions import db


class SpeechTranscription(db.Model):
    """音声入力履歴テーブル"""

    __tablename__ = "speech_transcriptions"

    id = db.Column(db.Integer, primary_key=True, comment="音声入力履歴ID")
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, comment="ユーザーID (RDS互換)"
    )
    transcription = db.Column(db.Text, nullable=False, comment="音声認識テキスト (RDS互換)")
    usage_context = db.Column(db.String(50), default="chat", comment="使用コンテキスト (RDS互換)")
    duration = db.Column(db.Numeric(5, 2), comment="音声の長さ（秒） (RDS互換)")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="作成日時")

    # 新機能用の追加フィールド（RDSと互換性を保ちつつ拡張）
    session_id = db.Column(db.String(100), comment="セッションID (新機能)")
    cleaned_text = db.Column(db.Text, comment="クリーニング後のテキスト (新機能)")
    confidence_score = db.Column(
        db.Numeric(3, 2), default=0.00, comment="認識精度スコア (新機能)"
    )
    language_code = db.Column(db.String(10), default="ja-JP", comment="言語コード (新機能)")
    context_id = db.Column(db.Integer, comment="コンテキストに関連するID (新機能)")
    is_processed = db.Column(db.Boolean, default=False, comment="処理済みフラグ (新機能)")
    error_message = db.Column(db.Text, comment="エラーメッセージ (新機能)")
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新日時 (新機能)",
    )

    # インデックス
    __table_args__ = (
        db.Index("idx_user_id", "user_id"),
        db.Index("idx_session_id", "session_id"),
        db.Index("idx_usage_context", "usage_context", "context_id"),
        db.Index("idx_created_at", "created_at"),
        db.Index("idx_is_processed", "is_processed"),
    )

    # リレーションシップ
    user = db.relationship(
        "User",
        backref=db.backref("speech_transcriptions", cascade="all, delete-orphan"),
    )

    def to_dict(self):
        """辞書形式に変換"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "transcription": self.transcription,
            "cleaned_text": self.cleaned_text,
            "confidence_score": float(self.confidence_score)
            if self.confidence_score
            else None,
            "language_code": self.language_code,
            "duration": float(self.duration) if self.duration else None,
            "usage_context": self.usage_context,
            "context_id": self.context_id,
            "is_processed": self.is_processed,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def mark_as_processed(self, cleaned_text=None, error_message=None):
        """処理完了としてマーク"""
        self.is_processed = True
        if cleaned_text:
            self.cleaned_text = cleaned_text
        if error_message:
            self.error_message = error_message
        self.updated_at = datetime.utcnow()

    def get_confidence_level(self):
        """信頼度レベルを文字列で取得"""
        if self.confidence_score >= 0.9:
            return "very_high"
        elif self.confidence_score >= 0.7:
            return "high"
        elif self.confidence_score >= 0.5:
            return "medium"
        elif self.confidence_score >= 0.3:
            return "low"
        else:
            return "very_low"

    def __repr__(self):
        return f"<SpeechTranscription {self.id}: {self.usage_context}>"


# 以下のクラスはRDSに存在しないため、将来の実装用にコメントアウト

# class SpeechSettings(db.Model):
#     """音声入力個人設定テーブル"""
#     __tablename__ = 'speech_settings'
#
#     id = db.Column(db.Integer, primary_key=True, comment='設定ID')
#     student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='生徒ID')
#     is_enabled = db.Column(db.Boolean, default=True, comment='音声入力有効フラグ')
#     language_preference = db.Column(db.String(10), default='ja-JP', comment='優先言語')

# class SpeechStatistics(db.Model):
#     """音声入力統計テーブル"""
#     __tablename__ = 'speech_statistics'
#
#     id = db.Column(db.Integer, primary_key=True, comment='統計ID')
#     student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='生徒ID')
