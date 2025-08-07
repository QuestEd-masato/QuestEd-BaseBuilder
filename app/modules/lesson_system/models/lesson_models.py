"""
Curriculum Lesson Models
========================
教師カリキュラムとの完全統合

新しい時間単位の学習システム:
- CurriculumLesson: 1時間(50分)単位のレッスン
- LessonTask: レッスン内のタスク
- StudentLessonProgress: 学生の時間単位進捗
- StudentTaskCheck: タスクチェック記録
"""

from datetime import datetime
from enum import Enum

from app.models import db


class LessonType(Enum):
    """レッスンタイプ列挙"""
    LECTURE = 'lecture'          # 講義
    PRACTICE = 'practice'        # 演習
    DISCUSSION = 'discussion'    # 討論
    PRESENTATION = 'presentation' # 発表
    EXPERIMENT = 'experiment'    # 実験
    REVIEW = 'review'           # 復習


class TaskCheckStatus(Enum):
    """タスクチェック状況"""
    NOT_CHECKED = 'not_checked'     # 未チェック（初期状態）
    CHECKED = 'checked'            # チェック済み（承認待ち）
    COMPLETED = 'completed'        # 完了（承認済み）
    
    # 後方互換性のための別名定義
    NOT_STARTED = 'not_checked'    # NOT_CHECKEDの別名
    IN_PROGRESS = 'checked'        # CHECKEDの別名（作業中→承認待ち状態）


