# app/models/unit_progress.py
"""単元学習進捗の詳細記録モデル"""

from datetime import datetime
from extensions import db


class UnitProgressRecord(db.Model):
    """単元内問題の詳細学習記録"""
    
    __tablename__ = "unit_progress_records"
    
    id = db.Column(db.Integer, primary_key=True, comment="進捗記録ID")
    student_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, comment="学生ID"
    )
    unit_id = db.Column(
        db.Integer, db.ForeignKey("curriculum_units.id"), nullable=False, comment="単元ID"
    )
    item_id = db.Column(
        db.Integer, db.ForeignKey("basic_knowledge_items.id"), nullable=False, comment="問題ID"
    )
    
    # 学習状況
    status = db.Column(
        db.Enum("not_started", "in_progress", "completed", "reviewed"),
        default="not_started",
        comment="学習状況"
    )
    
    # 学習記録
    started_at = db.Column(db.DateTime, nullable=True, comment="学習開始時刻")
    completed_at = db.Column(db.DateTime, nullable=True, comment="完了時刻")
    study_time_seconds = db.Column(db.Integer, default=0, comment="学習時間（秒）")
    attempt_count = db.Column(db.Integer, default=0, comment="取り組み回数")
    
    # 理解度・評価
    self_rating = db.Column(db.Integer, nullable=True, comment="自己評価(1-5)")
    difficulty_rating = db.Column(db.Integer, nullable=True, comment="難易度評価(1-5)")
    confidence_level = db.Column(db.Integer, nullable=True, comment="理解度(1-5)")
    
    # メモ・記録
    notes = db.Column(db.Text, comment="学習メモ")
    mistake_notes = db.Column(db.Text, comment="間違いメモ")
    review_notes = db.Column(db.Text, comment="復習メモ")
    
    # システム記録
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="作成日時")
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新日時"
    )
    
    # インデックス
    __table_args__ = (
        db.UniqueConstraint("student_id", "unit_id", "item_id", name="uk_student_unit_item"),
        db.Index("idx_student_unit", "student_id", "unit_id"),
        db.Index("idx_status", "status"),
        db.Index("idx_completed_at", "completed_at"),
    )
    
    # リレーションシップ
    student = db.relationship("User", backref="unit_progress_records")
    unit = db.relationship("CurriculumUnit", backref="progress_records")
    # item = db.relationship("BasicKnowledgeItem", backref="unit_progress_records")
    
    def start_learning(self):
        """学習開始"""
        if self.status == "not_started":
            self.status = "in_progress"
            self.started_at = datetime.utcnow()
            self.attempt_count += 1
        self.updated_at = datetime.utcnow()
    
    def complete_learning(self, self_rating=None, difficulty_rating=None, notes=None):
        """学習完了"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        if self_rating:
            self.self_rating = self_rating
        if difficulty_rating:
            self.difficulty_rating = difficulty_rating
        if notes:
            self.notes = notes
        self.updated_at = datetime.utcnow()
    
    def calculate_study_time(self):
        """学習時間を計算（秒）"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.study_time_seconds = int(delta.total_seconds())
        return self.study_time_seconds
    
    def get_study_time_formatted(self):
        """学習時間を読みやすい形式で取得"""
        if self.study_time_seconds < 60:
            return f"{self.study_time_seconds}秒"
        elif self.study_time_seconds < 3600:
            minutes = self.study_time_seconds // 60
            seconds = self.study_time_seconds % 60
            return f"{minutes}分{seconds}秒"
        else:
            hours = self.study_time_seconds // 3600
            minutes = (self.study_time_seconds % 3600) // 60
            return f"{hours}時間{minutes}分"
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "unit_id": self.unit_id,
            "item_id": self.item_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "study_time_seconds": self.study_time_seconds,
            "study_time_formatted": self.get_study_time_formatted(),
            "attempt_count": self.attempt_count,
            "self_rating": self.self_rating,
            "difficulty_rating": self.difficulty_rating,
            "confidence_level": self.confidence_level,
            "notes": self.notes,
            "mistake_notes": self.mistake_notes,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f"<UnitProgressRecord student:{self.student_id} unit:{self.unit_id} item:{self.item_id} status:{self.status}>"