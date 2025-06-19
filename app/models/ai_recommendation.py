from datetime import datetime, timedelta
from extensions import db


class AIRecommendation(db.Model):
    """AI推薦履歴テーブル"""
    __tablename__ = 'ai_recommendations'
    
    id = db.Column(db.Integer, primary_key=True, comment='推薦ID')
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='生徒ID')
    recommendation_type = db.Column(db.Enum('unit', 'problem', 'study_path', 'review', 'challenge'), nullable=False, comment='推薦タイプ')
    context_data = db.Column(db.JSON, comment='コンテキストデータ（学習履歴、弱点等）')
    ai_model = db.Column(db.String(50), default='gpt-4', comment='使用AIモデル')
    prompt_template = db.Column(db.Text, comment='使用したプロンプトテンプレート')
    ai_response = db.Column(db.Text, comment='AI生レスポンス')
    recommended_items = db.Column(db.JSON, comment='推薦アイテムID配列')
    confidence_score = db.Column(db.Numeric(3,2), default=0.00, comment='AI推薦信頼度（0.00-1.00）')
    reasoning = db.Column(db.Text, comment='推薦理由')
    is_accepted = db.Column(db.Boolean, default=None, comment='生徒の受け入れ状況（NULL=未回答）')
    is_effective = db.Column(db.Boolean, default=None, comment='効果測定結果')
    feedback_text = db.Column(db.Text, comment='生徒からのフィードバック')
    session_id = db.Column(db.String(100), comment='セッションID')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='作成日時')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新日時')
    
    # インデックス
    __table_args__ = (
        db.Index('idx_student_id', 'student_id'),
        db.Index('idx_recommendation_type', 'recommendation_type'),
        db.Index('idx_session_id', 'session_id'),
        db.Index('idx_created_at', 'created_at'),
        db.Index('idx_is_accepted', 'is_accepted'),
        db.Index('idx_confidence_score', 'confidence_score'),
    )
    
    # リレーションシップ
    student = db.relationship('User', backref='ai_recommendations')
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'recommendation_type': self.recommendation_type,
            'context_data': self.context_data,
            'ai_model': self.ai_model,
            'prompt_template': self.prompt_template,
            'ai_response': self.ai_response,
            'recommended_items': self.recommended_items,
            'confidence_score': float(self.confidence_score) if self.confidence_score else None,
            'reasoning': self.reasoning,
            'is_accepted': self.is_accepted,
            'is_effective': self.is_effective,
            'feedback_text': self.feedback_text,
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def accept_recommendation(self, feedback_text=None):
        """推薦を受け入れる"""
        self.is_accepted = True
        if feedback_text:
            self.feedback_text = feedback_text
        self.updated_at = datetime.utcnow()
    
    def reject_recommendation(self, feedback_text=None):
        """推薦を拒否する"""
        self.is_accepted = False
        if feedback_text:
            self.feedback_text = feedback_text
        self.updated_at = datetime.utcnow()
    
    def get_confidence_level(self):
        """信頼度レベルを文字列で取得"""
        if self.confidence_score >= 0.9:
            return 'very_high'
        elif self.confidence_score >= 0.7:
            return 'high'
        elif self.confidence_score >= 0.5:
            return 'medium'
        elif self.confidence_score >= 0.3:
            return 'low'
        else:
            return 'very_low'
    
    def __repr__(self):
        return f'<AIRecommendation {self.id}: {self.recommendation_type}>'


# 以下のクラスはRDSに存在しないため、将来の実装用にコメントアウト

# class LearningPattern(db.Model):
#     """学習パターン分析テーブル"""
#     __tablename__ = 'learning_patterns'

# class RecommendationSettings(db.Model):
#     """推薦設定テーブル"""
#     __tablename__ = 'recommendation_settings'

# class RecommendationEffectiveness(db.Model):
#     """AI推薦効果測定テーブル"""
#     __tablename__ = 'recommendation_effectiveness'

# class RecommendationAlgorithm(db.Model):
#     """推薦アルゴリズム設定テーブル"""
#     __tablename__ = 'recommendation_algorithms'

# class RecommendationQueue(db.Model):
#     """AI推薦キューテーブル"""
#     __tablename__ = 'recommendation_queue'