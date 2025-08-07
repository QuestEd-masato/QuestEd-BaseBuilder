# -*- coding: utf-8 -*-
"""
Curriculum Orchestration Service

カリキュラム統合制御サービス
Phase8F: curriculum_management.pyのView関数軽量化のための統合制御層
"""
import logging
from typing import Dict, List, Any, Optional
from flask import current_app, render_template
from flask_login import current_user

logger = logging.getLogger(__name__)


class CurriculumOrchestrationService:
    """カリキュラム統合制御サービス"""
    
    def __init__(self):
        """サービス初期化"""
        # Phase8C既存サービスをインポート
        from .curriculum_data_service import CurriculumDataService
        from .curriculum_validation_service import CurriculumValidationService
        from .curriculum_ai_service import CurriculumAIService
        from .curriculum_import_export_service import CurriculumImportExportService
        # 新システムに統一: lesson_systemを使用
        from app.modules.lesson_system.services.lesson_service import LessonService
        from .theme_management_service import ThemeManagementService
        from .teacher_curriculum_unit_service import TeacherCurriculumUnitService
        
        # サービス初期化
        self.data_service = CurriculumDataService()
        self.validation_service = CurriculumValidationService()
        self.ai_service = CurriculumAIService()
        self.import_export_service = CurriculumImportExportService()
        self.lesson_service = LessonService()
        self.theme_service = ThemeManagementService()
        self.unit_service = TeacherCurriculumUnitService()
        
        logger.info("CurriculumOrchestrationService initialized with 7 services")

    def get_curriculums_view(self, class_id: int) -> Dict[str, Any]:
        """
        カリキュラム一覧ビュー統合制御
        
        Args:
            class_id: クラスID
            
        Returns:
            Dict: ビューレンダリング用データ
        """
        try:
            logger.info(f"Getting curriculums view for class {class_id}")
            
            # データ取得
            result = self.data_service.get_curriculums_by_class(class_id)
            if not result['success']:
                return {
                    'success': False,
                    'message': result['message'],
                    'redirect': 'teacher_dashboard.dashboard'
                }
            
            # ビューデータ構築
            return {
                'success': True,
                'template': 'teacher/curriculum_list.html',
                'data': {
                    'class_obj': result['class'],
                    'curriculums': result['curriculums']
                }
            }
            
        except Exception as e:
            logger.error(f"Error in get_curriculums_view: {str(e)}")
            return {
                'success': False,
                'message': 'カリキュラム一覧の取得に失敗しました',
                'redirect': 'teacher_dashboard.dashboard'
            }

    def create_curriculum_view(self, class_id: int) -> Dict[str, Any]:
        """
        カリキュラム作成フォームビュー統合制御
        
        Args:
            class_id: クラスID
            
        Returns:
            Dict: ビューレンダリング用データ
        """
        try:
            logger.info(f"Creating curriculum form view for class {class_id}")
            
            # 権限チェック
            permission_check = self.validation_service.validate_teacher_permission(class_id)
            if not permission_check['valid']:
                return {
                    'success': False,
                    'message': permission_check['message'],
                    'redirect': 'teacher_dashboard.dashboard'
                }
            
            # フォームデータ準備
            form_data = self.data_service.prepare_curriculum_form_data(class_id)
            
            return {
                'success': True,
                'template': 'teacher/curriculum_create.html',
                'data': form_data
            }
            
        except Exception as e:
            logger.error(f"Error in create_curriculum_view: {str(e)}")
            return {
                'success': False,
                'message': 'カリキュラム作成フォームの準備に失敗しました',
                'redirect': 'teacher_dashboard.dashboard'
            }

    def generate_curriculum_view(self, class_id: int) -> Dict[str, Any]:
        """
        AI カリキュラム生成ビュー統合制御
        
        Args:
            class_id: クラスID
            
        Returns:
            Dict: ビューレンダリング用データ
        """
        try:
            logger.info(f"Generating AI curriculum view for class {class_id}")
            
            # 権限チェック
            permission_check = self.validation_service.validate_teacher_permission(class_id)
            if not permission_check['valid']:
                return {
                    'success': False,
                    'message': permission_check['message'],
                    'redirect': 'teacher_dashboard.dashboard'
                }
            
            # AI生成フォームデータ準備
            ai_form_data = self.ai_service.prepare_generation_form(class_id)
            
            return {
                'success': True,
                'template': 'teacher/curriculum_ai_generate.html',
                'data': ai_form_data
            }
            
        except Exception as e:
            logger.error(f"Error in generate_curriculum_view: {str(e)}")
            return {
                'success': False,
                'message': 'AI生成フォームの準備に失敗しました',
                'redirect': 'teacher_dashboard.dashboard'
            }

    def curriculum_detail_view(self, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラム詳細ビュー統合制御
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: ビューレンダリング用データ
        """
        try:
            logger.info(f"Getting curriculum detail view for {curriculum_id}")
            
            # 詳細データ取得
            detail_result = self.data_service.get_curriculum_detail(curriculum_id)
            if not detail_result['success']:
                return {
                    'success': False,
                    'message': detail_result['message'],
                    'redirect': 'teacher_dashboard.dashboard'
                }
            
            # 関連データ統合
            curriculum = detail_result['curriculum']
            lessons = self.lesson_service.get_lessons_by_curriculum(curriculum_id)
            themes = self.theme_service.get_themes_by_curriculum(curriculum_id)
            
            return {
                'success': True,
                'template': 'teacher/curriculum_detail.html',
                'data': {
                    'curriculum': curriculum,
                    'lessons': lessons,
                    'themes': themes
                }
            }
            
        except Exception as e:
            logger.error(f"Error in curriculum_detail_view: {str(e)}")
            return {
                'success': False,
                'message': 'カリキュラム詳細の取得に失敗しました',
                'redirect': 'teacher_dashboard.dashboard'
            }

    def edit_curriculum_view(self, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラム編集ビュー統合制御
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: ビューレンダリング用データ
        """
        try:
            logger.info(f"Getting curriculum edit view for {curriculum_id}")
            
            # 編集権限チェック
            permission_check = self.validation_service.validate_curriculum_edit_permission(curriculum_id)
            if not permission_check['valid']:
                return {
                    'success': False,
                    'message': permission_check['message'],
                    'redirect': 'teacher_dashboard.dashboard'
                }
            
            # 編集フォームデータ準備
            edit_result = self.data_service.prepare_curriculum_edit_data(curriculum_id)
            if not edit_result['success']:
                return {
                    'success': False,
                    'message': edit_result['message'],
                    'redirect': 'teacher_dashboard.dashboard'
                }
            
            return {
                'success': True,
                'template': 'teacher/curriculum_edit.html',  
                'data': {
                    'curriculum': edit_result['curriculum'],
                    'units': edit_result['units'],
                    'form_data': edit_result['form_data'],
                    'table_content_data': edit_result.get('table_content_data', [])
                }
            }
            
        except Exception as e:
            logger.error(f"Error in edit_curriculum_view: {str(e)}")
            return {
                'success': False,
                'message': 'カリキュラム編集フォームの準備に失敗しました',
                'redirect': 'teacher_dashboard.dashboard'
            }

    def process_curriculum_creation(self, class_id: int, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        カリキュラム作成処理統合制御
        
        Args:
            class_id: クラスID
            form_data: フォームデータ
            
        Returns:
            Dict: 処理結果
        """
        try:
            logger.info(f"Processing curriculum creation for class {class_id}")
            
            # バリデーション
            validation_result = self.validation_service.validate_curriculum_creation(class_id, form_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': validation_result['message'],
                    'redirect': f'teacher_curriculum_management.create_curriculum_form',
                    'redirect_args': {'class_id': class_id}
                }
            
            # カリキュラム作成
            creation_result = self.data_service.create_curriculum(class_id, form_data)
            if not creation_result['success']:
                return {
                    'success': False,
                    'message': creation_result['message'],
                    'redirect': f'teacher_curriculum_management.create_curriculum_form',
                    'redirect_args': {'class_id': class_id}
                }
            
            # 成功時の処理
            curriculum_id = creation_result['curriculum_id']
            
            # テーマとレッスンの初期設定
            if 'themes' in form_data:
                self.theme_service.create_initial_themes(curriculum_id, form_data['themes'])
            
            if 'lessons' in form_data:
                # 新システム対応: 複数レッスンの作成
                for lesson_data in form_data['lessons']:
                    lesson_data['curriculum_id'] = curriculum_id
                    self.lesson_service.create_lesson(curriculum_id, lesson_data)
            
            return {
                'success': True,
                'message': 'カリキュラムが正常に作成されました',
                'redirect': 'teacher_curriculum_management.curriculum_detail',
                'redirect_args': {'curriculum_id': curriculum_id}
            }
            
        except Exception as e:
            logger.error(f"Error in process_curriculum_creation: {str(e)}")
            return {
                'success': False,
                'message': 'カリキュラムの作成に失敗しました',
                'redirect': f'teacher_curriculum_management.create_curriculum_form',
                'redirect_args': {'class_id': class_id}
            }

    def process_curriculum_update(self, curriculum_id: int, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        カリキュラム更新処理統合制御
        
        Args:
            curriculum_id: カリキュラムID
            form_data: フォームデータ
            
        Returns:
            Dict: 処理結果
        """
        try:
            logger.info(f"[CURRICULUM] Processing curriculum update for {curriculum_id}")
            
            # バリデーション
            validation_result = self.validation_service.validate_curriculum_update(curriculum_id, form_data)
            if not validation_result['valid']:
                logger.warning(f"[CURRICULUM] Validation failed for curriculum {curriculum_id}: {validation_result['message']}")
                return {
                    'success': False,
                    'message': validation_result['message'],
                    'redirect': 'teacher_curriculum_management.edit_curriculum',
                    'redirect_args': {'curriculum_id': curriculum_id}
                }
            
            # テーブル編集データの前処理（Phase 3新機能）
            processed_form_data = dict(form_data)
            logger.info(f"[CURRICULUM] Original form_data keys: {list(form_data.keys())}")
            
            if 'table_content_data' in form_data:
                raw_data = form_data['table_content_data']
                logger.info(f"[CURRICULUM] Raw table_content_data type: {type(raw_data)}, length: {len(str(raw_data))}")
                try:
                    import json
                    if isinstance(raw_data, str):
                        table_data = json.loads(raw_data)
                    else:
                        table_data = raw_data  # 既にパース済みの場合
                    processed_form_data['table_content_data'] = table_data
                    logger.info(f"[CURRICULUM] Parsed table content: {len(table_data)} rows")
                    # 各行のデータをログ
                    for idx, row in enumerate(table_data):
                        logger.info(f"[CURRICULUM] Row {idx}: item='{row.get('item', '')}', time={row.get('time')}, basebuilder={row.get('basebuilder_id')}, rubric={row.get('rubric_aspect')}")
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"[CURRICULUM] Failed to parse table content data: {str(e)}")
                    logger.error(f"[CURRICULUM] Raw data was: {repr(raw_data)}")
                    processed_form_data['table_content_data'] = []
            else:
                logger.warning(f"[CURRICULUM] No table_content_data in form_data")
            
            # カリキュラム更新
            update_result = self.data_service.update_curriculum(curriculum_id, processed_form_data)
            if not update_result['success']:
                return {
                    'success': False,
                    'message': update_result['message'],
                    'redirect': 'teacher_curriculum_management.edit_curriculum',
                    'redirect_args': {'curriculum_id': curriculum_id}
                }
            
            # Phase1統合: レッスンテーブルへの直接更新（同期処理の置き換え）
            if 'table_content_data' in processed_form_data and processed_form_data['table_content_data']:
                logger.info(f"[CURRICULUM] Directly updating {len(processed_form_data['table_content_data'])} lessons to database")
                from app.api.curriculum_lesson_direct import batch_update_lessons_direct
                sync_result = batch_update_lessons_direct(curriculum_id, processed_form_data['table_content_data'])
                if sync_result['success']:
                    logger.info(f"[CURRICULUM] Successfully updated {sync_result['created_count']} lessons directly")
                else:
                    logger.warning(f"[CURRICULUM] Direct lesson update failed: {sync_result['message']}")
            
            return {
                'success': True,
                'message': 'カリキュラムが正常に更新されました',
                'redirect': 'teacher_curriculum_management.curriculum_detail',
                'redirect_args': {'curriculum_id': curriculum_id}
            }
            
        except Exception as e:
            logger.error(f"Error in process_curriculum_update: {str(e)}")
            return {
                'success': False,
                'message': 'カリキュラムの更新に失敗しました',
                'redirect': 'teacher_curriculum_management.edit_curriculum',
                'redirect_args': {'curriculum_id': curriculum_id}
            }

    def process_curriculum_deletion(self, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラム削除処理統合制御
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 処理結果
        """
        try:
            logger.info(f"Processing curriculum deletion for {curriculum_id}")
            
            # 削除権限チェック
            permission_check = self.validation_service.validate_curriculum_delete_permission(curriculum_id)
            if not permission_check['valid']:
                return {
                    'success': False,
                    'message': permission_check['message'],
                    'redirect': 'teacher_dashboard.dashboard'
                }
            
            # 関連データ削除（レッスン、テーマ）
            # 新システム対応: カリキュラムのレッスンを個別削除
            lessons = self.lesson_service.get_lessons_by_curriculum(curriculum_id)
            for lesson in lessons:
                self.lesson_service.delete_lesson(lesson.id)
            self.theme_service.delete_themes_by_curriculum(curriculum_id)
            
            # カリキュラム削除
            deletion_result = self.data_service.delete_curriculum(curriculum_id)
            if not deletion_result['success']:
                return {
                    'success': False,
                    'message': deletion_result['message'],
                    'redirect': 'teacher_dashboard.dashboard'
                }
            
            class_id = deletion_result.get('class_id')
            return {
                'success': True,
                'message': 'カリキュラムが正常に削除されました',
                'redirect': 'teacher_curriculum_management.view_curriculums',
                'redirect_args': {'class_id': class_id} if class_id else {}
            }
            
        except Exception as e:
            logger.error(f"Error in process_curriculum_deletion: {str(e)}")
            return {
                'success': False,
                'message': 'カリキュラムの削除に失敗しました',
                'redirect': 'teacher_dashboard.dashboard'
            }

    def rubric_edit_view(self, curriculum_id: int) -> Dict[str, Any]:
        """
        ルーブリック編集ビュー統合制御（アーキテクチャ統一）
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: ビューレンダリング用データ
        """
        try:
            logger.info(f"Getting rubric edit view for {curriculum_id}")
            
            # 既存のデータ取得ロジックを再利用（重複排除）
            detail_result = self.data_service.get_curriculum_detail(curriculum_id)
            if not detail_result['success']:
                return {
                    'success': False,
                    'message': detail_result['message'],
                    'redirect': 'teacher_dashboard.dashboard'
                }
            
            # Orchestration形式で統一
            return {
                'success': True,
                'template': 'teacher/curriculum_rubric_edit.html',
                'data': {
                    'curriculum': detail_result['curriculum'],
                    'rubric_info': detail_result.get('rubric_info', {})
                }
            }
            
        except Exception as e:
            logger.error(f"Error in rubric_edit_view: {str(e)}")
            return {
                'success': False,
                'message': 'ルーブリック編集画面の表示に失敗しました',
                'redirect': 'teacher_dashboard.dashboard'
            }