# -*- coding: utf-8 -*-
"""
ThemeManagementService

メインテーマの管理を担当する専門サービス
Phase8C: curriculum_management.pyのテーマ関連機能から分離
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app.models import Class, MainTheme, Curriculum, db

logger = logging.getLogger(__name__)


class ThemeManagementService:
    """テーマ管理専門サービス"""

    def get_themes_by_class(self, class_id: int) -> Dict[str, Any]:
        """
        クラスのメインテーマ一覧を取得
        
        Args:
            class_id: クラスID
            
        Returns:
            Dict: テーマ一覧
        """
        try:
            # クラス存在確認と権限チェック
            class_obj = Class.query.get(class_id)
            if not class_obj:
                return {
                    "success": False,
                    "message": "クラスが見つかりません"
                }

            if class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # テーマ一覧取得
            themes = MainTheme.query.filter_by(
                class_id=class_id
            ).order_by(MainTheme.created_at.desc()).all()

            # 各テーマの使用状況を確認
            themes_data = []
            for theme in themes:
                # このテーマを使用しているカリキュラム数
                curriculum_count = Curriculum.query.filter_by(
                    main_theme_id=theme.id
                ).count()
                
                themes_data.append({
                    "theme": theme,
                    "curriculum_count": curriculum_count,
                    "in_use": curriculum_count > 0
                })

            return {
                "success": True,
                "class": class_obj,
                "themes": themes_data,
                "total_count": len(themes)
            }

        except Exception as e:
            logger.error(f"Error getting themes for class {class_id}: {str(e)}")
            return {
                "success": False,
                "message": f"テーマ一覧の取得中にエラーが発生しました: {str(e)}"
            }

    def create_theme(self, class_id: int, theme_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        新しいメインテーマを作成
        
        Args:
            class_id: クラスID
            theme_data: テーマデータ
            
        Returns:
            Dict: 作成結果
        """
        try:
            # クラス存在確認と権限チェック
            class_obj = Class.query.get(class_id)
            if not class_obj:
                return {
                    "success": False,
                    "message": "クラスが見つかりません"
                }

            if class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # データ検証
            validation_result = self._validate_theme_data(theme_data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": "入力データに誤りがあります",
                    "errors": validation_result["errors"]
                }

            # 重複チェック
            existing_theme = MainTheme.query.filter_by(
                class_id=class_id,
                title=theme_data["title"]
            ).first()
            
            if existing_theme:
                return {
                    "success": False,
                    "message": "同じタイトルのテーマが既に存在します"
                }

            # 新しいテーマ作成
            new_theme = MainTheme(
                class_id=class_id,
                title=theme_data["title"],
                description=theme_data.get("description", ""),
                category=theme_data.get("category", "exploration"),
                difficulty_level=theme_data.get("difficulty_level", 2),
                estimated_duration_weeks=theme_data.get("estimated_duration_weeks", 4),
                learning_objectives=theme_data.get("learning_objectives", ""),
                keywords=theme_data.get("keywords", ""),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.session.add(new_theme)
            db.session.commit()

            return {
                "success": True,
                "theme": new_theme,
                "message": "メインテーマが正常に作成されました"
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error creating theme: {str(e)}")
            return {
                "success": False,
                "message": "データベースエラーが発生しました"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating theme: {str(e)}")
            return {
                "success": False,
                "message": f"テーマ作成中にエラーが発生しました: {str(e)}"
            }

    def get_theme_detail(self, theme_id: int) -> Dict[str, Any]:
        """
        テーマの詳細情報を取得
        
        Args:
            theme_id: テーマID
            
        Returns:
            Dict: テーマ詳細
        """
        try:
            theme = MainTheme.query.get(theme_id)
            if not theme:
                return {
                    "success": False,
                    "message": "テーマが見つかりません"
                }

            # 権限チェック
            if theme.class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # 関連カリキュラム情報
            related_curriculums = Curriculum.query.filter_by(
                main_theme_id=theme_id
            ).all()

            return {
                "success": True,
                "theme": theme,
                "related_curriculums": related_curriculums,
                "class": theme.class_obj
            }

        except Exception as e:
            logger.error(f"Error getting theme detail {theme_id}: {str(e)}")
            return {
                "success": False,
                "message": f"テーマ詳細の取得中にエラーが発生しました: {str(e)}"
            }

    def update_theme(self, theme_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        テーマを更新
        
        Args:
            theme_id: テーマID
            update_data: 更新データ
            
        Returns:
            Dict: 更新結果
        """
        try:
            theme = MainTheme.query.get(theme_id)
            if not theme:
                return {
                    "success": False,
                    "message": "テーマが見つかりません"
                }

            # 権限チェック
            if theme.class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # データ検証
            validation_result = self._validate_theme_data(update_data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": "入力データに誤りがあります",
                    "errors": validation_result["errors"]
                }

            # タイトル重複チェック（自分以外）
            if "title" in update_data:
                existing_theme = MainTheme.query.filter(
                    MainTheme.class_id == theme.class_id,
                    MainTheme.title == update_data["title"],
                    MainTheme.id != theme_id
                ).first()
                
                if existing_theme:
                    return {
                        "success": False,
                        "message": "同じタイトルのテーマが既に存在します"
                    }

            # 更新処理
            for key, value in update_data.items():
                if hasattr(theme, key):
                    setattr(theme, key, value)
            
            theme.updated_at = datetime.utcnow()
            db.session.commit()

            return {
                "success": True,
                "theme": theme,
                "message": "テーマが正常に更新されました"
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating theme: {str(e)}")
            return {
                "success": False,
                "message": "データベースエラーが発生しました"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating theme {theme_id}: {str(e)}")
            return {
                "success": False,
                "message": f"テーマ更新中にエラーが発生しました: {str(e)}"
            }

    def delete_theme(self, theme_id: int) -> Dict[str, Any]:
        """
        テーマを削除
        
        Args:
            theme_id: テーマID
            
        Returns:
            Dict: 削除結果
        """
        try:
            theme = MainTheme.query.get(theme_id)
            if not theme:
                return {
                    "success": False,
                    "message": "テーマが見つかりません"
                }

            # 権限チェック
            if theme.class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # 使用状況チェック
            related_curriculums = Curriculum.query.filter_by(
                main_theme_id=theme_id
            ).count()
            
            if related_curriculums > 0:
                return {
                    "success": False,
                    "message": f"このテーマは{related_curriculums}個のカリキュラムで使用されているため削除できません"
                }

            # 削除実行
            db.session.delete(theme)
            db.session.commit()

            return {
                "success": True,
                "message": "テーマが正常に削除されました"
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error deleting theme: {str(e)}")
            return {
                "success": False,
                "message": "データベースエラーが発生しました"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting theme {theme_id}: {str(e)}")
            return {
                "success": False,
                "message": f"テーマ削除中にエラーが発生しました: {str(e)}"
            }

    def _validate_theme_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        テーマデータの妥当性を検証
        
        Args:
            data: テーマデータ
            
        Returns:
            Dict: 検証結果
        """
        errors = []

        # 必須フィールドチェック
        if not data.get("title"):
            errors.append("タイトルは必須です")

        if not data.get("description"):
            errors.append("説明は必須です")

        # カテゴリチェック
        valid_categories = ["exploration", "project", "skill", "research", "creative", "other"]
        if data.get("category") and data["category"] not in valid_categories:
            errors.append(f"カテゴリは {', '.join(valid_categories)} のいずれかを指定してください")

        # 難易度チェック
        difficulty_level = data.get("difficulty_level")
        if difficulty_level is not None:
            if not isinstance(difficulty_level, int) or difficulty_level < 1 or difficulty_level > 5:
                errors.append("難易度は1〜5の範囲で指定してください")

        # 期間チェック
        duration_weeks = data.get("estimated_duration_weeks")
        if duration_weeks is not None:
            if not isinstance(duration_weeks, int) or duration_weeks < 1 or duration_weeks > 52:
                errors.append("推定期間は1〜52週の範囲で指定してください")

        # タイトル長さチェック
        if data.get("title") and len(data["title"]) > 100:
            errors.append("タイトルは100文字以内で入力してください")

        if errors:
            return {
                "valid": False,
                "errors": errors
            }

        return {
            "valid": True,
            "data": data
        }