# -*- coding: utf-8 -*-
"""
Curriculum Migration Adapter
============================
カリキュラムデータの二重管理問題を解決するための移行アダプター

Purpose:
    curriculum_data (JSON) → curriculum_lessons (テーブル) への段階的移行
    収束的改善により、2つのデータソースを1つに統一

設計原則:
    1. 後方互換性の維持
    2. 段階的な移行
    3. 最小限の新規作成（このファイルのみ）
    4. ロールバック可能性の確保
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from flask import current_app
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app.models import db, Curriculum
from app.modules.lesson_system.models.lesson_models import (
    CurriculumLesson, LessonTask, LessonType
)

logger = logging.getLogger(__name__)


class CurriculumMigrationAdapter:
    """
    カリキュラムデータ移行アダプター
    
    curriculum_data (JSON) と curriculum_lessons (テーブル) の
    統一インターフェースを提供し、段階的な移行を実現
    """
    
    # Phase制御フラグ（config.pyで管理）
    @classmethod
    def _get_dual_write_enabled(cls):
        """設定ファイルから二重書き込みの有効性を取得"""
        from flask import current_app
        return current_app.config.get('ENABLE_CURRICULUM_DATA_SYNC', False)
    
    @classmethod
    def _get_prefer_table_read(cls):
        """設定ファイルからテーブル優先読み込みの設定を取得"""
        from flask import current_app
        return current_app.config.get('PREFER_CURRICULUM_LESSONS', True)
    
    @classmethod
    def read_curriculum_content(cls, curriculum_id: int) -> Dict[str, Any]:
        """
        統一読み取りインターフェース
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: カリキュラムコンテンツ（統一フォーマット）
        """
        try:
            if cls._get_prefer_table_read():
                # Phase 4以降: curriculum_lessonsを優先
                content = cls._read_from_lessons_table(curriculum_id)
                if content and content.get('lessons'):
                    logger.debug(f"Read {len(content['lessons'])} lessons from table for curriculum {curriculum_id}")
                    return content
            
            # フォールバック: curriculum_dataから読み込み
            content = cls._read_from_data_column(curriculum_id)
            if content:
                logger.debug(f"Read content from JSON column for curriculum {curriculum_id}")
                return content
            
            # 両方空の場合
            return {'lessons': [], 'table_content': []}
            
        except Exception as e:
            logger.error(f"Error reading curriculum content: {str(e)}")
            return {'lessons': [], 'table_content': []}
    
    @classmethod
    def write_curriculum_content(cls, curriculum_id: int, content: Dict[str, Any]) -> bool:
        """
        統一書き込みインターフェース
        
        Args:
            curriculum_id: カリキュラムID
            content: 書き込むコンテンツ
            
        Returns:
            bool: 成功/失敗
        """
        try:
            success = True
            
            # Phase 7以降: 設定に応じた二重書き込み
            if cls._get_dual_write_enabled():
                # curriculum_dataカラムに書き込み（後方互換性維持）
                if not cls._write_to_data_column(curriculum_id, content):
                    success = False
                    logger.warning(f"Failed to write to data column for curriculum {curriculum_id}")
            else:
                logger.info(f"Dual write disabled by config - skipping curriculum_data column for curriculum {curriculum_id}")
            
            # curriculum_lessonsテーブルに書き込み（メイン）
            if not cls._write_to_lessons_table(curriculum_id, content):
                success = False
                logger.error(f"Failed to write to lessons table for curriculum {curriculum_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error writing curriculum content: {str(e)}")
            return False
    
    @classmethod
    def _read_from_lessons_table(cls, curriculum_id: int) -> Dict[str, Any]:
        """
        curriculum_lessonsテーブルから読み込み
        """
        try:
            lessons = CurriculumLesson.query.filter_by(
                curriculum_id=curriculum_id
            ).order_by(CurriculumLesson.lesson_number).all()
            
            if not lessons:
                return {}
            
            # テーブルデータを統一フォーマットに変換
            table_content = []
            for lesson in lessons:
                lesson_data = {
                    'lesson_number': lesson.lesson_number,
                    'title': lesson.title,
                    'description': lesson.description,
                    'lesson_type': lesson.lesson_type.value if lesson.lesson_type else 'lecture',
                    'duration_minutes': lesson.duration_minutes,
                    'learning_objectives': lesson.learning_objectives or [],
                    'key_points': lesson.key_points or [],
                    'evaluation_criteria': lesson.evaluation_criteria or {},
                    'resources': lesson.resources or [],
                    'teacher_notes': lesson.teacher_notes
                }
                
                # タスク情報も含める
                tasks = []
                for task in lesson.tasks:
                    tasks.append({
                        'task_number': task.task_number,
                        'title': task.title,
                        'description': task.description,
                        'instructions': task.instructions,
                        'expected_time_minutes': task.estimated_minutes,
                        'is_required': task.is_required
                    })
                lesson_data['tasks'] = tasks
                
                table_content.append(lesson_data)
            
            return {
                'lessons': [lesson.to_dict() for lesson in lessons],
                'table_content': table_content
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error reading lessons: {str(e)}")
            return {}
    
    @classmethod
    def _read_from_data_column(cls, curriculum_id: int) -> Dict[str, Any]:
        """
        curriculum_dataカラムから読み込み
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum or not curriculum.curriculum_data:
                return {}
            
            data = json.loads(curriculum.curriculum_data)
            
            # 統一フォーマットに変換
            table_content = data.get('table_content', [])
            
            # レガシーフォーマット対応
            if not table_content and 'units' in data:
                # 旧形式のデータ構造を変換
                table_content = cls._convert_legacy_format(data)
            
            return {
                'table_content': table_content,
                'lessons': []  # JSONからlessons形式への変換は必要に応じて実装
            }
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Error parsing curriculum_data JSON: {str(e)}")
            return {}
    
    @classmethod
    def _write_to_lessons_table(cls, curriculum_id: int, content: Dict[str, Any]) -> bool:
        """
        curriculum_lessonsテーブルに書き込み
        """
        try:
            # トランザクション開始
            # 既存レッスンを削除
            CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).delete()
            
            # table_contentまたはlessonsから新規作成
            lessons_data = content.get('table_content', content.get('lessons', []))
            
            for idx, lesson_data in enumerate(lessons_data):
                lesson = CurriculumLesson(
                    curriculum_id=curriculum_id,
                    lesson_number=lesson_data.get('lesson_number', idx + 1),
                    title=lesson_data.get('title', f'レッスン{idx + 1}'),
                    description=lesson_data.get('description', ''),
                    lesson_type=cls._get_lesson_type(lesson_data.get('lesson_type', 'lecture')),
                    duration_minutes=lesson_data.get('duration_minutes', 50),
                    learning_objectives=lesson_data.get('learning_objectives', []),
                    key_points=lesson_data.get('key_points', []),
                    evaluation_criteria=lesson_data.get('evaluation_criteria', {}),
                    resources=lesson_data.get('resources', []),
                    teacher_notes=lesson_data.get('teacher_notes', ''),
                    created_by=current_user.id if current_user and current_user.is_authenticated else 1
                )
                db.session.add(lesson)
                db.session.flush()  # IDを取得
                
                # タスクも作成
                tasks_data = lesson_data.get('tasks', [])
                for task_idx, task_data in enumerate(tasks_data):
                    task = LessonTask(
                        lesson_id=lesson.id,
                        task_number=task_data.get('task_number', task_idx + 1),
                        title=task_data.get('title', f'タスク{task_idx + 1}'),
                        description=task_data.get('description', ''),
                        instructions=task_data.get('instructions', ''),
                        estimated_minutes=task_data.get('expected_time_minutes', 10),
                        is_required=task_data.get('is_required', True)
                    )
                    db.session.add(task)
            
            db.session.commit()
            logger.info(f"Successfully wrote {len(lessons_data)} lessons to table for curriculum {curriculum_id}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error writing lessons: {str(e)}")
            return False
    
    @classmethod
    def _write_to_data_column(cls, curriculum_id: int, content: Dict[str, Any]) -> bool:
        """
        curriculum_dataカラムに書き込み（後方互換性のため）
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                logger.error(f"Curriculum {curriculum_id} not found")
                return False
            
            # 既存データを保持しながら更新
            existing_data = {}
            if curriculum.curriculum_data:
                try:
                    existing_data = json.loads(curriculum.curriculum_data)
                except json.JSONDecodeError:
                    existing_data = {}
            
            # table_contentを更新
            if 'table_content' in content:
                existing_data['table_content'] = content['table_content']
            elif 'lessons' in content:
                # lessons形式をtable_content形式に変換
                existing_data['table_content'] = content['lessons']
            
            curriculum.curriculum_data = json.dumps(existing_data, ensure_ascii=False)
            db.session.commit()
            
            logger.info(f"Successfully wrote to data column for curriculum {curriculum_id}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error writing to data column: {str(e)}")
            return False
    
    @classmethod
    def _get_lesson_type(cls, type_str: str) -> LessonType:
        """
        文字列をLessonType Enumに変換
        """
        type_map = {
            'lecture': LessonType.LECTURE,
            'practice': LessonType.PRACTICE,
            'discussion': LessonType.DISCUSSION,
            'presentation': LessonType.PRESENTATION,
            'experiment': LessonType.EXPERIMENT,
            'review': LessonType.REVIEW
        }
        return type_map.get(type_str.lower(), LessonType.LECTURE)
    
    @classmethod
    def _convert_legacy_format(cls, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        レガシーフォーマットを新フォーマットに変換
        """
        # 実装は実際のレガシーフォーマットに応じて調整
        return []
    
    @classmethod
    def verify_data_consistency(cls, curriculum_id: int) -> Dict[str, Any]:
        """
        データ整合性を検証（デバッグ用）
        
        Returns:
            Dict: 検証結果
        """
        try:
            json_content = cls._read_from_data_column(curriculum_id)
            table_content = cls._read_from_lessons_table(curriculum_id)
            
            json_count = len(json_content.get('table_content', []))
            table_count = len(table_content.get('lessons', []))
            
            return {
                'consistent': json_count == table_count,
                'json_lessons': json_count,
                'table_lessons': table_count,
                'message': 'Data is consistent' if json_count == table_count else f'Mismatch: JSON has {json_count}, Table has {table_count}'
            }
            
        except Exception as e:
            return {
                'consistent': False,
                'error': str(e)
            }