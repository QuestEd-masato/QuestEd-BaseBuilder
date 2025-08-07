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

            # カリキュラムデータの構築（シンプル化）
            curriculum_data = []
            for curriculum in curriculums:
                curriculum_data.append({
                    "curriculum": curriculum,
                    "conversion_status": {"available": False}  # 簡素化
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
                legacy_curriculum_id=curriculum_id
            ).order_by(CurriculumUnit.order_index).all()

            # メインテーマ情報（関連なし）
            main_theme = None
            
            # ルーブリックデータの取得（curriculum_dataフィールドから）
            rubric_info = {}
            if curriculum.curriculum_data:
                import json
                try:
                    data = json.loads(curriculum.curriculum_data)
                    # evaluation_aspectsにデフォルト値を設定
                    evaluation_aspects = data.get('evaluation_aspects', {})
                    if not evaluation_aspects or not isinstance(evaluation_aspects, dict):
                        evaluation_aspects = {
                            'knowledge': 30,
                            'thinking': 40,
                            'attitude': 30
                        }
                    
                    rubric_info = {
                        'rubric': data.get('rubric', []),
                        'evaluation_aspects': evaluation_aspects
                    }
                except:
                    rubric_info = {
                        'rubric': [],
                        'evaluation_aspects': {
                            'knowledge': 30,
                            'thinking': 40,
                            'attitude': 30
                        }
                    }

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

            # 新しいカリキュラム作成（存在するフィールドのみ使用）
            new_curriculum = Curriculum(
                class_id=class_id,
                teacher_id=current_user.id,  # 必須フィールド
                title=curriculum_data.get("title"),
                description=curriculum_data.get("description", ""),
                content=curriculum_data.get("content", ""),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.session.add(new_curriculum)
            db.session.commit()

            return {
                "success": True,
                "curriculum": new_curriculum,
                "curriculum_id": new_curriculum.id,
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
            
            # 構造化データの処理（ルーブリック・テーブル編集データ）
            # Phase修正: 常にcurriculum_dataを初期化・更新する
            import json
            try:
                existing_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            except:
                existing_data = {}
            
            # 更新フラグ
            data_updated = False
            
            # ルーブリックデータ
            if 'rubric_data' in update_data:
                existing_data['rubric'] = update_data['rubric_data']
                data_updated = True
            if 'evaluation_aspects' in update_data:
                existing_data['evaluation_aspects'] = update_data['evaluation_aspects']
                data_updated = True
            
            # テーブル編集データ（Phase 3新機能）
            if 'table_content_data' in update_data:
                table_data = update_data['table_content_data']
                existing_data['table_content'] = table_data
                logger.info(f"[CURRICULUM] Saving table content: {len(table_data) if isinstance(table_data, list) else 'non-list'} rows")
                logger.info(f"[CURRICULUM] Table data type: {type(table_data)}")
                if isinstance(table_data, list) and len(table_data) > 0:
                    logger.info(f"[CURRICULUM] First row sample: {table_data[0]}")
                data_updated = True
                
                # 【Phase 5-2追加】移行アダプター経由でcurriculum_lessonsにも保存
                from .migration_adapter import CurriculumMigrationAdapter
                adapter_content = {
                    'table_content': table_data,
                    'rubric': existing_data.get('rubric', {}),
                    'evaluation_aspects': existing_data.get('evaluation_aspects', {})
                }
                if not CurriculumMigrationAdapter.write_curriculum_content(curriculum_id, adapter_content):
                    logger.warning(f"[CURRICULUM] Failed to sync to curriculum_lessons for curriculum {curriculum_id}")
                else:
                    logger.info(f"[CURRICULUM] Successfully synced to curriculum_lessons table")
            
            # curriculum_dataが空またはNULLの場合でも初期化
            if not curriculum.curriculum_data or data_updated:
                curriculum.curriculum_data = json.dumps(existing_data, ensure_ascii=False)
                logger.debug(f"[CURRICULUM] Updated curriculum_data field with {len(existing_data)} keys")
            
            curriculum.updated_at = datetime.utcnow()
            
            # コミット前の状態をログ
            logger.info(f"[CURRICULUM] About to commit changes for curriculum {curriculum_id}")
            logger.info(f"[CURRICULUM] New curriculum_data length: {len(curriculum.curriculum_data) if curriculum.curriculum_data else 0}")
            
            db.session.commit()
            
            # コミット後の確認
            db.session.refresh(curriculum)
            logger.info(f"[CURRICULUM] After commit - curriculum_data length: {len(curriculum.curriculum_data) if curriculum.curriculum_data else 0}")
            logger.info(f"[CURRICULUM] After commit - updated_at: {curriculum.updated_at}")

            logger.info(f"[CURRICULUM] Successfully updated curriculum {curriculum_id}")
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
            CurriculumUnit.query.filter_by(legacy_curriculum_id=curriculum_id).delete()
            
            # カリキュラム削除
            class_id = curriculum.class_id  # 削除前にclass_idを保存
            db.session.delete(curriculum)
            db.session.commit()

            return {
                "success": True,
                "class_id": class_id,
                "message": "カリキュラムが正常に削除されました"
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting curriculum {curriculum_id}: {str(e)}")
            return {
                "success": False,
                "message": f"カリキュラム削除中にエラーが発生しました: {str(e)}"
            }

    def prepare_curriculum_edit_data(self, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラム編集フォーム用データを準備
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 編集フォーム用データ
        """
        try:
            # 基本詳細データを取得（既存メソッド活用）
            detail_result = self.get_curriculum_detail(curriculum_id)
            if not detail_result['success']:
                return detail_result
            
            # 編集フォーム用に整形
            curriculum = detail_result['curriculum']
            units = detail_result['units']
            
            # 構造化データの解析（ルーブリック・テーブル編集データ）
            structured_data = {}
            if curriculum.curriculum_data:
                try:
                    import json
                    structured_data = json.loads(curriculum.curriculum_data)
                except:
                    structured_data = {}
            
            # テーブル編集データの抽出（Phase 3新機能）
            table_content_data = structured_data.get('table_content', [])
            
            # Service Layer Architecture完全準拠形式で返却
            return {
                "success": True,
                "curriculum": curriculum,
                "units": units,
                "form_data": {
                    'title': curriculum.title,
                    'description': curriculum.description or '',
                    'content': curriculum.content or ''
                },
                "structured_data": structured_data,
                "table_content_data": table_content_data
            }
            
        except Exception as e:
            logger.error(f"Error preparing curriculum edit data {curriculum_id}: {str(e)}")
            return {
                "success": False,
                "message": f"編集データの準備中にエラーが発生しました: {str(e)}"
            }

    def prepare_curriculum_form_data(self, class_id: int) -> Dict[str, Any]:
        """
        カリキュラム作成フォーム用データを準備
        
        Args:
            class_id: クラスID
            
        Returns:
            Dict: フォーム用データ
        """
        try:
            # クラス情報取得と権限チェック（既存パターン踏襲）
            class_obj = Class.query.get(class_id)
            if not class_obj:
                return {
                    "success": False,
                    "message": "クラスが見つかりません"
                }

            # 権限チェック（既存ロジック再利用）
            if class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # フォーム用基本データ準備（最小限）
            form_data = {
                'class': class_obj,
                'form_defaults': {
                    'difficulty_level': 2,
                    'total_hours': 20
                }
            }
            
            return form_data
            
        except Exception as e:
            logger.error(f"Error preparing curriculum form data for class {class_id}: {str(e)}")
            return {
                "success": False,
                "message": f"フォームデータの準備中にエラーが発生しました: {str(e)}"
            }