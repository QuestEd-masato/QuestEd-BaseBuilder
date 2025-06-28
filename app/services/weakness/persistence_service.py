"""
Weakness Persistence Service
============================
データ永続化専門モジュール

責任:
- 分析結果の保存
- キャッシュ管理
- 履歴データの取得
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from flask import current_app
from sqlalchemy import desc

from extensions import db
from app.models import WeaknessAnalysis  # 新しいモデルが必要
from .severity_evaluator import Weakness
from .recommendation_generator import Recommendation


class WeaknessPersistenceService:
    """永続化サービスクラス"""
    
    def __init__(self):
        self.cache_duration_hours = 24  # キャッシュ有効期間
    
    def get_recent_analysis(
        self, 
        student_id: int,
        max_age_hours: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        最近の分析結果を取得
        
        Args:
            student_id: 学生ID
            max_age_hours: 最大経過時間（時間）
            
        Returns:
            dict: 分析結果（キャッシュがある場合）
        """
        max_age_hours = max_age_hours or self.cache_duration_hours
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        try:
            recent_analysis = WeaknessAnalysis.query.filter(
                WeaknessAnalysis.student_id == student_id,
                WeaknessAnalysis.created_at >= cutoff_time
            ).order_by(desc(WeaknessAnalysis.created_at)).first()
            
            if recent_analysis:
                return self._deserialize_analysis(recent_analysis)
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving recent analysis: {str(e)}")
            return None
    
    def save_analysis(self, analysis_result: Dict[str, Any]) -> bool:
        """
        分析結果を保存
        
        Args:
            analysis_result: 分析結果
            
        Returns:
            bool: 保存成功フラグ
        """
        try:
            # 既存の分析を無効化
            self._invalidate_old_analyses(analysis_result['student_id'])
            
            # 新しい分析結果を保存
            new_analysis = WeaknessAnalysis(
                student_id=analysis_result['student_id'],
                analysis_date=analysis_result['analysis_date'],
                weaknesses_json=self._serialize_weaknesses(analysis_result['weaknesses']),
                recommendations_json=self._serialize_recommendations(
                    analysis_result.get('recommendations', [])
                ),
                statistics_json=json.dumps(
                    analysis_result.get('statistics', {}),
                    default=str
                ),
                patterns_json=json.dumps(
                    analysis_result.get('patterns', {}),
                    default=str
                ),
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_analysis)
            db.session.commit()
            
            current_app.logger.info(
                f"Saved weakness analysis for student {analysis_result['student_id']}"
            )
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error saving analysis: {str(e)}")
            db.session.rollback()
            return False
    
    def get_analysis_history(
        self,
        student_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        分析履歴を取得
        
        Args:
            student_id: 学生ID
            limit: 取得件数上限
            
        Returns:
            list: 分析履歴
        """
        try:
            analyses = WeaknessAnalysis.query.filter_by(
                student_id=student_id
            ).order_by(
                desc(WeaknessAnalysis.created_at)
            ).limit(limit).all()
            
            return [self._deserialize_analysis(a) for a in analyses]
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving analysis history: {str(e)}")
            return []
    
    def get_weakness_trends(
        self,
        student_id: int,
        weakness_category: str,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """
        特定の弱点のトレンドを取得
        
        Args:
            student_id: 学生ID
            weakness_category: 弱点カテゴリ
            days_back: 遡る日数
            
        Returns:
            list: トレンドデータ
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            analyses = WeaknessAnalysis.query.filter(
                WeaknessAnalysis.student_id == student_id,
                WeaknessAnalysis.created_at >= cutoff_date
            ).order_by(WeaknessAnalysis.created_at).all()
            
            trends = []
            for analysis in analyses:
                weaknesses = json.loads(analysis.weaknesses_json)
                
                # 指定カテゴリの弱点を探す
                category_weaknesses = [
                    w for w in weaknesses 
                    if w.get('category') == weakness_category
                ]
                
                if category_weaknesses:
                    avg_severity = sum(w['severity'] for w in category_weaknesses) / len(category_weaknesses)
                    trends.append({
                        'date': analysis.created_at,
                        'severity': avg_severity,
                        'count': len(category_weaknesses)
                    })
            
            return trends
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving weakness trends: {str(e)}")
            return []
    
    def delete_old_analyses(self, days_to_keep: int = 90) -> int:
        """
        古い分析結果を削除
        
        Args:
            days_to_keep: 保持する日数
            
        Returns:
            int: 削除した件数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            old_analyses = WeaknessAnalysis.query.filter(
                WeaknessAnalysis.created_at < cutoff_date
            ).all()
            
            count = len(old_analyses)
            
            for analysis in old_analyses:
                db.session.delete(analysis)
            
            db.session.commit()
            
            current_app.logger.info(f"Deleted {count} old weakness analyses")
            
            return count
            
        except Exception as e:
            current_app.logger.error(f"Error deleting old analyses: {str(e)}")
            db.session.rollback()
            return 0
    
    def _invalidate_old_analyses(self, student_id: int):
        """古い分析を無効化"""
        try:
            WeaknessAnalysis.query.filter_by(
                student_id=student_id,
                is_active=True
            ).update({'is_active': False})
            
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Error invalidating old analyses: {str(e)}")
            db.session.rollback()
    
    def _serialize_weaknesses(self, weaknesses: List[Weakness]) -> str:
        """弱点リストをJSON文字列に変換"""
        serialized = []
        
        for weakness in weaknesses:
            serialized.append({
                'category': weakness.category,
                'subcategory': weakness.subcategory,
                'description': weakness.description,
                'severity': weakness.severity,
                'confidence': weakness.confidence,
                'evidence_count': weakness.evidence_count,
                'affected_areas': weakness.affected_areas,
                'trend': weakness.trend,
                'last_occurrence': weakness.last_occurrence.isoformat()
            })
        
        return json.dumps(serialized, ensure_ascii=False)
    
    def _serialize_recommendations(self, recommendations: List[Recommendation]) -> str:
        """推奨事項リストをJSON文字列に変換"""
        serialized = []
        
        for rec in recommendations:
            serialized.append({
                'id': rec.id,
                'weakness_id': rec.weakness_id,
                'title': rec.title,
                'description': rec.description,
                'action_type': rec.action_type,
                'priority': rec.priority,
                'estimated_time_minutes': rec.estimated_time_minutes,
                'resources': rec.resources,
                'prerequisites': rec.prerequisites,
                'expected_outcome': rec.expected_outcome
            })
        
        return json.dumps(serialized, ensure_ascii=False)
    
    def _deserialize_analysis(self, analysis_record: 'WeaknessAnalysis') -> Dict[str, Any]:
        """データベースレコードから分析結果を復元"""
        try:
            weaknesses = json.loads(analysis_record.weaknesses_json)
            recommendations = json.loads(analysis_record.recommendations_json)
            statistics = json.loads(analysis_record.statistics_json) if analysis_record.statistics_json else {}
            patterns = json.loads(analysis_record.patterns_json) if analysis_record.patterns_json else {}
            
            # 日付文字列をdatetimeオブジェクトに変換
            for weakness in weaknesses:
                if 'last_occurrence' in weakness:
                    weakness['last_occurrence'] = datetime.fromisoformat(weakness['last_occurrence'])
            
            return {
                'student_id': analysis_record.student_id,
                'analysis_date': analysis_record.analysis_date,
                'weaknesses': weaknesses,
                'recommendations': recommendations,
                'statistics': statistics,
                'patterns': patterns,
                'created_at': analysis_record.created_at
            }
            
        except Exception as e:
            current_app.logger.error(f"Error deserializing analysis: {str(e)}")
            return {
                'student_id': analysis_record.student_id,
                'analysis_date': analysis_record.analysis_date,
                'weaknesses': [],
                'recommendations': [],
                'statistics': {},
                'patterns': {},
                'created_at': analysis_record.created_at
            }


# 必要に応じてモデルを作成
"""
# app/models.py に追加が必要:

class WeaknessAnalysis(db.Model):
    __tablename__ = 'weakness_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    analysis_date = db.Column(db.DateTime, nullable=False)
    weaknesses_json = db.Column(db.Text, nullable=False)  # JSON形式の弱点データ
    recommendations_json = db.Column(db.Text, nullable=False)  # JSON形式の推奨事項
    statistics_json = db.Column(db.Text)  # JSON形式の統計データ
    patterns_json = db.Column(db.Text)  # JSON形式のパターンデータ
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # リレーション
    student = db.relationship('User', backref='weakness_analyses')
"""