"""
Curriculum Task Models
======================
Week 1: 基盤整備

新タスクシステムのためのモデル定義
- CurriculumTask: 週次課題データ
- StudentTaskProgress: 学生課題進捗
- TaskDependency: 課題依存関係
- TaskFileAttachment: 課題添付ファイル
"""

from datetime import datetime, timedelta
from enum import Enum

from app.models import db


class TaskType(Enum):
    """課題タイプ列挙"""
    WORKSHEET = 'worksheet'
    REPORT = 'report'
    TEST = 'test'
    PRESENTATION = 'presentation'
    PROJECT = 'project'
    DISCUSSION = 'discussion'


class TaskStatus(Enum):
    """課題進捗状況列挙"""
    NOT_STARTED = 'not_started'
    IN_PROGRESS = 'in_progress'
    SUBMITTED = 'submitted'
    COMPLETED = 'completed'
    NEEDS_REVISION = 'needs_revision'


class DueDateType(Enum):
    """期限タイプ列挙"""
    RELATIVE_TO_WEEK_START = 'relative_to_week_start'
    RELATIVE_TO_PREVIOUS = 'relative_to_previous'
    FIXED_DATE = 'fixed_date'


class CurriculumTask(db.Model):
    """週次課題モデル"""
    __tablename__ = 'curriculum_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculums.id', ondelete='CASCADE'), nullable=False)
    week_number = db.Column(db.Integer, nullable=False)
    order_in_week = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # 課題分類
    task_type = db.Column(db.Enum(TaskType), nullable=False)
    estimated_minutes = db.Column(db.Integer, default=50)
    difficulty_level = db.Column(db.Integer, default=2)
    is_required = db.Column(db.Boolean, default=True)
    
    # 提出要件・評価基準 (JSON)
    submission_requirements = db.Column(db.JSON)
    evaluation_criteria = db.Column(db.JSON)
    
    # 期限管理
    due_date_type = db.Column(db.Enum(DueDateType), default=DueDateType.RELATIVE_TO_WEEK_START)
    due_date_offset_days = db.Column(db.Integer, default=7)
    fixed_due_date = db.Column(db.Date)
    
    # メタデータ
    resources = db.Column(db.JSON)  # 参考資料・リンク
    teacher_notes = db.Column(db.Text)
    auto_approval_enabled = db.Column(db.Boolean, default=False)
    auto_approval_threshold = db.Column(db.Integer, default=80)
    
    # 管理情報
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    curriculum = db.relationship('Curriculum', backref='tasks', lazy=True)
    creator = db.relationship('User', foreign_keys=[created_by], lazy=True)
    progress_records = db.relationship('StudentTaskProgress', backref='task', lazy=True, cascade='all, delete-orphan')
    dependencies = db.relationship('TaskDependency', foreign_keys='TaskDependency.task_id', backref='task', lazy=True)
    prerequisites = db.relationship('TaskDependency', foreign_keys='TaskDependency.prerequisite_task_id', backref='prerequisite_task', lazy=True)
    
    def __repr__(self):
        return f'<CurriculumTask {self.title}>'
    
    def get_type_display(self):
        """課題タイプの日本語表示"""
        type_display = {
            TaskType.WORKSHEET: 'ワークシート',
            TaskType.REPORT: 'レポート',
            TaskType.TEST: 'テスト',
            TaskType.PRESENTATION: 'プレゼンテーション',
            TaskType.PROJECT: 'プロジェクト',
            TaskType.DISCUSSION: 'ディスカッション'
        }
        return type_display.get(self.task_type, self.task_type.value)
    
    def calculate_due_date(self, week_start_date):
        """期限日を計算"""
        if self.due_date_type == DueDateType.FIXED_DATE:
            return self.fixed_due_date
        elif self.due_date_type == DueDateType.RELATIVE_TO_WEEK_START:
            return week_start_date + timedelta(days=self.due_date_offset_days)
        else:
            # 前の課題からの相対期限は後で実装
            return week_start_date + timedelta(days=self.due_date_offset_days)
    
    def get_submission_format_display(self):
        """提出形式の表示"""
        if not self.submission_requirements:
            return '未設定'
        
        format_mapping = {
            'document': '文書ファイル',
            'handwritten': '手書き',
            'video': '動画',
            'presentation': 'プレゼンテーション'
        }
        
        format_value = self.submission_requirements.get('format', '未設定')
        return format_mapping.get(format_value, format_value)
    
    def to_dict(self):
        """辞書形式で返す（API用）"""
        return {
            'id': self.id,
            'curriculum_id': self.curriculum_id,
            'week_number': self.week_number,
            'order_in_week': self.order_in_week,
            'title': self.title,
            'description': self.description,
            'task_type': self.task_type.value,
            'task_type_display': self.get_type_display(),
            'estimated_minutes': self.estimated_minutes,
            'difficulty_level': self.difficulty_level,
            'is_required': self.is_required,
            'submission_requirements': self.submission_requirements,
            'evaluation_criteria': self.evaluation_criteria,
            'due_date_type': self.due_date_type.value,
            'due_date_offset_days': self.due_date_offset_days,
            'fixed_due_date': self.fixed_due_date.isoformat() if self.fixed_due_date else None,
            'resources': self.resources,
            'teacher_notes': self.teacher_notes,
            'auto_approval_enabled': self.auto_approval_enabled,
            'auto_approval_threshold': self.auto_approval_threshold,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class StudentTaskProgress(db.Model):
    """学生課題進捗モデル"""
    __tablename__ = 'student_task_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('curriculum_tasks.id', ondelete='CASCADE'), nullable=False)
    
    # 進捗状況
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.NOT_STARTED)
    progress_percentage = db.Column(db.Integer, default=0)
    
    # タイムスタンプ
    started_at = db.Column(db.DateTime)
    submitted_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    last_activity_at = db.Column(db.DateTime)
    
    # 提出データ
    submission_data = db.Column(db.JSON)  # 提出ファイル・内容
    self_evaluation = db.Column(db.JSON)  # 自己評価
    time_spent_minutes = db.Column(db.Integer, default=0)
    
    # 教師評価
    teacher_evaluation = db.Column(db.JSON)  # ルーブリック評価結果
    teacher_feedback = db.Column(db.Text)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approval_requested_at = db.Column(db.DateTime)
    
    # リレーションシップ
    student = db.relationship('User', foreign_keys=[student_id], lazy=True)
    approver = db.relationship('User', foreign_keys=[approved_by], lazy=True)
    file_attachments = db.relationship('TaskFileAttachment', backref='task_progress', lazy=True, cascade='all, delete-orphan')
    
    # 複合インデックス制約
    __table_args__ = (
        db.UniqueConstraint('student_id', 'task_id', name='unique_student_task'),
        db.Index('idx_student_progress', 'student_id', 'status'),
        db.Index('idx_task_submissions', 'task_id', 'status'),
        db.Index('idx_approval_queue', 'status', 'approval_requested_at')
    )
    
    def __repr__(self):
        return f'<StudentTaskProgress {self.student_id}:{self.task_id}>'
    
    def get_status_display(self):
        """進捗状況の日本語表示"""
        status_display = {
            TaskStatus.NOT_STARTED: '未開始',
            TaskStatus.IN_PROGRESS: '学習中',
            TaskStatus.SUBMITTED: '提出済み',
            TaskStatus.COMPLETED: '完了',
            TaskStatus.NEEDS_REVISION: '修正必要'
        }
        return status_display.get(self.status, self.status.value)
    
    def start_task(self):
        """課題開始"""
        if self.status == TaskStatus.NOT_STARTED:
            self.status = TaskStatus.IN_PROGRESS
            self.started_at = datetime.utcnow()
            self.last_activity_at = datetime.utcnow()
            return True
        return False
    
    def submit_task(self, submission_data, self_evaluation=None):
        """課題提出"""
        if self.status in [TaskStatus.IN_PROGRESS, TaskStatus.NEEDS_REVISION]:
            self.status = TaskStatus.SUBMITTED
            self.submitted_at = datetime.utcnow()
            self.last_activity_at = datetime.utcnow()
            self.submission_data = submission_data
            if self_evaluation:
                self.self_evaluation = self_evaluation
            self.approval_requested_at = datetime.utcnow()
            return True
        return False
    
    def approve_task(self, approver_id, teacher_evaluation=None, feedback=None):
        """課題承認"""
        if self.status == TaskStatus.SUBMITTED:
            self.status = TaskStatus.COMPLETED
            self.completed_at = datetime.utcnow()
            self.approved_by = approver_id
            if teacher_evaluation:
                self.teacher_evaluation = teacher_evaluation
            if feedback:
                self.teacher_feedback = feedback
            return True
        return False
    
    def request_revision(self, feedback):
        """修正依頼"""
        if self.status == TaskStatus.SUBMITTED:
            self.status = TaskStatus.NEEDS_REVISION
            self.teacher_feedback = feedback
            self.last_activity_at = datetime.utcnow()
            return True
        return False
    
    def update_progress(self, percentage, time_spent=0):
        """進捗更新"""
        self.progress_percentage = min(100, max(0, percentage))
        self.time_spent_minutes += time_spent
        self.last_activity_at = datetime.utcnow()
    
    def to_dict(self):
        """辞書形式で返す（API用）"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'task_id': self.task_id,
            'status': self.status.value,
            'status_display': self.get_status_display(),
            'progress_percentage': self.progress_percentage,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_activity_at': self.last_activity_at.isoformat() if self.last_activity_at else None,
            'submission_data': self.submission_data,
            'self_evaluation': self.self_evaluation,
            'time_spent_minutes': self.time_spent_minutes,
            'teacher_evaluation': self.teacher_evaluation,
            'teacher_feedback': self.teacher_feedback,
            'approved_by': self.approved_by,
            'approval_requested_at': self.approval_requested_at.isoformat() if self.approval_requested_at else None
        }


class TaskDependency(db.Model):
    """課題依存関係モデル"""
    __tablename__ = 'task_dependencies'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('curriculum_tasks.id', ondelete='CASCADE'), nullable=False)
    prerequisite_task_id = db.Column(db.Integer, db.ForeignKey('curriculum_tasks.id', ondelete='CASCADE'), nullable=False)
    dependency_type = db.Column(db.Enum('required', 'recommended', name='dependency_types'), default='required')
    
    # 複合インデックス制約
    __table_args__ = (
        db.UniqueConstraint('task_id', 'prerequisite_task_id', name='unique_task_dependency'),
    )
    
    def __repr__(self):
        return f'<TaskDependency {self.task_id}:{self.prerequisite_task_id}>'


class TaskFileAttachment(db.Model):
    """課題添付ファイルモデル"""
    __tablename__ = 'task_file_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    task_progress_id = db.Column(db.Integer, db.ForeignKey('student_task_progress.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TaskFileAttachment {self.original_filename}>'
    
    def get_file_size_display(self):
        """ファイルサイズの表示用変換"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
    
    def to_dict(self):
        """辞書形式で返す（API用）"""
        return {
            'id': self.id,
            'task_progress_id': self.task_progress_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_size_display': self.get_file_size_display(),
            'mime_type': self.mime_type,
            'uploaded_at': self.uploaded_at.isoformat()
        }