# -*- coding: utf-8 -*-
"""
CurriculumDataService

カリキュラムの基本的なCRUD操作を管理する専門サービス
Phase8C: curriculum_management.pyから分離
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from flask import current_app
from flask_login import current_user
from sqlalchemy import func

from app.models import (
    Class,
    Curriculum,
    CurriculumUnit,
    MainTheme,
    Subject,
    User,
    db
)

logger = logging.getLogger(__name__)


class CurriculumDataService:
    """カリキュラムデータ管理専門サービス"""

    def get_curriculums_by_class(self, class_id: int) -> Dict[str, Any]:
        """
        クラスのカリキュラム一覧を取得
        
        Args:
            class_id: クラスID
            
        Returns:
            Dict: カリキュラム一覧と関連情報
        """
        try:
            # クラス情報取得
            class_obj = Class.query.get(class_id)
            if not class_obj:
                return {
                    "success": False,
                    "message": "クラスが見つかりません"
                }

            # 権限チェック
            if class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # カリキュラム一覧取得
            curriculums = Curriculum.query.filter_by(
                class_id=class_id
            ).order_by(Curriculum.created_at.desc()).all()

            # 変換ステータス取得（CurriculumBridgeService連携）
            from app.services.curriculum_bridge_service import CurriculumBridgeService
            
            curriculum_data = []
            for curriculum in curriculums:
                conversion_status = CurriculumBridgeService.get_conversion_status(curriculum.id)
                curriculum_data.append({
                    "curriculum": curriculum,
                    "conversion_status": conversion_status
                })

            return {
                "success": True,
                "class": class_obj,
                "curriculums": curriculum_data,
                "total_count": len(curriculums)
            }

        except Exception as e:
            logger.error(f"Error getting curriculums for class {class_id}: {str(e)}")
            return {
                "success": False,
                "message": f"カリキュラム一覧の取得中にエラーが発生しました: {str(e)}"
            }

    def get_curriculum_detail(self, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラム詳細情報を取得
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: カリキュラム詳細情報
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {
                    "success": False,
                    "message": "カリキュラムが見つかりません"
                }

            # 権限チェック
            if curriculum.class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # 関連データ取得
            units = CurriculumUnit.query.filter_by(
                curriculum_id=curriculum_id
            ).order_by(CurriculumUnit.order_index).all()

            # メインテーマ情報
            main_theme = MainTheme.query.get(curriculum.main_theme_id) if curriculum.main_theme_id else None
            
            # ルーブリックデータの取得（curriculum_dataフィールドから）
            rubric_info = {}
            if curriculum.curriculum_data:
                import json
                try:
                    data = json.loads(curriculum.curriculum_data)
                    rubric_info = {
                        'rubric': data.get('rubric', {}),
                        'evaluation_aspects': data.get('evaluation_aspects', {})
                    }
                except:
                    rubric_info = {}

            return {
                "success": True,
                "curriculum": curriculum,
                "units": units,
                "main_theme": main_theme,
                "class": curriculum.class_obj,
                "rubric_info": rubric_info
            }

        except Exception as e:
            logger.error(f"Error getting curriculum detail {curriculum_id}: {str(e)}")
            return {
                "success": False,
                "message": f"カリキュラム詳細の取得中にエラーが発生しました: {str(e)}"
            }

    def create_curriculum(self, class_id: int, curriculum_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        新しいカリキュラムを作成
        
        Args:
            class_id: クラスID
            curriculum_data: カリキュラムデータ
            
        Returns:
            Dict: 作成結果
        """
        try:
            # クラスと権限チェック
            class_obj = Class.query.get(class_id)
            if not class_obj or class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # 新しいカリキュラム作成
            new_curriculum = Curriculum(
                class_id=class_id,
                title=curriculum_data.get("title"),
                description=curriculum_data.get("description", ""),
                main_theme_id=curriculum_data.get("main_theme_id"),
                total_classes=curriculum_data.get("total_classes", 35),
                total_hours=curriculum_data.get("total_hours", 29.2),
                difficulty_level=curriculum_data.get("difficulty_level", 2),
                self_paced_mode=curriculum_data.get("self_paced_mode", "flexible"),
                content=curriculum_data.get("content", ""),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.session.add(new_curriculum)
            db.session.commit()

            return {
                "success": True,
                "curriculum": new_curriculum,
                "message": "カリキュラムが正常に作成されました"
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating curriculum: {str(e)}")
            return {
                "success": False,
                "message": f"カリキュラム作成中にエラーが発生しました: {str(e)}"
            }

    def update_curriculum(self, curriculum_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        カリキュラムを更新
        
        Args:
            curriculum_id: カリキュラムID
            update_data: 更新データ
            
        Returns:
            Dict: 更新結果
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {
                    "success": False,
                    "message": "カリキュラムが見つかりません"
                }

            # 権限チェック
            if curriculum.class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # 更新処理
            for key, value in update_data.items():
                if hasattr(curriculum, key):
                    setattr(curriculum, key, value)
            
            # ルーブリックデータの処理（既存curriculum_dataフィールドを活用）
            if 'rubric_data' in update_data or 'evaluation_aspects' in update_data:
                import json
                try:
                    existing_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
                except:
                    existing_data = {}
                
                if 'rubric_data' in update_data:
                    existing_data['rubric'] = update_data['rubric_data']
                if 'evaluation_aspects' in update_data:
                    existing_data['evaluation_aspects'] = update_data['evaluation_aspects']
                
                curriculum.curriculum_data = json.dumps(existing_data, ensure_ascii=False)
            
            curriculum.updated_at = datetime.utcnow()
            db.session.commit()

            return {
                "success": True,
                "curriculum": curriculum,
                "message": "カリキュラムが正常に更新されました"
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating curriculum {curriculum_id}: {str(e)}")
            return {
                "success": False,
                "message": f"カリキュラム更新中にエラーが発生しました: {str(e)}"
            }

    def delete_curriculum(self, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラムを削除
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 削除結果
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {
                    "success": False,
                    "message": "カリキュラムが見つかりません"
                }

            # 権限チェック
            if curriculum.class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # 関連データ削除
            CurriculumUnit.query.filter_by(curriculum_id=curriculum_id).delete()
            
            # カリキュラム削除
            db.session.delete(curriculum)
            db.session.commit()

            return {
                "success": True,
                "message": "カリキュラムが正常に削除されました"
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting curriculum {curriculum_id}: {str(e)}")
            return {
                "success": False,
                "message": f"カリキュラム削除中にエラーが発生しました: {str(e)}"
            }