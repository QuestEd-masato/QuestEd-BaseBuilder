from datetime import datetime
from extensions import db


class CurriculumUnit(db.Model):
    """学習単元マスタテーブル"""
    __tablename__ = 'curriculum_units'
    
    id = db.Column(db.Integer, primary_key=True, comment='単元ID')
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False, comment='教科ID')
    unit_code = db.Column(db.String(20), unique=True, nullable=False, comment='単元コード')
    title = db.Column(db.String(200), nullable=False, comment='単元名')
    description = db.Column(db.Text, comment='単元説明')
    difficulty_level = db.Column(db.Integer, default=1, comment='難易度レベル（1-5）')
    estimated_hours = db.Column(db.Numeric(4,2), default=1.00, comment='推定学習時間')
    prerequisites = db.Column(db.JSON, comment='前提単元ID配列')
    learning_objectives = db.Column(db.Text, comment='学習目標')
    tags = db.Column(db.JSON, comment='タグ配列')
    order_index = db.Column(db.Integer, default=0, comment='表示順序')
    is_active = db.Column(db.Boolean, default=True, comment='有効フラグ')
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=True, comment='学校ID（NULL=全校共通）')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='作成者ID')
    legacy_curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculums.id'), nullable=True, comment='レガシーカリキュラムID')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='作成日時')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新日時')
    
    # インデックス
    __table_args__ = (
        db.Index('idx_subject_id', 'subject_id'),
        db.Index('idx_difficulty_level', 'difficulty_level'),
        db.Index('idx_school_id', 'school_id'),
        db.Index('idx_is_active', 'is_active'),
        db.Index('idx_order_index', 'order_index'),
    )
    
    # リレーションシップ
    subject = db.relationship('Subject', backref='curriculum_units')
    school = db.relationship('School', backref='curriculum_units')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_units')
    legacy_curriculum = db.relationship('Curriculum', backref='migrated_units')
    
    # 単元と問題の紐付け
    unit_mappings = db.relationship('UnitItemMapping', backref='curriculum_unit', lazy='dynamic', cascade='all, delete-orphan')
    
    # 生徒の選択履歴
    student_selections = db.relationship('StudentUnitSelection', backref='curriculum_unit', lazy='dynamic', cascade='all, delete-orphan')
    
    # AI推薦での利用
    ai_recommendations = db.relationship('AIRecommendation', 
                                       primaryjoin="and_(foreign(AIRecommendation.recommended_items).contains(cast(CurriculumUnit.id, String)), AIRecommendation.recommendation_type=='unit')",
                                       viewonly=True)
    
    # 学習パスでの利用
    # path_units = db.relationship('LearningPathUnit', backref='curriculum_unit', lazy='dynamic', cascade='all, delete-orphan')  # LearningPathUnitがコメントアウトされているため
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'unit_code': self.unit_code,
            'title': self.title,
            'description': self.description,
            'difficulty_level': self.difficulty_level,
            'estimated_hours': float(self.estimated_hours) if self.estimated_hours else None,
            'prerequisites': self.prerequisites,
            'learning_objectives': self.learning_objectives,
            'tags': self.tags,
            'order_index': self.order_index,
            'is_active': self.is_active,
            'school_id': self.school_id,
            'created_by': self.created_by,
            'legacy_curriculum_id': self.legacy_curriculum_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'subject_name': self.subject.name if self.subject else None,
            'subject_code': self.subject.code if self.subject else None
        }
    
    def get_mapped_problems(self):
        """紐付けられた問題を取得"""
        from basebuilder.models import BasicKnowledgeItem
        mappings = self.unit_mappings.filter_by(is_required=True).order_by(UnitItemMapping.order_index).all()
        problem_ids = [mapping.item_id for mapping in mappings]
        return BasicKnowledgeItem.query.filter(BasicKnowledgeItem.id.in_(problem_ids)).all()
    
    def get_student_progress(self, student_id, class_id=None):
        """指定生徒の学習進捗を取得"""
        selection = self.student_selections.filter_by(
            student_id=student_id,
            class_id=class_id
        ).first()
        return selection
    
    def check_prerequisites(self, student_id, class_id=None):
        """前提条件をチェック"""
        if not self.prerequisites:
            return True
        
        for prerequisite_id in self.prerequisites:
            prerequisite_unit = CurriculumUnit.query.get(prerequisite_id)
            if prerequisite_unit:
                progress = prerequisite_unit.get_student_progress(student_id, class_id)
                if not progress or progress.status != 'completed':
                    return False
        return True
    
    def get_difficulty_label(self):
        """難易度のラベルを取得"""
        difficulty_labels = {
            1: '基礎',
            2: '標準',
            3: '応用',
            4: '発展',
            5: '最難関'
        }
        return difficulty_labels.get(self.difficulty_level, '不明')
    
    def __repr__(self):
        return f'<CurriculumUnit {self.unit_code}: {self.title}>'


class UnitItemMapping(db.Model):
    """単元と問題の紐付けテーブル"""
    __tablename__ = 'unit_item_mappings'
    
    id = db.Column(db.Integer, primary_key=True, comment='マッピングID')
    unit_id = db.Column(db.Integer, db.ForeignKey('curriculum_units.id'), nullable=False, comment='単元ID')
    item_id = db.Column(db.Integer, db.ForeignKey('basic_knowledge_items.id'), nullable=False, comment='問題ID')
    weight = db.Column(db.Numeric(3,2), default=1.00, comment='重み（重要度）')
    order_index = db.Column(db.Integer, default=0, comment='単元内での表示順序')
    is_required = db.Column(db.Boolean, default=True, comment='必須問題フラグ')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='作成日時')
    
    # ユニーク制約とインデックス
    __table_args__ = (
        db.UniqueConstraint('unit_id', 'item_id', name='uk_unit_item'),
        db.Index('idx_unit_id', 'unit_id'),
        db.Index('idx_item_id', 'item_id'),
        db.Index('idx_is_required', 'is_required'),
        db.Index('idx_order_index', 'order_index'),
    )
    
    # リレーションシップ
    basic_knowledge_item = db.relationship('BasicKnowledgeItem', backref='unit_mappings')
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'unit_id': self.unit_id,
            'item_id': self.item_id,
            'weight': float(self.weight) if self.weight else None,
            'order_index': self.order_index,
            'is_required': self.is_required,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<UnitItemMapping unit:{self.unit_id} item:{self.item_id}>'


class StudentUnitSelection(db.Model):
    """生徒の単元選択履歴テーブル"""
    __tablename__ = 'student_unit_selections'
    
    id = db.Column(db.Integer, primary_key=True, comment='選択履歴ID')
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='生徒ID')
    unit_id = db.Column(db.Integer, db.ForeignKey('curriculum_units.id'), nullable=False, comment='単元ID')
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True, comment='クラスID')
    status = db.Column(db.Enum('not_started', 'in_progress', 'completed', 'paused'), default='not_started', comment='学習状況')
    progress_percentage = db.Column(db.Numeric(5,2), default=0.00, comment='進捗率（%）')
    total_items = db.Column(db.Integer, default=0, comment='総問題数')
    completed_items = db.Column(db.Integer, default=0, comment='完了問題数')
    correct_items = db.Column(db.Integer, default=0, comment='正解問題数')
    started_at = db.Column(db.DateTime, nullable=True, comment='開始日時')
    completed_at = db.Column(db.DateTime, nullable=True, comment='完了日時')
    last_activity_at = db.Column(db.DateTime, nullable=True, comment='最終活動日時')
    study_time_minutes = db.Column(db.Integer, default=0, comment='学習時間（分）')
    notes = db.Column(db.Text, comment='学習メモ')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='作成日時')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新日時')
    
    # ユニーク制約とインデックス
    __table_args__ = (
        db.UniqueConstraint('student_id', 'unit_id', 'class_id', name='uk_student_unit_class'),
        db.Index('idx_student_id', 'student_id'),
        db.Index('idx_unit_id', 'unit_id'),
        db.Index('idx_class_id', 'class_id'),
        db.Index('idx_status', 'status'),
        db.Index('idx_last_activity_at', 'last_activity_at'),
        db.Index('idx_progress_percentage', 'progress_percentage'),
    )
    
    # リレーションシップ
    student = db.relationship('User', backref='unit_selections')
    class_obj = db.relationship('Class', backref='unit_selections')
    
    def update_progress(self):
        """進捗率を再計算"""
        if self.total_items > 0:
            self.progress_percentage = (self.completed_items / self.total_items) * 100
        else:
            self.progress_percentage = 0.00
        
        # ステータスの自動更新
        if self.completed_items == 0:
            self.status = 'not_started'
        elif self.completed_items == self.total_items:
            self.status = 'completed'
            if not self.completed_at:
                self.completed_at = datetime.utcnow()
        else:
            if self.status == 'not_started':
                self.status = 'in_progress'
                if not self.started_at:
                    self.started_at = datetime.utcnow()
        
        self.last_activity_at = datetime.utcnow()
    
    def get_accuracy_rate(self):
        """正解率を計算"""
        if self.completed_items > 0:
            return (self.correct_items / self.completed_items) * 100
        return 0.0
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'unit_id': self.unit_id,
            'class_id': self.class_id,
            'status': self.status,
            'progress_percentage': float(self.progress_percentage) if self.progress_percentage else 0.0,
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'correct_items': self.correct_items,
            'accuracy_rate': self.get_accuracy_rate(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_activity_at': self.last_activity_at.isoformat() if self.last_activity_at else None,
            'study_time_minutes': self.study_time_minutes,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<StudentUnitSelection student:{self.student_id} unit:{self.unit_id} status:{self.status}>'


class ClassLearningSettings(db.Model):
    """クラス別学習設定テーブル"""
    __tablename__ = 'class_learning_settings'
    
    id = db.Column(db.Integer, primary_key=True, comment='設定ID')
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False, comment='クラスID')
    allow_free_progress = db.Column(db.Boolean, default=True, comment='自由進度学習許可')
    require_unit_order = db.Column(db.Boolean, default=False, comment='単元順序強制')
    max_concurrent_units = db.Column(db.Integer, default=3, comment='同時学習可能単元数')
    min_completion_rate = db.Column(db.Numeric(5,2), default=80.00, comment='単元完了最低正解率（%）')
    allow_unit_skip = db.Column(db.Boolean, default=False, comment='単元スキップ許可')
    show_difficulty_level = db.Column(db.Boolean, default=True, comment='難易度表示')
    enable_peer_comparison = db.Column(db.Boolean, default=False, comment='他生徒との比較表示')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='設定作成者ID')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='作成日時')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新日時')
    
    # ユニーク制約とインデックス
    __table_args__ = (
        db.UniqueConstraint('class_id', name='uk_class_learning_settings'),
        db.Index('idx_allow_free_progress', 'allow_free_progress'),
    )
    
    # リレーションシップ
    class_obj = db.relationship('Class', backref=db.backref('learning_settings', uselist=False))
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_learning_settings')
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'class_id': self.class_id,
            'allow_free_progress': self.allow_free_progress,
            'require_unit_order': self.require_unit_order,
            'max_concurrent_units': self.max_concurrent_units,
            'min_completion_rate': float(self.min_completion_rate) if self.min_completion_rate else None,
            'allow_unit_skip': self.allow_unit_skip,
            'show_difficulty_level': self.show_difficulty_level,
            'enable_peer_comparison': self.enable_peer_comparison,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<ClassLearningSettings class:{self.class_id}>'


class LearningPath(db.Model):
    """単元学習パスマスタテーブル"""
    __tablename__ = 'learning_paths'
    
    id = db.Column(db.Integer, primary_key=True, comment='パスID')
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False, comment='クラスID')
    path_name = db.Column(db.String(100), nullable=False, comment='パス名')
    description = db.Column(db.Text, comment='パス説明')
    is_default = db.Column(db.Boolean, default=False, comment='デフォルトパス')
    is_active = db.Column(db.Boolean, default=True, comment='有効フラグ')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='作成者ID')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='作成日時')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新日時')
    
    # インデックス
    __table_args__ = (
        db.Index('idx_class_id', 'class_id'),
        db.Index('idx_is_default', 'is_default'),
        db.Index('idx_is_active', 'is_active'),
    )
    
    # リレーションシップ
    class_obj = db.relationship('Class', backref='learning_paths')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_paths')
    # path_units = db.relationship('LearningPathUnit', backref='learning_path', lazy='dynamic', cascade='all, delete-orphan')  # LearningPathUnitがコメントアウトされているため
    
    def get_ordered_units(self):
        """順序付けされた単元リストを取得"""
        # return self.path_units.order_by(LearningPathUnit.sequence_order).all()  # LearningPathUnitがコメントアウトされているため
        return []  # 暫定的に空リストを返す
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'class_id': self.class_id,
            'path_name': self.path_name,
            'description': self.description,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'unit_count': 0  # self.path_units.count() - LearningPathUnitがコメントアウトされているため
        }
    
    def __repr__(self):
        return f'<LearningPath {self.path_name}>'


# 以下のクラスはRDSに存在しない可能性があるため、将来の実装用にコメントアウト

# class LearningPathUnit(db.Model):
#     """学習パス詳細テーブル"""
#     __tablename__ = 'learning_path_units'