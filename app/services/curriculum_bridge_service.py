"""
カリキュラムブリッジサービス

レガシーCurriculumシステムと新CurriculumUnitシステムを連携させる
変換・同期機能を提供します。
"""
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, func
from flask import current_app
import json
import logging

from extensions import db
from app.models import (
    Curriculum, CurriculumUnit, StudentUnitSelection,
    Class, User
)

logger = logging.getLogger(__name__)


class CurriculumBridgeService:
    """カリキュラムブリッジサービス"""
    
    # 難易度推定マッピング
    DIFFICULTY_MAPPING = {
        '基礎': 1,
        '標準': 2, 
        '応用': 3,
        '発展': 3,
        '入門': 1,
        '初級': 1,
        '中級': 2,
        '上級': 3,
        '初心者': 1,
        'beginner': 1,
        'intermediate': 2,
        'advanced': 3
    }
    
    @classmethod
    def convert_curriculum_to_units(cls, curriculum_id: int, created_by: int) -> Dict[str, any]:
        """
        既存カリキュラムを自由進度学習単元に変換
        
        Args:
            curriculum_id: 変換対象のカリキュラムID
            created_by: 作成者のユーザーID
            
        Returns:
            変換結果の詳細
        """
        try:
            # カリキュラム取得
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                raise ValueError(f"カリキュラムID {curriculum_id} が見つかりません")
            
            # カリキュラムアイテムの解析
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            items = curriculum_data.get('items', [])
            
            if not items:
                logger.warning(f"カリキュラムID {curriculum_id} にはアイテムがありません")
                return {
                    'success': False,
                    'message': 'カリキュラムにアイテムが含まれていません',
                    'converted_count': 0
                }
            
            # 既存の変換済み単元をチェック
            existing_units = CurriculumUnit.query.filter_by(
                legacy_curriculum_id=curriculum_id
            ).all()
            
            converted_count = 0
            updated_count = 0
            
            # アイテムごとに単元を作成・更新
            for index, item in enumerate(items):
                # 既存単元の確認
                existing_unit = next(
                    (u for u in existing_units if u.order_index == index), 
                    None
                )
                
                if existing_unit:
                    # 既存単元を更新
                    cls._update_curriculum_unit(existing_unit, item, index)
                    updated_count += 1
                else:
                    # 新規単元を作成
                    new_unit = cls._create_curriculum_unit(
                        curriculum, item, index, created_by
                    )
                    db.session.add(new_unit)
                    converted_count += 1
            
            # 変換情報をカリキュラムに記録
            curriculum.is_converted_to_units = True
            curriculum.units_conversion_date = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"カリキュラム変換完了: {converted_count}件作成, {updated_count}件更新")
            
            return {
                'success': True,
                'message': f'カリキュラムの変換が完了しました',
                'converted_count': converted_count,
                'updated_count': updated_count,
                'total_items': len(items)
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"カリキュラム変換エラー: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'変換中にエラーが発生しました: {str(e)}',
                'converted_count': 0
            }
    
    @classmethod
    def _create_curriculum_unit(cls, curriculum: Curriculum, item: Dict, 
                               index: int, created_by: int) -> CurriculumUnit:
        """カリキュラムアイテムから新規単元を作成"""
        
        # タイトル生成
        title = cls._generate_unit_title(item)
        
        # 説明生成
        description = cls._generate_unit_description(item)
        
        # 難易度推定
        difficulty_level = cls._estimate_difficulty(item)
        
        # 学習時間推定
        estimated_minutes = cls._estimate_learning_time(item)
        
        # 新規単元作成
        unit = CurriculumUnit(
            title=title,
            description=description,
            difficulty_level=difficulty_level,
            estimated_minutes=estimated_minutes,
            order_index=index,
            is_active=True,
            school_id=curriculum.class_obj.school_id if curriculum.class_obj and curriculum.class_obj.school_id else None,
            created_by=created_by,
            legacy_curriculum_id=curriculum.id,
            
            # 追加メタデータ
            unit_code=f"CONV_{curriculum.id}_{index:03d}",
            learning_objectives=item.get('evaluation_method', ''),
            tags=json.dumps([
                item.get('phase', ''),
                item.get('category', ''),
                'converted'
            ], ensure_ascii=False)
        )
        
        return unit
    
    @classmethod
    def _update_curriculum_unit(cls, unit: CurriculumUnit, item: Dict, index: int):
        """既存単元をアイテム情報で更新"""
        
        unit.title = cls._generate_unit_title(item)
        unit.description = cls._generate_unit_description(item)
        unit.difficulty_level = cls._estimate_difficulty(item)
        unit.estimated_minutes = cls._estimate_learning_time(item)
        unit.updated_at = datetime.utcnow()
        
        # メタデータ更新
        unit.learning_objectives = item.get('evaluation_method', '')
        unit.tags = json.dumps([
            item.get('phase', ''),
            item.get('category', ''),
            'converted'
        ], ensure_ascii=False)
    
    @classmethod
    def _generate_unit_title(cls, item: Dict) -> str:
        """アイテム情報から単元タイトルを生成"""
        phase = item.get('phase', '')
        week = item.get('week', '')
        activity = item.get('activity', '')
        
        # タイトル生成ロジック
        if phase and week:
            title = f"{phase}第{week}週"
        elif phase:
            title = phase
        elif week:
            title = f"第{week}週"
        else:
            title = "学習単元"
        
        # 活動内容を追加（50文字まで）
        if activity:
            activity_short = activity[:50] + '...' if len(activity) > 50 else activity
            title += f" - {activity_short}"
        
        return title
    
    @classmethod
    def _generate_unit_description(cls, item: Dict) -> str:
        """アイテム情報から単元説明を生成"""
        description_parts = []
        
        # 活動内容
        if item.get('activity'):
            description_parts.append(f"【学習内容】\n{item['activity']}")
        
        # 教師サポート
        if item.get('teacher_support'):
            description_parts.append(f"【指導のポイント】\n{item['teacher_support']}")
        
        # 評価方法
        if item.get('evaluation_method'):
            description_parts.append(f"【評価方法】\n{item['evaluation_method']}")
        
        # カテゴリ情報
        if item.get('category'):
            description_parts.append(f"【関連分野】\n{item['category']}")
        
        return '\n\n'.join(description_parts) if description_parts else '学習単元の説明'
    
    @classmethod
    def _estimate_difficulty(cls, item: Dict) -> int:
        """アイテム情報から難易度を推定"""
        
        # カテゴリベースの推定
        category = item.get('category', '').lower()
        for keyword, level in cls.DIFFICULTY_MAPPING.items():
            if keyword in category:
                return level
        
        # フェーズベースの推定
        phase = item.get('phase', '').lower()
        if any(word in phase for word in ['導入', '基礎', '入門']):
            return 1
        elif any(word in phase for word in ['発展', '応用', '上級']):
            return 3
        else:
            return 2  # デフォルト
    
    @classmethod
    def _estimate_learning_time(cls, item: Dict) -> int:
        """アイテム情報から学習時間を推定"""
        
        # 時間数が直接指定されている場合
        hours = item.get('hours', 0)
        if hours and isinstance(hours, (int, float)):
            return int(hours * 60)  # 分に変換
        
        # 活動内容の長さから推定
        activity = item.get('activity', '')
        if len(activity) > 200:
            return 90  # 長い説明 = 複雑な内容
        elif len(activity) > 100:
            return 60  # 中程度
        else:
            return 45  # 短時間
    
    @classmethod
    def sync_curriculum_updates(cls, curriculum_id: int) -> Dict[str, any]:
        """
        カリキュラム更新時の自動同期
        
        Args:
            curriculum_id: 更新されたカリキュラムID
            
        Returns:
            同期結果
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {'success': False, 'message': 'カリキュラムが見つかりません'}
            
            # 既存の変換済み単元が存在するかチェック
            existing_units = CurriculumUnit.query.filter_by(
                legacy_curriculum_id=curriculum_id
            ).count()
            
            if existing_units > 0:
                # 既存単元を更新
                return cls.convert_curriculum_to_units(curriculum_id, curriculum.created_by)
            else:
                return {'success': True, 'message': '同期対象の単元がありません'}
                
        except Exception as e:
            logger.error(f"カリキュラム同期エラー: {str(e)}", exc_info=True)
            return {'success': False, 'message': f'同期エラー: {str(e)}'}
    
    @classmethod
    def get_conversion_status(cls, curriculum_id: int) -> Dict[str, any]:
        """
        カリキュラムの変換状況を取得
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            変換状況の詳細
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {'exists': False}
            
            # 変換済み単元数
            converted_units = CurriculumUnit.query.filter_by(
                legacy_curriculum_id=curriculum_id
            ).count()
            
            # カリキュラムアイテム数
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            total_items = len(curriculum_data.get('items', []))
            
            return {
                'exists': True,
                'is_converted': getattr(curriculum, 'is_converted_to_units', False),
                'conversion_date': getattr(curriculum, 'units_conversion_date', None),
                'total_items': total_items,
                'converted_units': converted_units,
                'conversion_rate': (converted_units / total_items * 100) if total_items > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"変換状況取得エラー: {str(e)}", exc_info=True)
            return {'exists': False, 'error': str(e)}
    
    @classmethod
    def get_converted_units_for_students(cls, class_id: int) -> List[Dict]:
        """
        クラスの変換済み単元を生徒表示用形式で取得
        
        Args:
            class_id: クラスID
            
        Returns:
            生徒表示用の単元リスト
        """
        try:
            # クラスのカリキュラムを取得
            curriculum = Curriculum.query.filter_by(class_id=class_id).first()
            if not curriculum:
                return []
            
            # 変換済み単元を取得
            units = CurriculumUnit.query.filter_by(
                legacy_curriculum_id=curriculum.id,
                is_active=True
            ).order_by(CurriculumUnit.order_index).all()
            
            return [unit.to_dict() for unit in units]
            
        except Exception as e:
            logger.error(f"変換済み単元取得エラー: {str(e)}", exc_info=True)
            return []