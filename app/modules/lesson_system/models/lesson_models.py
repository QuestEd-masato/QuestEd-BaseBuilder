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
    NOT_CHECKED = 'not_checked'
    CHECKED = 'checked'
    COMPLETED = 'completed'


class CurriculumLesson(db.Model):
    """カリキュラム内の1時間(50分)レッスンモデル"""
    __tablename__ = 'curriculum_lessons'
    
    id = db.Column(db.Integer, primary_key=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculums.id', ondelete='CASCADE'), nullable=False)
    
    # レッスン基本情報
    lesson_number = db.Column(db.Integer, nullable=False)  # 第○時間目
    title = db.Column(db.String(200), nullable=False)     # レッスンタイトル
    description = db.Column(db.Text)                      # レッスン説明
    lesson_type = db.Column(db.Enum(LessonType), default=LessonType.LECTURE)
    
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
    expected_time_minutes = db.Column(db.Integer, default=10) # 予想所要時間
    
    # 必須・選択
    is_required = db.Column(db.Boolean, default=True)     # 必須タスクかどうか
    weight = db.Column(db.Float, default=1.0)             # 評価重み
    
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
            'expected_time_minutes': self.expected_time_minutes,
            'is_required': self.is_required,
            'weight': self.weight,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StudentLessonProgress(db.Model):
    """学生のレッスン進捗モデル"""
    __tablename__ = 'student_lesson_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('curriculum_lessons.id', ondelete='CASCADE'), nullable=False)
    
    # 進捗状況
    started_at = db.Column(db.DateTime)                   # 開始時刻
    completed_at = db.Column(db.DateTime)                 # 完了時刻
    time_spent_minutes = db.Column(db.Integer, default=0) # 実際の学習時間
    
    # 理解度・振り返り
    understanding_level = db.Column(db.Integer)           # 理解度(1-5)
    difficulty_level = db.Column(db.Integer)              # 難易度(1-5)
    reflection = db.Column(db.Text)                       # 振り返りコメント
    
    # 状況
    is_completed = db.Column(db.Boolean, default=False)   # 完了フラグ
    completion_percentage = db.Column(db.Integer, default=0) # 完了率
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    student = db.relationship('User', backref='lesson_progress')
    task_checks = db.relationship('StudentTaskCheck', backref='lesson_progress', lazy='dynamic', cascade='all, delete-orphan')
    
    # ユニーク制約
    __table_args__ = (db.UniqueConstraint('student_id', 'lesson_id', name='unique_student_lesson'),)
    
    def __repr__(self):
        return f'<StudentLessonProgress {self.student_id}-{self.lesson_id}: {self.completion_percentage}%>'
    
    def to_dict(self):
        """辞書形式で返す"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'lesson_id': self.lesson_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'time_spent_minutes': self.time_spent_minutes,
            'understanding_level': self.understanding_level,
            'difficulty_level': self.difficulty_level,
            'reflection': self.reflection,
            'is_completed': self.is_completed,
            'completion_percentage': self.completion_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
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