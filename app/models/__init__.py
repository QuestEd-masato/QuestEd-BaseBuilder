# app/models/__init__.py
import json
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db

# Curriculum Task System Models Import
from .curriculum_task import (
    CurriculumTask, StudentTaskProgress, TaskDependency, TaskFileAttachment,
    TaskType, TaskStatus, DueDateType
)

# Curriculum Lesson System Models - Available via modules/lesson_system
# Note: These models are now accessible through app.modules.lesson_system.models.lesson_models
# Legacy import paths for backward compatibility are maintained in each service that needs them.


# モデル定義
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)  # ログイン用ID
    full_name = db.Column(db.String(100), nullable=True)  # 表示用氏名
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(10), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=True)
    class_id = db.Column(
        db.Integer, db.ForeignKey("classes.id"), nullable=True
    )  # RDS追加フィールド
    is_active = db.Column(db.Boolean, default=True)  # RDS追加フィールド
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    # メール認証・承認関連フィールド
    email_confirmed = db.Column(db.Boolean, default=False)
    email_token = db.Column(db.String(100), nullable=True)
    token_created_at = db.Column(db.DateTime, nullable=True)
    is_approved = db.Column(db.Boolean, default=False)

    # パスワードリセット関連フィールド
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_created_at = db.Column(db.DateTime, nullable=True)

    # 学年・学級関連フィールド
    grade = db.Column(db.Integer, nullable=True, comment="学年(1-12)")
    classroom = db.Column(db.String(10), nullable=True, comment="学級(1組、A組等)")
    student_number = db.Column(db.String(20), nullable=True, comment="生徒番号")

    # リレーションシップの定義（カスケード削除を設定）
    # TEMPORARY: Disabled to fix ambiguous foreign key error
    # classes_teaching = db.relationship(
    #     "Class",
    #     foreign_keys="Class.teacher_id",
    #     backref="teacher",
    #     lazy=True,
    #     cascade="all, delete-orphan",
    # )
    interest_surveys = db.relationship(
        "InterestSurvey", backref="student", lazy=True, cascade="all, delete-orphan"
    )
    personality_surveys = db.relationship(
        "PersonalitySurvey", backref="student", lazy=True, cascade="all, delete-orphan"
    )
    inquiry_themes = db.relationship(
        "InquiryTheme", backref="student", lazy=True, cascade="all, delete-orphan"
    )
    activity_logs = db.relationship(
        "ActivityLog", backref="student", lazy=True, cascade="all, delete-orphan"
    )
    todos = db.relationship(
        "Todo", backref="student", lazy=True, cascade="all, delete-orphan"
    )
    goals = db.relationship(
        "Goal", backref="student", lazy=True, cascade="all, delete-orphan"
    )
    student_evaluations = db.relationship(
        "StudentEvaluation",
        foreign_keys="StudentEvaluation.student_id",
        back_populates="student",
        lazy=True,
        cascade="all, delete-orphan",
    )
    chat_histories = db.relationship(
        "ChatHistory", back_populates="user", lazy=True, cascade="all, delete-orphan"
    )

    def has_completed_surveys(self):
        """学生がすべてのアンケートを完了しているかチェック"""
        if self.role != "student":
            return False
        interest_completed = (
            InterestSurvey.query.filter_by(student_id=self.id).first() is not None
        )
        personality_completed = (
            PersonalitySurvey.query.filter_by(student_id=self.id).first() is not None
        )
        return interest_completed and personality_completed

    def has_selected_theme(self):
        """学生が探究テーマを選択しているかチェック"""
        if self.role != "student":
            return False
        return (
            InquiryTheme.query.filter_by(student_id=self.id, is_selected=True).first()
            is not None
        )

    def get_display_name(self):
        """表示用の名前を取得（full_name優先、フォールバックでusername）"""
        return self.full_name if self.full_name else self.username

    @property
    def display_name(self):
        """表示名のプロパティ（テンプレートで使いやすくするため）"""
        return self.get_display_name()

    def set_password(self, password):
        """パスワードを暗号化して設定"""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """パスワードを確認"""
        # 現在のパスワードがハッシュ化されているかチェック
        if self.password and not self.password.startswith("pbkdf2:"):
            # プレーンテキストの場合は直接比較（一時的な対応）
            return self.password == password
        # ハッシュ化されている場合は通常の確認
        return check_password_hash(self.password, password)