class CurriculumLesson(db.Model):
    """カリキュラム内の1時間(50分)レッスンモデル"""
    __tablename__ = 'curriculum_lessons'
    
    id = db.Column(db.Integer, primary_key=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculums.id', ondelete='CASCADE'), nullable=False)
    
    # レッスン基本情報
    lesson_number = db.Column(db.Integer, nullable=False)  # 第○時間目
    title = db.Column(db.String(200), nullable=False)     # レッスンタイトル
    description = db.Column(db.Text)                      # レッスン説明
    lesson_type = db.Column(db.Enum(LessonType, values_callable=lambda x: [e.value for e in x]), default=LessonType.LECTURE)
    
    # 時間設定
    duration_minutes = db.Column(db.Integer, default=50)   # 授業時間（分）
    estimated_prep_time = db.Column(db.Integer, default=10) # 準備時間（分）
    
    # 学習目標
    learning_objectives = db.Column(db.JSON)               # 学習目標リスト
    key_points = db.Column(db.JSON)                       # 重要ポイント
    
    # 評価基準
    evaluation_criteria = db.Column(db.JSON)              # 評価ルーブリック
    
    # メタデータ
    resources = db.Column(db.JSON)                        # 参考資料・リンク
    teacher_notes = db.Column(db.Text)                    # 教師用メモ
    
    # 管理情報
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    curriculum = db.relationship('Curriculum', backref='lessons')
    tasks = db.relationship('LessonTask', backref='lesson', lazy='dynamic', cascade='all, delete-orphan')
    student_progress = db.relationship('StudentLessonProgress', backref='lesson', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CurriculumLesson {self.curriculum_id}-{self.lesson_number}: {self.title}>'
    
    def to_dict(self):
        """辞書形式で返す"""
        return {
            'id': self.id,
            'curriculum_id': self.curriculum_id,
            'lesson_number': self.lesson_number,
            'title': self.title,
            'description': self.description,
            'lesson_type': self.lesson_type.value if self.lesson_type else None,
            'duration_minutes': self.duration_minutes,
            'learning_objectives': self.learning_objectives or [],
            'key_points': self.key_points or [],
            'evaluation_criteria': self.evaluation_criteria or {},
            'resources': self.resources or [],
            'teacher_notes': self.teacher_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LessonTask(db.Model):
    """レッスン内のタスクモデル"""
    __tablename__ = 'lesson_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('curriculum_lessons.id', ondelete='CASCADE'), nullable=False)
    
    # タスク基本情報
    task_number = db.Column(db.Integer, nullable=False)    # タスク番号
    title = db.Column(db.String(200), nullable=False)     # タスクタイトル  
    description = db.Column(db.Text)                      # タスク説明
    
    # タスク詳細
    instructions = db.Column(db.Text)                     # 具体的な指示
    estimated_minutes = db.Column(db.Integer, default=10) # 予想所要時間
    
    # 必須・選択
    is_required = db.Column(db.Boolean, default=True)     # 必須タスクかどうか
    # weight = db.Column(db.Float, default=1.0)             # 評価重み（DBに存在しない）
    
    # 管理情報
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    task_checks = db.relationship('StudentTaskCheck', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<LessonTask {self.lesson_id}-{self.task_number}: {self.title}>'
    
    def to_dict(self):
        """辞書形式で返す"""
        return {
            'id': self.id,
            'lesson_id': self.lesson_id,
            'task_number': self.task_number,
            'title': self.title,
            'description': self.description,
            'instructions': self.instructions,
            'expected_time_minutes': self.estimated_minutes,
            'is_required': self.is_required,
            # 'weight': self.weight,  # DBに存在しない
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StudentLessonProgress(db.Model):
    """学生のレッスン進捗モデル"""
    __tablename__ = 'student_lesson_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('curriculum_lessons.id', ondelete='CASCADE'), nullable=False)
    
    # 進捗状況（実際のDBスキーマに合わせて修正）
    started_at = db.Column(db.DateTime)                   # 開始時刻
    completed_at = db.Column(db.DateTime)                 # 完了時刻
    # time_spent_minutes は実際のDBに存在しないためコメントアウト
    # time_spent_minutes = db.Column(db.Integer, default=0) # 実際の学習時間
    
    # 理解度・振り返り（実際のDBスキーマに存在しないためコメントアウト）
    # understanding_level = db.Column(db.Integer)           # 理解度(1-5)
    # difficulty_level = db.Column(db.Integer)              # 難易度(1-5)
    # reflection = db.Column(db.Text)                       # 振り返りコメント
    
    # 状況（実際のDBスキーマに存在しないためコメントアウト）
    # is_completed = db.Column(db.Boolean, default=False)   # 完了フラグ
    # completion_percentage = db.Column(db.Integer, default=0) # 完了率
    
    # 承認ワークフロー機能
    approval_status = db.Column(
        db.Enum('none', 'pending', 'approved', 'rejected'),
        default='none',
        comment='承認状況'
    )
    completion_request_date = db.Column(db.DateTime, comment='完了申請日時')
    teacher_comments = db.Column(db.Text, comment='教師コメント')
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), comment='承認者ID')
    
    # タイムスタンプ（実際のDBスキーマに存在するもののみ）
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    student = db.relationship('User', foreign_keys=[student_id], backref='lesson_progress')
    task_checks = db.relationship('StudentTaskCheck', backref='lesson_progress', lazy='dynamic', cascade='all, delete-orphan')
    
    # ユニーク制約
    __table_args__ = (db.UniqueConstraint('student_id', 'lesson_id', name='unique_student_lesson'),)
    
    def __repr__(self):
        return f'<StudentLessonProgress {self.student_id}-{self.lesson_id}: {self.approval_status}>'
    
    def request_completion(self, notes=None):
        """完了申請を送信"""
        self.approval_status = 'pending'
        self.completion_request_date = datetime.utcnow()
        # notes は teacher_comments に保存
        if notes:
            self.teacher_comments = notes
        db.session.commit()
    
    def approve_completion(self, teacher_id, comments=None):
        """完了を承認"""
        self.approval_status = 'approved'
        self.approved_by = teacher_id
        self.teacher_comments = comments
        # is_completed フィールドは存在しないためコメントアウト
        # self.is_completed = True
        db.session.commit()
    
    def reject_completion(self, teacher_id, reason):
        """完了申請を却下"""
        self.approval_status = 'rejected'
        self.approved_by = teacher_id
        self.teacher_comments = reason
        db.session.commit()
    
    def can_request_completion(self):
        """完了申請が可能かチェック"""
        return (
            # completion_percentage フィールドは存在しないため、常にTrueとする
            # self.completion_percentage >= 80
            self.approval_status in ['none', 'rejected']
        )
    
    def get_approval_status_label(self):
        """承認状況のラベルを取得"""
        status_labels = {
            'none': '未申請',
            'pending': '承認待ち',
            'approved': '承認済み',
            'rejected': '却下',
        }
        return status_labels.get(self.approval_status, '不明')
    
    def to_dict(self):
        """辞書形式で返す（実際のDBスキーマに合わせて修正）"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'lesson_id': self.lesson_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            # 存在しないフィールドはコメントアウト
            # 'time_spent_minutes': self.time_spent_minutes,
            # 'understanding_level': self.understanding_level,
            # 'difficulty_level': self.difficulty_level,
            # 'reflection': self.reflection,
            # 'is_completed': self.is_completed,
            # 'completion_percentage': self.completion_percentage,
            'approval_status': self.approval_status,
            'approval_status_label': self.get_approval_status_label(),
            'completion_request_date': self.completion_request_date.isoformat() if self.completion_request_date else None,
            'teacher_comments': self.teacher_comments,
            'approved_by': self.approved_by,
            # 'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StudentTaskCheck(db.Model):
    """学生のタスクチェック記録モデル"""
    __tablename__ = 'student_task_checks'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    lesson_progress_id = db.Column(db.Integer, db.ForeignKey('student_lesson_progress.id', ondelete='CASCADE'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('lesson_tasks.id', ondelete='CASCADE'), nullable=False)
    
    # チェック状況
    status = db.Column(db.Enum(TaskCheckStatus), default=TaskCheckStatus.NOT_CHECKED)
    checked_at = db.Column(db.DateTime)                   # チェック時刻
    completed_at = db.Column(db.DateTime)                 # 完了時刻
    
    # 学習記録
    time_spent_minutes = db.Column(db.Integer, default=0) # タスクにかけた時間
    notes = db.Column(db.Text)                           # メモ・感想
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    student = db.relationship('User', backref='task_checks')
    
    # ユニーク制約
    __table_args__ = (db.UniqueConstraint('student_id', 'task_id', name='unique_student_task'),)
    
    def __repr__(self):
        return f'<StudentTaskCheck {self.student_id}-{self.task_id}: {self.status.value}>'
    
    def to_dict(self):
        """辞書形式で返す"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'lesson_progress_id': self.lesson_progress_id,
            'task_id': self.task_id,
            'status': self.status.value if self.status else None,
            'checked_at': self.checked_at.isoformat() if self.checked_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'time_spent_minutes': self.time_spent_minutes,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }