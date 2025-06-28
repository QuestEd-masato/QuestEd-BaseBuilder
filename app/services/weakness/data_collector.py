"""
Weakness Data Collector
======================
学習データ収集専門モジュール

責任:
- 各種学習システムからのデータ収集
- データの正規化と統合
- 欠損データの処理
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import current_app
from sqlalchemy import func, and_

from extensions import db
from app.models import (
    User, Class, StudentUnitSelection, CurriculumUnit,
    ActivityLog, InquiryTheme, StudentEvaluation
)
from basebuilder.models import (
    AnswerRecord, BasicKnowledgeItem, ProblemCategory,
    TextSet, WordProficiency
)


class WeaknessDataCollector:
    """学習データ収集クラス"""
    
    def __init__(self):
        self.default_days_back = 30  # デフォルトの分析期間
    
    def collect_comprehensive_learning_data(
        self, 
        student_id: int, 
        days_back: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        包括的な学習データを収集
        
        Args:
            student_id: 学生ID
            days_back: 遡る日数（デフォルト30日）
            
        Returns:
            dict: 収集したデータ
        """
        days_back = days_back or self.default_days_back
        start_date = datetime.now() - timedelta(days=days_back)
        
        try:
            data = {
                'student_id': student_id,
                'collection_date': datetime.now(),
                'period_start': start_date,
                'period_end': datetime.now(),
                'answer_records': self._collect_answer_records(student_id, start_date),
                'unit_progress': self._collect_unit_progress(student_id),
                'activity_logs': self._collect_activity_logs(student_id, start_date),
                'inquiry_themes': self._collect_inquiry_themes(student_id),
                'evaluations': self._collect_evaluations(student_id),
                'basebuilder_data': self._collect_basebuilder_data(student_id, start_date)
            }
            
            current_app.logger.info(
                f"Collected comprehensive data for student {student_id}: "
                f"{len(data['answer_records'])} answers, "
                f"{len(data['unit_progress'])} units"
            )
            
            return data
            
        except Exception as e:
            current_app.logger.error(
                f"Error collecting data for student {student_id}: {str(e)}"
            )
            return self._get_empty_data_structure(student_id, start_date)
    
    def _collect_answer_records(
        self, 
        student_id: int, 
        start_date: datetime
    ) -> List[Dict]:
        """回答記録を収集"""
        try:
            records = AnswerRecord.query.filter(
                and_(
                    AnswerRecord.student_id == student_id,
                    AnswerRecord.created_at >= start_date
                )
            ).all()
            
            return [{
                'id': r.id,
                'problem_id': r.problem_id,
                'is_correct': r.is_correct,
                'response_time': r.response_time,
                'created_at': r.created_at,
                'problem': {
                    'id': r.problem.id,
                    'content': r.problem.content,
                    'category_id': r.problem.category_id,
                    'difficulty_level': r.problem.difficulty_level,
                    'subject': r.problem.category.subject if r.problem.category else None
                } if r.problem else None
            } for r in records]
            
        except Exception as e:
            current_app.logger.error(f"Error collecting answer records: {str(e)}")
            return []
    
    def _collect_unit_progress(self, student_id: int) -> List[Dict]:
        """単元進捗を収集"""
        try:
            selections = StudentUnitSelection.query.filter_by(
                student_id=student_id
            ).all()
            
            return [{
                'unit_id': s.unit_id,
                'status': s.status,
                'progress_percentage': s.progress_percentage,
                'started_at': s.started_at,
                'completed_at': s.completed_at,
                'unit': {
                    'id': s.unit.id,
                    'name': s.unit.name,
                    'subject_id': s.unit.subject_id,
                    'estimated_hours': s.unit.estimated_hours
                } if s.unit else None
            } for s in selections]
            
        except Exception as e:
            current_app.logger.error(f"Error collecting unit progress: {str(e)}")
            return []
    
    def _collect_activity_logs(
        self, 
        student_id: int, 
        start_date: datetime
    ) -> List[Dict]:
        """活動ログを収集"""
        try:
            logs = ActivityLog.query.filter(
                and_(
                    ActivityLog.student_id == student_id,
                    ActivityLog.created_at >= start_date
                )
            ).order_by(ActivityLog.created_at.desc()).all()
            
            return [{
                'id': log.id,
                'activity': log.activity,
                'reflection': log.reflection,
                'created_at': log.created_at,
                'main_theme_id': log.main_theme_id,
                'inquiry_theme_id': log.inquiry_theme_id
            } for log in logs]
            
        except Exception as e:
            current_app.logger.error(f"Error collecting activity logs: {str(e)}")
            return []
    
    def _collect_inquiry_themes(self, student_id: int) -> List[Dict]:
        """探究テーマを収集"""
        try:
            themes = InquiryTheme.query.filter_by(
                student_id=student_id
            ).all()
            
            return [{
                'id': theme.id,
                'theme': theme.theme,
                'created_at': theme.created_at,
                'main_theme_id': theme.main_theme_id,
                'activity_count': len(theme.activity_logs)
            } for theme in themes]
            
        except Exception as e:
            current_app.logger.error(f"Error collecting inquiry themes: {str(e)}")
            return []
    
    def _collect_evaluations(self, student_id: int) -> List[Dict]:
        """教師評価を収集"""
        try:
            evaluations = StudentEvaluation.query.filter_by(
                student_id=student_id
            ).order_by(StudentEvaluation.created_at.desc()).all()
            
            return [{
                'id': e.id,
                'evaluation_text': e.evaluation_text,
                'score': e.score,
                'created_at': e.created_at,
                'teacher_id': e.teacher_id
            } for e in evaluations]
            
        except Exception as e:
            current_app.logger.error(f"Error collecting evaluations: {str(e)}")
            return []
    
    def _collect_basebuilder_data(
        self, 
        student_id: int, 
        start_date: datetime
    ) -> Dict[str, Any]:
        """BaseBuilder関連データを収集"""
        try:
            # 単語習熟度
            word_proficiencies = WordProficiency.query.filter_by(
                student_id=student_id
            ).all()
            
            # カテゴリ別回答統計
            category_stats = db.session.query(
                ProblemCategory.id,
                ProblemCategory.name,
                func.count(AnswerRecord.id).label('total_answers'),
                func.sum(func.cast(AnswerRecord.is_correct, db.Integer)).label('correct_answers')
            ).join(
                BasicKnowledgeItem,
                BasicKnowledgeItem.category_id == ProblemCategory.id
            ).join(
                AnswerRecord,
                and_(
                    AnswerRecord.problem_id == BasicKnowledgeItem.id,
                    AnswerRecord.student_id == student_id,
                    AnswerRecord.created_at >= start_date
                )
            ).group_by(ProblemCategory.id).all()
            
            return {
                'word_proficiencies': [{
                    'word': wp.word,
                    'mastery_level': wp.mastery_level,
                    'view_count': wp.view_count,
                    'correct_count': wp.correct_count,
                    'last_seen': wp.last_seen
                } for wp in word_proficiencies],
                'category_performance': [{
                    'category_id': stat.id,
                    'category_name': stat.name,
                    'total_answers': stat.total_answers,
                    'correct_answers': stat.correct_answers or 0,
                    'accuracy': (stat.correct_answers or 0) / stat.total_answers if stat.total_answers > 0 else 0
                } for stat in category_stats]
            }
            
        except Exception as e:
            current_app.logger.error(f"Error collecting BaseBuilder data: {str(e)}")
            return {
                'word_proficiencies': [],
                'category_performance': []
            }
    
    def _get_empty_data_structure(
        self, 
        student_id: int, 
        start_date: datetime
    ) -> Dict[str, Any]:
        """空のデータ構造を返す（エラー時のフォールバック）"""
        return {
            'student_id': student_id,
            'collection_date': datetime.now(),
            'period_start': start_date,
            'period_end': datetime.now(),
            'answer_records': [],
            'unit_progress': [],
            'activity_logs': [],
            'inquiry_themes': [],
            'evaluations': [],
            'basebuilder_data': {
                'word_proficiencies': [],
                'category_performance': []
            }
        }