# 学校管理のモデル定義
class School(db.Model):
    __tablename__ = "schools"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=True)  # 学校コード
    address = db.Column(db.Text)
    contact_email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # リレーションシップの定義
    years = db.relationship("SchoolYear", backref="school", lazy=True)
    users = db.relationship("User", backref="school", lazy=True)
    classes = db.relationship("Class", backref="school", lazy=True)

    # BaseBuilderモジュールとの関係は動的に追加される


class SchoolYear(db.Model):
    __tablename__ = "school_years"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    year = db.Column(db.String(20), nullable=False)  # 例: '2023-2024'
    is_current = db.Column(db.Boolean, default=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    # ユニーク制約 (同じ学校で同じ年度は一つだけ)
    __table_args__ = (db.UniqueConstraint("school_id", "year"),)

    # リレーションシップ
    class_groups = db.relationship("ClassGroup", backref="school_year", lazy=True)


class ClassGroup(db.Model):
    __tablename__ = "class_groups"
    id = db.Column(db.Integer, primary_key=True)
    school_year_id = db.Column(
        db.Integer, db.ForeignKey("school_years.id"), nullable=False
    )
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # 例: '1年A組'
    description = db.Column(db.Text)
    grade = db.Column(db.String(20))  # 例: '1年', '2年'など
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # リレーションシップ
    enrollments = db.relationship("StudentEnrollment", backref="class_group", lazy=True)
    teacher = db.relationship(
        "User",
        backref=db.backref(
            "class_groups_teaching", lazy=True, cascade="all, delete-orphan"
        ),
    )


class StudentEnrollment(db.Model):
    __tablename__ = "student_enrollments"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    class_group_id = db.Column(
        db.Integer, db.ForeignKey("class_groups.id"), nullable=False
    )
    school_year_id = db.Column(
        db.Integer, db.ForeignKey("school_years.id"), nullable=False
    )
    student_number = db.Column(db.Integer)  # 出席番号
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ユニーク制約 (同じ生徒は同じ年度・クラスに一度だけ登録可能)
    __table_args__ = (
        db.UniqueConstraint("student_id", "class_group_id", "school_year_id"),
    )

    # リレーションシップ
    student = db.relationship(
        "User",
        backref=db.backref(
            "student_enrollments", lazy=True, cascade="all, delete-orphan"
        ),
    )
    school_year = db.relationship(
        "SchoolYear", backref="student_enrollments", lazy=True
    )


# クラスモデル定義
class Class(db.Model):
    __tablename__ = "classes"
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    schedule = db.Column(db.String(200))
    location = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 学年・学級関連フィールド
    grade = db.Column(db.Integer, nullable=True, comment="対象学年")
    classroom = db.Column(db.String(10), nullable=True, comment="学級名")

    # クラスと学生の関連付け（多対多の関係）
    students = db.relationship(
        "User",
        secondary="class_enrollments",
        backref=db.backref("enrolled_classes", lazy="dynamic"),
        lazy="dynamic",
        overlaps="class_enrollments,enrollments,student,class_obj",
    )


# クラスと学生の中間テーブル（多対多の関連付け）
class ClassEnrollment(db.Model):
    __tablename__ = "class_enrollments"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # リレーションシップ
    student = db.relationship(
        "User",
        foreign_keys=[student_id],
        backref=db.backref("class_enrollments", cascade="all, delete-orphan"),
        overlaps="enrolled_classes,students",
    )
    class_obj = db.relationship(
        "Class",
        foreign_keys=[class_id],
        backref=db.backref("enrollments", overlaps="students"),
        overlaps="enrolled_classes,students",
    )

    # ユニーク制約（同じ学生が同じクラスに複数回登録されないように）
    __table_args__ = (db.UniqueConstraint("class_id", "student_id"),)


class MainTheme(db.Model):
    __tablename__ = "main_themes"
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # リレーションシップ
    teacher = db.relationship(
        "User",
        backref=db.backref("main_themes", lazy=True, cascade="all, delete-orphan"),
    )
    class_obj = db.relationship("Class", backref=db.backref("main_themes", lazy=True))

    # このメインテーマに関連する個人テーマ
    personal_themes = db.relationship("InquiryTheme", backref="main_theme", lazy=True)


class InquiryTheme(db.Model):
    __tablename__ = "inquiry_themes"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True)  # 追加
    main_theme_id = db.Column(
        db.Integer, db.ForeignKey("main_themes.id"), nullable=True
    )
    is_ai_generated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    title = db.Column(db.String(200))
    question = db.Column(db.Text)
    description = db.Column(db.Text)
    rationale = db.Column(db.Text)
    approach = db.Column(db.Text)
    potential = db.Column(db.Text)
    is_selected = db.Column(db.Boolean, default=False)

    # リレーションシップを追加
    class_obj = db.relationship(
        "Class", backref=db.backref("inquiry_themes", lazy=True)
    )


