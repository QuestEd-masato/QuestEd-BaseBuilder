"""
QuestEd 単元進捗管理サービス

学習記録から単元進捗を自動計算・更新する機能を提供します。
answer_recordsとstudent_unit_selectionsを連携させ、
実際の学習活動を単元進捗に反映します。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, or_, func, text
from flask import current_app

from extensions import db
from app.models import (
    StudentUnitSelection, CurriculumUnit, User
)
from basebuilder.models import (
    AnswerRecord, BasicKnowledgeItem, UnitItemMapping
)

logger = logging.getLogger(__name__)


class UnitProgressManager:
    """単元進捗管理サービス"""
    
    @staticmethod
    def update_unit_progress(student_id: int, unit_id: int) -> Dict[str, any]:
        """
        学習記録から単元進捗を自動計算・更新
        
        Args:
            student_id: 学生ID
            unit_id: 単元ID
            
        Returns:
            更新結果の詳細
        """
        try:
            # 単元に関連する問題を取得
            related_problems = UnitProgressManager._get_unit_related_problems(unit_id)
            
            if not related_problems:
                logger.warning(f"Unit {unit_id} has no related problems")
                return {
                    'success': False,
                    'message': '単元に関連する問題が見つかりません',
                    'progress': 0
                }
            
            # 学習記録から進捗を計算
            progress_data = UnitProgressManager._calculate_progress_from_records(
                student_id, related_problems
            )
            
            # student_unit_selection を更新
            selection = StudentUnitSelection.query.filter_by(
                student_id=student_id,
                unit_id=unit_id
            ).first()
            
            if not selection:
                # 選択記録がない場合は作成
                selection = StudentUnitSelection(
                    student_id=student_id,
                    unit_id=unit_id,
                    status='not_started',
                    progress_percentage=0.0,
                    selected_at=datetime.utcnow()
                )
                db.session.add(selection)
            
            # 進捗データを更新
            selection.progress_percentage = progress_data['progress_percentage']
            selection.total_items = progress_data['total_problems']
            selection.completed_items = progress_data['attempted_problems']
            selection.correct_items = progress_data['correct_problems']
            selection.last_activity_at = progress_data['last_activity']
            
            # ステータス更新
            if progress_data['progress_percentage'] >= 100:
                selection.status = 'completed'
                selection.completed_at = datetime.utcnow()
            elif progress_data['progress_percentage'] > 0:
                selection.status = 'in_progress'
                if not selection.started_at:
                    selection.started_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'progress': progress_data['progress_percentage'],
                'status': selection.status,
                'attempted': progress_data['attempted_problems'],
                'correct': progress_data['correct_problems'],
                'total': progress_data['total_problems']
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update unit progress: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'progress': 0
            }
    
    @staticmethod
    def _get_unit_related_problems(unit_id: int) -> List[int]:
        """単元に関連する問題IDのリストを取得"""
        try:
            # unit_item_mappings から取得（理想）
            mappings = UnitItemMapping.query.filter_by(unit_id=unit_id).all()
            if mappings:
                return [mapping.item_id for mapping in mappings]
            
            # フォールバック: 単元情報から推測
            unit = CurriculumUnit.query.get(unit_id)
            if not unit:
                return []
            
            # subject_id が一致する問題を取得
            problems = BasicKnowledgeItem.query.filter(
                and_(
                    BasicKnowledgeItem.subject_id == unit.subject_id,
                    BasicKnowledgeItem.is_active == True
                )
            ).all()
            
            return [problem.id for problem in problems]
            
        except Exception as e:
            logger.error(f"Failed to get unit related problems: {str(e)}")
            return []
    
    @staticmethod
    def _calculate_progress_from_records(student_id: int, problem_ids: List[int]) -> Dict[str, any]:
        """学習記録から進捗データを計算"""
        try:
            if not problem_ids:
                return {
                    'progress_percentage': 0.0,
                    'total_problems': 0,
                    'attempted_problems': 0,
                    'correct_problems': 0,
                    'last_activity': None
                }
            
            # 回答記録を取得
            records = AnswerRecord.query.filter(
                and_(
                    AnswerRecord.student_id == student_id,
                    AnswerRecord.problem_id.in_(problem_ids)
                )
            ).all()
            
            # 統計計算
            attempted_problems = len(set(record.problem_id for record in records))
            correct_problems = len(set(
                record.problem_id for record in records if record.is_correct
            ))
            last_activity = max(
                (record.created_at for record in records), default=None
            )
            
            # 進捗率計算（正解した問題の割合）
            progress_percentage = (correct_problems / len(problem_ids)) * 100 if problem_ids else 0
            
            return {
                'progress_percentage': round(progress_percentage, 2),
                'total_problems': len(problem_ids),
                'attempted_problems': attempted_problems,
                'correct_problems': correct_problems,
                'last_activity': last_activity
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate progress: {str(e)}")
            return {
                'progress_percentage': 0.0,
                'total_problems': 0,
                'attempted_problems': 0,
                'correct_problems': 0,
                'last_activity': None
            }
    
    @staticmethod
    def create_unit_item_mappings() -> Dict[str, any]:
        """
        単元と問題の自動マッピングを作成
        
        Returns:
            作成結果の詳細
        """
        try:
            created_count = 0
            units = CurriculumUnit.query.filter_by(is_active=True).all()
            
            for unit in units:
                # 既存のマッピングをチェック
                existing_count = UnitItemMapping.query.filter_by(unit_id=unit.id).count()
                if existing_count > 0:
                    continue
                
                # 関連問題を特定
                related_problems = UnitProgressManager._find_related_problems_for_unit(unit)
                
                # マッピング作成
                for index, problem in enumerate(related_problems):
                    mapping = UnitItemMapping(
                        unit_id=unit.id,
                        item_id=problem.id,
                        mapping_type='auto_generated',
                        weight=UnitProgressManager._calculate_relevance_weight(unit, problem),
                        order_index=index,
                        is_required=True,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(mapping)
                    created_count += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'created_mappings': created_count,
                'processed_units': len(units)
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create unit item mappings: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'created_mappings': 0
            }
    
    @staticmethod
    def _find_related_problems_for_unit(unit: CurriculumUnit) -> List:
        """単元に関連する問題を特定"""
        try:
            # 基本的には同じ教科の問題を取得
            query = BasicKnowledgeItem.query.filter(
                and_(
                    BasicKnowledgeItem.is_active == True,
                    BasicKnowledgeItem.subject_id == unit.subject_id
                )
            )
            
            # 難易度でフィルタ（オプション）
            if unit.difficulty_level:
                query = query.filter(
                    BasicKnowledgeItem.difficulty == unit.difficulty_level
                )
            
            # 学校でフィルタ（オプション）
            if unit.school_id:
                query = query.filter(
                    or_(
                        BasicKnowledgeItem.school_id == unit.school_id,
                        BasicKnowledgeItem.school_id.is_(None)
                    )
                )
            
            return query.limit(20).all()  # 最大20問
            
        except Exception as e:
            logger.error(f"Failed to find related problems: {str(e)}")
            return []
    
    @staticmethod
    def _calculate_relevance_weight(unit: CurriculumUnit, problem) -> float:
        """単元と問題の関連度重みを計算"""
        weight = 1.0
        
        # 難易度一致で重み増加
        if unit.difficulty_level and problem.difficulty == unit.difficulty_level:
            weight += 0.2
        
        # 学校一致で重み増加
        if unit.school_id and problem.school_id == unit.school_id:
            weight += 0.1
        
        # キーワード一致チェック（簡易版）
        if unit.title and problem.title:
            if any(word in problem.title for word in unit.title.split()[:3]):
                weight += 0.3
        
        return min(weight, 2.0)  # 最大2.0
    
    @staticmethod
    def batch_update_all_progress() -> Dict[str, any]:
        """全ての生徒の単元進捗を一括更新"""
        try:
            updated_count = 0
            error_count = 0
            
            # アクティブな単元選択を取得
            selections = StudentUnitSelection.query.filter_by(
                status='not_started'
            ).limit(100).all()  # バッチサイズ制限
            
            for selection in selections:
                result = UnitProgressManager.update_unit_progress(
                    selection.student_id,
                    selection.unit_id
                )
                
                if result['success']:
                    updated_count += 1
                else:
                    error_count += 1
            
            return {
                'success': True,
                'updated_count': updated_count,
                'error_count': error_count,
                'processed_total': len(selections)
            }
            
        except Exception as e:
            logger.error(f"Failed to batch update progress: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'updated_count': 0
            }