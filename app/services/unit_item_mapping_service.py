"""
単元・問題マッピングサービス
==================================================
単元と問題の関連付けを管理し、学習進捗を正しく追跡するためのサービス。
Phase 3実装の一部として、unit_item_mappingsテーブルを活用。

注意: インデントエラーや重複定義を避けるため、慎重に実装
"""

from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime
from sqlalchemy import func, and_, or_

from app.models import db, CurriculumUnit, BasicKnowledgeItem, AnswerRecord, StudentUnitSelection
from app.utils.logger import create_logger

logger = create_logger(__name__)


class UnitItemMappingService:
    """単元と問題のマッピングを管理するサービスクラス"""
    
    @staticmethod
    def get_unit_problems(unit_id: int) -> List[Dict]:
        """
        単元に関連する問題を取得
        
        Args:
            unit_id: 単元ID
            
        Returns:
            問題情報のリスト
        """
        try:
            # unit_item_mappingsテーブルが存在する場合
            result = db.session.execute("""
                SELECT 
                    bki.id,
                    bki.content,
                    bki.options,
                    bki.correct_answer,
                    bki.difficulty_level,
                    uim.weight,
                    uim.order_index
                FROM unit_item_mappings uim
                JOIN basic_knowledge_items bki ON uim.item_id = bki.id
                WHERE uim.unit_id = :unit_id 
                    AND uim.item_type = 'problem'
                    AND bki.is_active = 1
                ORDER BY uim.order_index, uim.weight DESC
            """, {'unit_id': unit_id})
            
            problems = []
            for row in result:
                problems.append({
                    'id': row.id,
                    'content': row.content,
                    'options': json.loads(row.options) if row.options else [],
                    'correct_answer': row.correct_answer,
                    'difficulty_level': row.difficulty_level,
                    'weight': float(row.weight),
                    'order_index': row.order_index
                })
            
            return problems
            
        except Exception as e:
            logger.warning(f"unit_item_mappings not available, falling back: {str(e)}")
            # フォールバック: 教科と難易度で関連問題を推定
            return UnitItemMappingService._get_problems_by_unit_attributes(unit_id)
    
    @staticmethod
    def _get_problems_by_unit_attributes(unit_id: int) -> List[Dict]:
        """
        単元の属性（教科、難易度）から関連問題を推定
        
        Args:
            unit_id: 単元ID
            
        Returns:
            問題情報のリスト
        """
        try:
            unit = CurriculumUnit.query.get(unit_id)
            if not unit:
                return []
            
            # 教科と難易度で問題を検索
            query = BasicKnowledgeItem.query.filter_by(
                subject_id=unit.subject_id,
                is_active=True
            )
            
            if unit.difficulty_level:
                query = query.filter_by(difficulty_level=unit.difficulty_level)
            
            problems = query.limit(50).all()
            
            return [{
                'id': p.id,
                'content': p.content,
                'options': json.loads(p.options) if p.options else [],
                'correct_answer': p.correct_answer,
                'difficulty_level': p.difficulty_level,
                'weight': 1.0,  # デフォルト重み
                'order_index': idx
            } for idx, p in enumerate(problems)]
            
        except Exception as e:
            logger.error(f"Error getting problems by attributes: {str(e)}")
            return []
    
    @staticmethod
    def calculate_unit_progress(student_id: int, unit_id: int) -> Tuple[float, int, int]:
        """
        単元の学習進捗を計算
        
        Args:
            student_id: 学生ID
            unit_id: 単元ID
            
        Returns:
            (進捗率, 正解数, 総問題数)のタプル
        """
        try:
            # 単元に関連する問題を取得
            unit_problems = UnitItemMappingService.get_unit_problems(unit_id)
            if not unit_problems:
                return (0.0, 0, 0)
            
            problem_ids = [p['id'] for p in unit_problems]
            
            # 学生の回答記録を取得
            correct_answers = AnswerRecord.query.filter(
                and_(
                    AnswerRecord.student_id == student_id,
                    AnswerRecord.problem_id.in_(problem_ids),
                    AnswerRecord.is_correct == True
                )
            ).distinct(AnswerRecord.problem_id).count()
            
            total_problems = len(problem_ids)
            progress_percentage = (correct_answers / total_problems * 100) if total_problems > 0 else 0
            
            return (progress_percentage, correct_answers, total_problems)
            
        except Exception as e:
            logger.error(f"Error calculating unit progress: {str(e)}")
            return (0.0, 0, 0)
    
    @staticmethod
    def update_unit_selection_progress(student_id: int, unit_id: int) -> bool:
        """
        StudentUnitSelectionの進捗を更新
        
        Args:
            student_id: 学生ID
            unit_id: 単元ID
            
        Returns:
            更新成功の場合True
        """
        try:
            # 進捗を計算
            progress_percentage, correct_count, total_count = UnitItemMappingService.calculate_unit_progress(
                student_id, unit_id
            )
            
            # StudentUnitSelectionを更新
            selection = StudentUnitSelection.query.filter_by(
                student_id=student_id,
                unit_id=unit_id
            ).first()
            
            if not selection:
                logger.warning(f"No selection found for student {student_id}, unit {unit_id}")
                return False
            
            # 進捗更新
            selection.progress_percentage = progress_percentage
            selection.correct_count = correct_count
            selection.total_count = total_count
            
            # ステータス更新
            if progress_percentage == 0:
                selection.status = 'not_started'
            elif progress_percentage >= 100:
                selection.status = 'completed'
                if not selection.completed_at:
                    selection.completed_at = datetime.utcnow()
            else:
                selection.status = 'in_progress'
            
            db.session.commit()
            
            logger.info(f"Updated progress for student {student_id}, unit {unit_id}: {progress_percentage}%")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating unit selection progress: {str(e)}")
            return False
    
    @staticmethod
    def create_automatic_mappings(unit_id: int, max_problems: int = 50) -> int:
        """
        単元に対して自動的に問題マッピングを作成
        
        Args:
            unit_id: 単元ID
            max_problems: 最大問題数
            
        Returns:
            作成されたマッピング数
        """
        try:
            unit = CurriculumUnit.query.get(unit_id)
            if not unit:
                return 0
            
            # 既存のマッピングをチェック
            existing_count = db.session.execute("""
                SELECT COUNT(*) FROM unit_item_mappings 
                WHERE unit_id = :unit_id
            """, {'unit_id': unit_id}).scalar()
            
            if existing_count > 0:
                logger.info(f"Unit {unit_id} already has {existing_count} mappings")
                return 0
            
            # 関連する問題を検索
            problems = BasicKnowledgeItem.query.filter_by(
                subject_id=unit.subject_id,
                is_active=True
            )
            
            if unit.difficulty_level:
                problems = problems.filter_by(difficulty_level=unit.difficulty_level)
            
            problems = problems.limit(max_problems).all()
            
            # マッピングを作成
            created_count = 0
            for idx, problem in enumerate(problems):
                try:
                    db.session.execute("""
                        INSERT INTO unit_item_mappings 
                        (unit_id, item_id, item_type, weight, order_index)
                        VALUES (:unit_id, :item_id, 'problem', 1.0, :order_index)
                        ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
                    """, {
                        'unit_id': unit_id,
                        'item_id': problem.id,
                        'order_index': idx
                    })
                    created_count += 1
                except Exception as e:
                    logger.warning(f"Failed to create mapping for problem {problem.id}: {str(e)}")
            
            db.session.commit()
            logger.info(f"Created {created_count} mappings for unit {unit_id}")
            return created_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating automatic mappings: {str(e)}")
            return 0
    
    @staticmethod
    def get_unmapped_units() -> List[Dict]:
        """
        マッピングが作成されていない単元を取得
        
        Returns:
            未マッピング単元のリスト
        """
        try:
            result = db.session.execute("""
                SELECT 
                    cu.id,
                    cu.title,
                    cu.subject_id,
                    cu.difficulty_level,
                    COUNT(uim.id) as mapping_count
                FROM curriculum_units cu
                LEFT JOIN unit_item_mappings uim ON cu.id = uim.unit_id
                WHERE cu.is_active = 1
                GROUP BY cu.id
                HAVING mapping_count = 0
            """)
            
            unmapped_units = []
            for row in result:
                unmapped_units.append({
                    'id': row.id,
                    'title': row.title,
                    'subject_id': row.subject_id,
                    'difficulty_level': row.difficulty_level
                })
            
            return unmapped_units
            
        except Exception as e:
            logger.error(f"Error getting unmapped units: {str(e)}")
            return []
    
    @staticmethod
    def batch_create_mappings() -> Dict[str, int]:
        """
        全ての未マッピング単元に対してマッピングを作成
        
        Returns:
            処理結果の統計情報
        """
        try:
            unmapped_units = UnitItemMappingService.get_unmapped_units()
            
            stats = {
                'total_units': len(unmapped_units),
                'processed_units': 0,
                'total_mappings': 0,
                'failed_units': 0
            }
            
            for unit in unmapped_units:
                try:
                    mapping_count = UnitItemMappingService.create_automatic_mappings(unit['id'])
                    if mapping_count > 0:
                        stats['processed_units'] += 1
                        stats['total_mappings'] += mapping_count
                    else:
                        stats['failed_units'] += 1
                except Exception as e:
                    logger.error(f"Failed to process unit {unit['id']}: {str(e)}")
                    stats['failed_units'] += 1
            
            logger.info(f"Batch mapping complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in batch mapping: {str(e)}")
            return {
                'total_units': 0,
                'processed_units': 0,
                'total_mappings': 0,
                'failed_units': 0
            }