class InterestSurvey(db.Model):
    __tablename__ = "interest_surveys"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    responses = db.Column(db.Text)
    # submitted_at フィールドを追加
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


class PersonalitySurvey(db.Model):
    __tablename__ = "personality_surveys"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    responses = db.Column(db.Text)
    # submitted_at フィールドを追加
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True)  # 追加
    title = db.Column(db.String(200))
    date = db.Column(db.Date, default=datetime.utcnow().date())
    content = db.Column(db.Text)
    reflection = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activity = db.Column(db.Text)  # 既存のフィールドを残す
    tags = db.Column(db.String(255))  # 新しいタグフィールドを追加

    # リレーションシップを追加
    class_obj = db.relationship("Class", backref=db.backref("activity_logs", lazy=True))


class Todo(db.Model):
    __tablename__ = "todos"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    priority = db.Column(db.String(20))  # 'high', 'medium', 'low'
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Goal(db.Model):
    __tablename__ = "goals"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    goal_type = db.Column(db.String(20))  # 'long', 'medium', 'short'
    due_date = db.Column(db.Date)
    progress = db.Column(db.Integer, default=0)  # 0-100
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class StudentEvaluation(db.Model):
    __tablename__ = "student_evaluations"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    evaluation_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # リレーションシップ
    student = db.relationship("User", foreign_keys=[student_id], back_populates="student_evaluations")
    class_obj = db.relationship("Class", backref=db.backref("evaluations", lazy=True))


