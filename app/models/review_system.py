from datetime import date, datetime, timedelta

from extensions import db


class ReviewSet(db.Model):
    """復習セットテーブル"""

    __tablename__ = "review_sets"

    id = db.Column(db.Integer, primary_key=True, comment="復習セットID")
    student_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, comment="生徒ID"
    )
    title = db.Column(db.String(200), nullable=False, comment="復習セット名")
    description = db.Column(db.Text, comment="復習セット説明")
    generation_type = db.Column(
        db.Enum("automatic", "manual", "ai_generated"),
        default="automatic",
        comment="生成タイプ",
    )
    target_weakness_areas = db.Column(db.JSON, comment="対象弱点分野")
    difficulty_level = db.Column(db.Integer, default=3, comment="難易度レベル（1-5）")
    total_problems = db.Column(db.Integer, nullable=False, default=0, comment="総問題数")
    estimated_time_minutes = db.Column(db.Integer, default=30, comment="推定解答時間（分）")
    review_type = db.Column(
        db.Enum("spaced_repetition", "weakness_focused", "comprehensive", "exam_prep"),
        default="weakness_focused",
        comment="復習タイプ",
    )
    status = db.Column(
        db.Enum("draft", "active", "completed", "expired"),
        default="draft",
        comment="ステータス",
    )
    expires_at = db.Column(db.DateTime, nullable=True, comment="有効期限")
    generated_by_ai = db.Column(db.Boolean, default=False, comment="AI生成フラグ")
    ai_generation_params = db.Column(db.JSON, comment="AI生成パラメータ")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="作成日時")
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新日時"
    )

    # インデックス
    __table_args__ = (
        db.Index("idx_student_id", "student_id"),
        db.Index("idx_generation_type", "generation_type"),
        db.Index("idx_status", "status"),
        db.Index("idx_difficulty_level", "difficulty_level"),
        db.Index("idx_expires_at", "expires_at"),
        db.Index("idx_created_at", "created_at"),
    )

    # リレーションシップ
    student = db.relationship(
        "User", backref=db.backref("review_sets", cascade="all, delete-orphan")
    )
    items = db.relationship(
        "ReviewSetItem",
        backref="review_set",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        """辞書形式に変換"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "title": self.title,
            "description": self.description,
            "generation_type": self.generation_type,
            "target_weakness_areas": self.target_weakness_areas,
            "difficulty_level": self.difficulty_level,
            "total_problems": self.total_problems,
            "estimated_time_minutes": self.estimated_time_minutes,
            "review_type": self.review_type,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "generated_by_ai": self.generated_by_ai,
            "ai_generation_params": self.ai_generation_params,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_items": self.get_completed_items_count(),
            "progress_percentage": self.get_progress_percentage(),
        }

    def get_completed_items_count(self):
        """完了した問題数を取得"""
        return self.items.filter_by(is_completed=True).count()

    def get_progress_percentage(self):
        """進捗率を計算"""
        if self.total_problems > 0:
            completed = self.get_completed_items_count()
            return (completed / self.total_problems) * 100
        return 0.0

    def get_accuracy_rate(self):
        """正解率を計算"""
        completed_items = self.items.filter_by(is_completed=True).all()
        if not completed_items:
            return 0.0

        correct_count = sum(1 for item in completed_items if item.is_correct)
        return (correct_count / len(completed_items)) * 100

    def activate(self):
        """復習セットをアクティブ化"""
        self.status = "active"
        self.updated_at = datetime.utcnow()

    def complete(self):
        """復習セットを完了"""
        self.status = "completed"
        self.updated_at = datetime.utcnow()

    def is_expired(self):
        """有効期限切れかチェック"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    def __repr__(self):
        return f"<ReviewSet {self.id}: {self.title}>"


class ReviewSetItem(db.Model):
    """復習セット問題テーブル"""

    __tablename__ = "review_set_items"

    id = db.Column(db.Integer, primary_key=True, comment="復習問題ID")
    review_set_id = db.Column(
        db.Integer, db.ForeignKey("review_sets.id"), nullable=False, comment="復習セットID"
    )
    problem_id = db.Column(
        db.Integer,
        db.ForeignKey("basic_knowledge_items.id"),
        nullable=False,
        comment="問題ID",
    )
    order_index = db.Column(db.Integer, nullable=False, comment="問題順序")
    weight = db.Column(db.Numeric(3, 2), default=1.00, comment="重み（重要度）")
    expected_difficulty = db.Column(db.Numeric(3, 2), comment="期待難易度")
    weakness_category = db.Column(db.String(100), comment="弱点カテゴリ")
    selection_reason = db.Column(db.Text, comment="選択理由")
    is_completed = db.Column(db.Boolean, default=False, comment="完了フラグ")
    student_answer = db.Column(db.Text, comment="生徒の回答")
    is_correct = db.Column(db.Boolean, default=None, comment="正解フラグ")
    time_spent_seconds = db.Column(db.Integer, comment="解答時間（秒）")
    attempts_count = db.Column(db.Integer, default=0, comment="試行回数")
    completed_at = db.Column(db.DateTime, nullable=True, comment="完了日時")

    # ユニーク制約とインデックス
    __table_args__ = (
        db.UniqueConstraint(
            "review_set_id", "problem_id", name="uk_review_set_problem"
        ),
        db.Index("idx_review_set_id", "review_set_id"),
        db.Index("idx_problem_id", "problem_id"),
        db.Index("idx_order_index", "order_index"),
        db.Index("idx_is_completed", "is_completed"),
        db.Index("idx_weakness_category", "weakness_category"),
    )

    # リレーションシップ
    basic_knowledge_item = db.relationship("BasicKnowledgeItem", backref="review_items")

    def to_dict(self):
        """辞書形式に変換"""
        return {
            "id": self.id,
            "review_set_id": self.review_set_id,
            "problem_id": self.problem_id,
            "order_index": self.order_index,
            "weight": float(self.weight) if self.weight else None,
            "expected_difficulty": float(self.expected_difficulty)
            if self.expected_difficulty
            else None,
            "weakness_category": self.weakness_category,
            "selection_reason": self.selection_reason,
            "is_completed": self.is_completed,
            "student_answer": self.student_answer,
            "is_correct": self.is_correct,
            "time_spent_seconds": self.time_spent_seconds,
            "attempts_count": self.attempts_count,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }

    def answer(self, student_answer, is_correct, time_spent_seconds=None):
        """回答を記録"""
        self.student_answer = student_answer
        self.is_correct = is_correct
        self.is_completed = True
        self.attempts_count += 1
        self.completed_at = datetime.utcnow()

        if time_spent_seconds:
            self.time_spent_seconds = time_spent_seconds

    def __repr__(self):
        return f"<ReviewSetItem set:{self.review_set_id} problem:{self.problem_id}>"


# 以下のクラスはRDSに存在しないため、将来の実装用にコメントアウト

# class StudentWeakness(db.Model):
#     """生徒弱点分析テーブル"""
#     __tablename__ = 'student_weaknesses'

# class ReviewSchedule(db.Model):
#     """復習スケジュールテーブル（間隔反復学習用）"""
#     __tablename__ = 'review_schedules'

# class ReviewPerformance(db.Model):
#     """復習パフォーマンステーブル"""
#     __tablename__ = 'review_performance'

# class ReviewGenerationRule(db.Model):
#     """復習問題生成ルールテーブル"""
#     __tablename__ = 'review_generation_rules'