class Curriculum(db.Model):
    __tablename__ = "curriculums"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject_id = db.Column(
        db.Integer, db.ForeignKey("subjects.id"), nullable=True
    )  # RDS追加フィールド
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    # total_hours = db.Column(db.Float, default=29.2, comment='50分コマから計算した総時間数')
    # total_classes = db.Column(db.Integer, default=35, comment='50分コマの総数')
    # difficulty_level = db.Column(db.Integer, default=2, comment='難易度レベル（1-5）')
    # mastery_threshold = db.Column(db.Integer, default=80, comment='習熟度判定基準（%）')
    # self_paced_mode = db.Column(db.String(20), default='flexible', comment='自由進度設定')
    # prerequisite_skills = db.Column(db.Text, comment='前提スキル・知識')
    # has_fieldwork = db.Column(db.Boolean, default=False)
    # fieldwork_count = db.Column(db.Integer, default=0)
    # has_presentation = db.Column(db.Boolean, default=True)
    # presentation_format = db.Column(db.String(50), default='プレゼンテーション')
    # group_work_level = db.Column(db.String(50), default='ハイブリッド')
    # external_collaboration = db.Column(db.Boolean, default=False)
    content = db.Column(db.Text)  # JSONとして保存されたカリキュラム内容
    format = db.Column(db.String(20), default="json")  # データ形式: json(レガシー) | table(新形式)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # ブリッジ機能関連フィールド
    is_converted_to_units = db.Column(db.Boolean, default=False, comment="単元への変換済みフラグ")
    units_conversion_date = db.Column(db.DateTime, nullable=True, comment="単元変換日時")
    curriculum_data = db.Column(db.Text, comment="カリキュラム詳細データ（JSON形式）")
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, comment="作成者ID"
    )

    # リレーションシップ
    class_obj = db.relationship("Class", backref=db.backref("curriculums", lazy=True))
    teacher = db.relationship(
        "User",
        foreign_keys=[teacher_id],
        backref=db.backref("taught_curriculums", lazy=True),
    )
    creator = db.relationship(
        "User",
        foreign_keys=[created_by],
        backref=db.backref("created_curriculums", lazy=True),
    )

    def get_curriculum_items(self):
        """カリキュラムアイテムを取得"""
        if self.curriculum_data:
            try:
                data = json.loads(self.curriculum_data)
                return data.get("items", [])
            except json.JSONDecodeError:
                return []
        return []

    def get_difficulty_label(self):
        """難易度ラベルを取得"""
        difficulty_labels = {1: "基礎", 2: "標準", 3: "応用", 4: "発展", 5: "最難関"}
        return difficulty_labels.get(self.difficulty_level, "不明")

    def get_estimated_minutes_per_class(self):
        """コマあたりの推定分数を取得"""
        return 50  # 50分/コマ固定

    def get_self_paced_mode_label(self):
        """自由進度モードのラベルを取得"""
        mode_labels = {
            "disabled": "無効",
            "flexible": "柔軟進度",
            "completely_free": "完全自由進度",
        }
        return mode_labels.get(self.self_paced_mode, "不明")

    def is_self_paced_enabled(self):
        """自由進度学習が有効かどうか"""
        return self.self_paced_mode in ["flexible", "completely_free"]

    @property
    def total_classes(self):
        """総授業数を取得（デフォルト値35）"""
        # curriculum_dataからtotal_classesを取得、なければデフォルト値
        if self.curriculum_data:
            try:
                data = json.loads(self.curriculum_data)
                return data.get('total_classes', 35)
            except:
                pass
        return 35
    
    @property
    def total_hours(self):
        """総時間数を取得（50分コマ x 総授業数）"""
        return round(self.total_classes * 50 / 60, 1)  # 50分コマを時間に換算
    
    @property 
    def difficulty_level(self):
        """難易度レベルを取得（デフォルト値2）"""
        if self.curriculum_data:
            try:
                data = json.loads(self.curriculum_data)
                return data.get('difficulty_level', 2)
            except:
                pass
        return 2

    def to_dict(self):
        """辞書形式に変換"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "total_classes": self.total_classes,
            "total_hours": self.total_hours,
            "difficulty_level": self.difficulty_level,
            "difficulty_label": self.get_difficulty_label(),
            "mastery_threshold": self.mastery_threshold,
            "self_paced_mode": self.self_paced_mode,
            "self_paced_mode_label": self.get_self_paced_mode_label(),
            "prerequisite_skills": self.prerequisite_skills,
            "is_self_paced_enabled": self.is_self_paced_enabled(),
            "estimated_minutes_per_class": self.get_estimated_minutes_per_class(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RubricTemplate(db.Model):
    __tablename__ = "rubric_templates"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)  # JSONとして保存されたルーブリック
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # リレーションシップ
    class_obj = db.relationship(
        "Class", backref=db.backref("rubric_templates", lazy=True)
    )
    teacher = db.relationship(
        "User",
        backref=db.backref("created_rubrics", lazy=True, cascade="all, delete-orphan"),
    )


class Group(db.Model):
    __tablename__ = "groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # リレーションシップ
    class_obj = db.relationship("Class", backref=db.backref("groups", lazy=True))
    creator = db.relationship(
        "User",
        backref=db.backref("created_groups", lazy=True, cascade="all, delete-orphan"),
    )
    members = db.relationship(
        "User",
        secondary="group_memberships",
        backref=db.backref("joined_groups", lazy="dynamic", cascade="all, delete"),
    )


class GroupMembership(db.Model):
    __tablename__ = "group_memberships"
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ユニーク制約
    __table_args__ = (db.UniqueConstraint("group_id", "student_id"),)


class ChatHistory(db.Model):
    __tablename__ = "chat_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, default=True)  # True=ユーザー, False=AI
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # userリレーションシップは1つだけにする
    user = db.relationship("User", back_populates="chat_histories")
    class_obj = db.relationship(
        "Class", backref=db.backref("chat_histories", lazy=True)
    )


class Milestone(db.Model):
    __tablename__ = "milestones"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # クラスとの関連付け
    class_obj = db.relationship("Class", backref=db.backref("milestones", lazy=True))


# Note: Models below have been moved to separate files and imported above
# Keeping this section for reference only

from app.models.ai_recommendation import AIRecommendation  # 他クラスはRDSに存在しないためコメントアウト

# Import new feature models
from app.models.curriculum_unit import (  # LearningPathUnitはRDSに存在しないためコメントアウト
    ClassLearningSettings,
    CurriculumUnit,
    LearningPath,
    StudentUnitSelection,
    UnitItemMapping,
)
from app.models.unit_progress import UnitProgressRecord
from app.models.email_log import EmailLog
from app.models.review_system import ReviewSet, ReviewSetItem  # 他クラスはRDSに存在しないためコメントアウト
from app.models.speech_transcription import (
    SpeechTranscription,  # SpeechSettings, SpeechStatisticsはRDSに存在しないためコメントアウト
)

# MFA (Multi-Factor Authentication) models
from app.models.mfa_models import (
    UserMFASecret,
    MFABackupCode,
    MFALoginAttempt,
    MFADeviceTrust,
)

# Import Subject model
from app.models.subject import Subject

# Import BaseBuilder models for unified access
from basebuilder.models import (
    AnswerRecord,
    BaseBuilderLearningPath,
    BasicKnowledgeItem,
    KnowledgeThemeRelation,
    PathAssignment,
    ProblemCategory,
    ProficiencyRecord,
    TextDelivery,
    TextProficiencyRecord,
    TextSet,
    WordProficiency,
)

# BaseBuilderRecord は存在しないため、AnswerRecord をエイリアスとして使用
BaseBuilderRecord = AnswerRecord

# StudentMilestone モデルを作成（マイルストーンと学生の関連付け）
class StudentMilestone(db.Model):
    __tablename__ = "student_milestones"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    milestone_id = db.Column(db.Integer, db.ForeignKey("milestones.id"), nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # リレーションシップ
    student = db.relationship("User", backref="student_milestones")
    milestone = db.relationship("Milestone", backref="student_milestones")


# WeaknessAnalysis モデルを作成（Phase6で分離された弱点分析用）
class WeaknessAnalysis(db.Model):
    __tablename__ = "weakness_analyses"
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    analysis_date = db.Column(db.DateTime, nullable=False)
    weaknesses_json = db.Column(db.Text, nullable=False)  # JSON形式の弱点データ
    recommendations_json = db.Column(db.Text, nullable=False)  # JSON形式の推奨事項
    statistics_json = db.Column(db.Text)  # JSON形式の統計データ
    patterns_json = db.Column(db.Text)  # JSON形式のパターンデータ
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # リレーション
    student = db.relationship("User", backref="weakness_analyses")

# Note: All model classes are now imported from separate files above


class Ranking(db.Model):
    """
    学習ランキングモデル

    学生の学習成果をランキング形式で管理し、
    様々な指標に基づいてランキングを生成します。
    """

    __tablename__ = "rankings"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"))

    # ランキング種類
    ranking_type = db.Column(
        db.Enum(
            "total_points",  # 総合ポイント
            "weekly_points",  # 週間ポイント
            "monthly_points",  # 月間ポイント
            "accuracy_rate",  # 正答率
            "study_time",  # 学習時間
            "consistency",  # 継続性
        ),
        nullable=False,
    )

    # ランキング期間
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)

    # ランキングデータ
    rank_position = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Numeric(10, 2), nullable=False)
    total_participants = db.Column(db.Integer, nullable=False)

    # 詳細データ
    detailed_stats = db.Column(db.JSON)  # 詳細統計情報

    # メタデータ
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_current = db.Column(db.Boolean, default=True)

    # インデックス用制約
    __table_args__ = (
        db.Index(
            "idx_ranking_type_period", "ranking_type", "period_start", "period_end"
        ),
        db.Index("idx_ranking_student_type", "student_id", "ranking_type"),
        db.Index("idx_ranking_class_type", "class_id", "ranking_type"),
        db.Index("idx_ranking_current", "is_current", "ranking_type"),
    )

    # リレーションシップ
    student = db.relationship("User", backref="rankings")
    school = db.relationship("School", backref="rankings")
    class_obj = db.relationship("Class", backref="rankings")


class RankingCache(db.Model):
    """
    ランキングキャッシュモデル

    計算済みのランキングデータをキャッシュして
    パフォーマンスを向上させます。
    """

    __tablename__ = "ranking_cache"

    id = db.Column(db.Integer, primary_key=True)
    cache_key = db.Column(db.String(200), unique=True, nullable=False)
    ranking_type = db.Column(db.String(50), nullable=False)
    scope = db.Column(db.Enum("school", "class"), nullable=False)
    scope_id = db.Column(db.Integer, nullable=False)  # school_id or class_id

    # キャッシュデータ
    ranking_data = db.Column(db.JSON, nullable=False)
    participant_count = db.Column(db.Integer, nullable=False)

    # キャッシュメタデータ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # インデックス
    __table_args__ = (
        db.Index("idx_cache_key", "cache_key"),
        db.Index("idx_cache_type_scope", "ranking_type", "scope", "scope_id"),
        db.Index("idx_cache_expires", "expires_at"),
    )


# Export all models
__all__ = [
    "db",
    "User",
    "School",
    "SchoolYear",
    "ClassGroup",
    "StudentEnrollment",
    "Class",
    "ClassEnrollment",
    "MainTheme",
    "InquiryTheme",
    "InterestSurvey",
    "PersonalitySurvey",
    "ActivityLog",
    "Todo",
    "Goal",
    "StudentEvaluation",
    "Curriculum",
    "RubricTemplate",
    "Group",
    "GroupMembership",
    "ChatHistory",
    "Milestone",
    "Subject",
    "Ranking",
    "RankingCache",
    "StudentMilestone",
    "WeaknessAnalysis",
    # Curriculum Unit models (RDS互換のみ)
    "CurriculumUnit",
    "UnitItemMapping",
    "StudentUnitSelection",
    "ClassLearningSettings",
    "LearningPath",
    # Speech models (RDS互換のみ)
    "SpeechTranscription",
    # AI Recommendation models (RDS互換のみ)
    "AIRecommendation",
    # Review System models (RDS互換のみ)
    "ReviewSet",
    "ReviewSetItem",
    # Email models
    "EmailLog",
    # MFA models
    "UserMFASecret",
    "MFABackupCode",
    "MFALoginAttempt",
    "MFADeviceTrust",
    # BaseBuilder models
    "ProblemCategory",
    "BasicKnowledgeItem",
    "AnswerRecord",
    "ProficiencyRecord",
    "TextSet",
    "TextDelivery",
    "BaseBuilderLearningPath",
    "PathAssignment",
    "WordProficiency",
    "TextProficiencyRecord",
    "KnowledgeThemeRelation",
    "BaseBuilderRecord",
]
