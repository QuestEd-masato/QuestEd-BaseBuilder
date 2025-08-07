# -*- coding: utf-8 -*-
"""
Direct Curriculum Lesson API
カリキュラム・レッスン直接編集API

Purpose: curriculum_data (JSON) ↔ curriculum_lessons (テーブル) 同期処理の置き換え
         curriculum_lessonsテーブルへの直接操作によるデータ整合性保証
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app.models import db, Curriculum
from app.modules.lesson_system.models.lesson_models import CurriculumLesson, LessonTask, LessonType
from app.teacher.common import teacher_required

logger = logging.getLogger(__name__)

# Blueprint作成
curriculum_lesson_api = Blueprint("curriculum_lesson_api", __name__)


def create_default_tasks_for_lesson(lesson_id: int):
    """新規レッスンにデフォルトタスクを作成"""
    try:
        default_tasks = [
            {
                "title": "理解確認",
                "description": "本日の学習内容を理解できているか確認しましょう",
                "instructions": "重要なポイントを振り返り、分からない部分があれば質問してください",
                "estimated_minutes": 5
            },
            {
                "title": "実践練習",
                "description": "学んだことを実際にやってみましょう",
                "instructions": "習得した知識やスキルを使って、実際に問題を解いてみてください",
                "estimated_minutes": 15
            }
        ]
        
        for i, task_data in enumerate(default_tasks, 1):
            task = LessonTask(
                lesson_id=lesson_id,
                task_number=i,
                title=task_data["title"],
                description=task_data["description"],
                instructions=task_data["instructions"],
                estimated_minutes=task_data["estimated_minutes"],
                is_required=True
            )
            db.session.add(task)
            
        logger.info(f"[DIRECT_API] Created {len(default_tasks)} default tasks for lesson {lesson_id}")
        
    except Exception as e:
        logger.error(f"[DIRECT_API] Failed to create default tasks for lesson {lesson_id}: {e}")
        # エラーが発生してもレッスン作成は継続


@curriculum_lesson_api.route('/curriculum/<int:curriculum_id>/lessons/batch-update', methods=['POST'])
@login_required
@teacher_required
def batch_update_lessons(curriculum_id):
    """
    レッスン一括更新API（同期処理の置き換え）
    
    Args:
        curriculum_id: カリキュラムID
        
    Request Body:
        {
            "lessons": [
                {
                    "title": "レッスンタイトル",
                    "description": "レッスン説明", 
                    "duration_minutes": 50,
                    "learning_objectives": ["目標1", "目標2"],
                    "basebuilder_references": "textset_123",
                    "evaluation_criteria": {"aspect": "knowledge"}
                }
            ]
        }
        
    Returns:
        JSON: 処理結果
    """
    try:
        # カリキュラムの存在確認
        curriculum = Curriculum.query.get(curriculum_id)
        if not curriculum:
            return jsonify({
                'success': False,
                'message': 'カリキュラムが見つかりません'
            }), 404
        
        # 権限確認（教師 かつ 担当クラス）
        if not (current_user.role == 'teacher' and 
                (curriculum.teacher_id == current_user.id or curriculum.created_by == current_user.id)):
            return jsonify({
                'success': False,
                'message': '編集権限がありません'
            }), 403
        
        # リクエストデータの取得
        data = request.get_json()
        if not data or 'lessons' not in data:
            return jsonify({
                'success': False,
                'message': 'レッスンデータが提供されていません'
            }), 400
        
        lessons_data = data['lessons']
        logger.info(f"[DIRECT_API] Processing {len(lessons_data)} lessons for curriculum {curriculum_id}")
        
        # トランザクション開始
        with db.session.begin():
            # 既存レッスンの進捗データを保護
            existing_lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).all()
            progress_backup = {}
            
            for lesson in existing_lessons:
                # 学生の進捗データをバックアップ
                progress_records = lesson.student_progress.all()
                if progress_records:
                    progress_backup[lesson.lesson_number] = {
                        'progress_records': [p.to_dict() for p in progress_records],
                        'lesson_id': lesson.id
                    }
            
            # 既存レッスンを削除
            CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).delete()
            logger.info(f"[DIRECT_API] Deleted {len(existing_lessons)} existing lessons")
            
            # 新しいレッスンを作成
            created_lessons = []
            for index, lesson_data in enumerate(lessons_data, 1):
                lesson = CurriculumLesson(
                    curriculum_id=curriculum_id,
                    lesson_number=index,
                    title=lesson_data.get('title', f'レッスン{index}'),
                    description=lesson_data.get('description', ''),
                    lesson_type=LessonType.LECTURE,  # デフォルト値
                    duration_minutes=int(lesson_data.get('duration_minutes', 50)),
                    created_by=current_user.id
                )
                
                # 学習目標の設定
                objectives = lesson_data.get('learning_objectives', [])
                if isinstance(objectives, str):
                    # 文字列の場合は配列に変換
                    lesson.learning_objectives = [objectives] if objectives.strip() else []
                elif isinstance(objectives, list):
                    lesson.learning_objectives = objectives
                else:
                    lesson.learning_objectives = []
                
                # BaseBuilder連携の設定（実際のDBスキーマにフィールドが存在しないためコメントアウト）
                # basebuilder_ref = lesson_data.get('basebuilder_references')
                # if basebuilder_ref:
                #     lesson.basebuilder_references = basebuilder_ref
                
                # 評価基準の設定
                eval_criteria = lesson_data.get('evaluation_criteria', {})
                if isinstance(eval_criteria, dict):
                    lesson.evaluation_criteria = eval_criteria
                
                db.session.add(lesson)
                created_lessons.append(lesson)
                logger.info(f"[DIRECT_API] Created lesson {index}: {lesson.title}")
            
            # セッションをフラッシュして新しいIDを取得
            db.session.flush()
            
            # デフォルトタスクを作成
            for lesson in created_lessons:
                create_default_tasks_for_lesson(lesson.id)
            
            # 進捗データの復元（レッスン番号ベース）
            restored_count = 0
            for lesson in created_lessons:
                if lesson.lesson_number in progress_backup:
                    backup_data = progress_backup[lesson.lesson_number]
                    logger.info(f"[DIRECT_API] Restoring progress for lesson {lesson.lesson_number}")
                    
                    # 進捗レコードの復元
                    from app.modules.lesson_system.models.lesson_models import StudentLessonProgress
                    for progress_dict in backup_data['progress_records']:
                        new_progress = StudentLessonProgress(
                            student_id=progress_dict['student_id'],
                            lesson_id=lesson.id,  # 新しいレッスンID
                            started_at=datetime.fromisoformat(progress_dict['started_at']) if progress_dict.get('started_at') else None,
                            completed_at=datetime.fromisoformat(progress_dict['completed_at']) if progress_dict.get('completed_at') else None,
                            # 実際のDBスキーマに存在しないフィールドはコメントアウト
                            # time_spent_minutes=progress_dict.get('time_spent_minutes', 0),
                            # understanding_level=progress_dict.get('understanding_level'),
                            # difficulty_level=progress_dict.get('difficulty_level'),
                            # reflection=progress_dict.get('reflection'),
                            # is_completed=progress_dict.get('is_completed', False),
                            # completion_percentage=progress_dict.get('completion_percentage', 0),
                            approval_status=progress_dict.get('approval_status', 'none'),
                            completion_request_date=datetime.fromisoformat(progress_dict['completion_request_date']) if progress_dict.get('completion_request_date') else None,
                            teacher_comments=progress_dict.get('teacher_comments'),
                            approved_by=progress_dict.get('approved_by')
                        )
                        db.session.add(new_progress)
                        restored_count += 1
        
        # トランザクションコミット
        logger.info(f"[DIRECT_API] Successfully updated {len(created_lessons)} lessons, restored {restored_count} progress records")
        
        return jsonify({
            'success': True,
            'message': f'{len(created_lessons)}個のレッスンを更新しました',
            'created_count': len(created_lessons),
            'restored_progress_count': restored_count
        })
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"[DIRECT_API] Database error for curriculum {curriculum_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'データベースエラーが発生しました'
        }), 500
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"[DIRECT_API] Unexpected error for curriculum {curriculum_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'予期しないエラーが発生しました: {str(e)}'
        }), 500


@curriculum_lesson_api.route('/curriculum/<int:curriculum_id>/lessons/<int:lesson_id>', methods=['PUT'])
@login_required
@teacher_required 
def update_single_lesson(curriculum_id, lesson_id):
    """
    個別レッスン更新API
    
    Args:
        curriculum_id: カリキュラムID
        lesson_id: レッスンID
        
    Request Body:
        {
            "title": "新しいタイトル",
            "description": "新しい説明",
            "duration_minutes": 60,
            "learning_objectives": ["目標1", "目標2"],
            "basebuilder_references": "textset_456"
        }
        
    Returns:
        JSON: 処理結果
    """
    try:
        # レッスンの存在確認
        lesson = CurriculumLesson.query.filter_by(
            id=lesson_id, 
            curriculum_id=curriculum_id
        ).first()
        
        if not lesson:
            return jsonify({
                'success': False,
                'message': 'レッスンが見つかりません'
            }), 404
        
        # 権限確認
        curriculum = lesson.curriculum
        if not (current_user.role == 'teacher' and 
                (curriculum.teacher_id == current_user.id or curriculum.created_by == current_user.id)):
            return jsonify({
                'success': False,
                'message': '編集権限がありません'
            }), 403
        
        # リクエストデータの取得
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '更新データが提供されていません'
            }), 400
        
        # フィールドの更新
        if 'title' in data:
            lesson.title = data['title']
        if 'description' in data:
            lesson.description = data['description']
        if 'duration_minutes' in data:
            lesson.duration_minutes = int(data['duration_minutes'])
        if 'learning_objectives' in data:
            objectives = data['learning_objectives']
            if isinstance(objectives, str):
                lesson.learning_objectives = [objectives] if objectives.strip() else []
            elif isinstance(objectives, list):
                lesson.learning_objectives = objectives
        # BaseBuilder連携（実際のDBスキーマにフィールドが存在しないためコメントアウト）
        # if 'basebuilder_references' in data:
        #     lesson.basebuilder_references = data['basebuilder_references']
        if 'evaluation_criteria' in data:
            lesson.evaluation_criteria = data['evaluation_criteria']
        
        lesson.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"[DIRECT_API] Updated lesson {lesson_id} in curriculum {curriculum_id}")
        
        return jsonify({
            'success': True,
            'message': 'レッスンを更新しました',
            'lesson': lesson.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"[DIRECT_API] Error updating lesson {lesson_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'レッスンの更新に失敗しました: {str(e)}'
        }), 500


@curriculum_lesson_api.route('/curriculum/<int:curriculum_id>/lessons', methods=['GET'])
@login_required
def get_curriculum_lessons(curriculum_id):
    """
    カリキュラムのレッスン一覧取得API
    
    Args:
        curriculum_id: カリキュラムID
        
    Returns:
        JSON: レッスン一覧
    """
    try:
        # カリキュラムの存在確認
        curriculum = Curriculum.query.get(curriculum_id)
        if not curriculum:
            return jsonify({
                'success': False,
                'message': 'カリキュラムが見つかりません'
            }), 404
        
        # レッスン一覧を取得
        lessons = CurriculumLesson.query.filter_by(
            curriculum_id=curriculum_id
        ).order_by(CurriculumLesson.lesson_number).all()
        
        lessons_data = [lesson.to_dict() for lesson in lessons]
        
        return jsonify({
            'success': True,
            'lessons': lessons_data,
            'total_count': len(lessons_data)
        })
        
    except Exception as e:
        logger.error(f"[DIRECT_API] Error getting lessons for curriculum {curriculum_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'レッスン一覧の取得に失敗しました: {str(e)}'
        }), 500


# 同期処理の直接呼び出し関数（内部使用）
def batch_update_lessons_direct(curriculum_id: int, table_content_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    同期処理の置き換え関数（内部呼び出し用）
    
    Args:
        curriculum_id: カリキュラムID
        table_content_data: テーブル編集データ
        
    Returns:
        Dict: 処理結果
    """
    try:
        lessons_data = []
        for item in table_content_data:
            lesson_data = {
                'title': item.get('item', ''),
                'description': item.get('description', ''),
                'duration_minutes': item.get('time', 50),
                'learning_objectives': [item.get('detail', '')] if item.get('detail') else [],
                'basebuilder_references': item.get('basebuilder_id'),
                'evaluation_criteria': {'aspect': item.get('rubric_aspect')} if item.get('rubric_aspect') else {}
            }
            lessons_data.append(lesson_data)
        
        # batch_update_lessons の内部ロジックを直接実行
        # （認証チェックは呼び出し元で実施済み）
        
        # 既存レッスンの進捗データを保護
        existing_lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).all()
        progress_backup = {}
        
        for lesson in existing_lessons:
            progress_records = lesson.student_progress.all()
            if progress_records:
                progress_backup[lesson.lesson_number] = {
                    'progress_records': [p.to_dict() for p in progress_records],
                    'lesson_id': lesson.id
                }
        
        # 既存レッスンを削除
        CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).delete()
        
        # 新しいレッスンを作成
        created_lessons = []
        for index, lesson_data in enumerate(lessons_data, 1):
            lesson = CurriculumLesson(
                curriculum_id=curriculum_id,
                lesson_number=index,
                title=lesson_data.get('title', f'レッスン{index}'),
                description=lesson_data.get('description', ''),
                lesson_type=LessonType.LECTURE,
                duration_minutes=int(lesson_data.get('duration_minutes', 50)),
                learning_objectives=lesson_data.get('learning_objectives', []),
                # basebuilder_references=lesson_data.get('basebuilder_references'),  # DBスキーマに存在しないためコメントアウト
                evaluation_criteria=lesson_data.get('evaluation_criteria', {}),
                created_by=current_user.id if current_user and current_user.is_authenticated else None
            )
            
            db.session.add(lesson)
            created_lessons.append(lesson)
        
        # セッションをフラッシュして新しいIDを取得
        db.session.flush()
        
        # 進捗データの復元
        restored_count = 0
        for lesson in created_lessons:
            if lesson.lesson_number in progress_backup:
                backup_data = progress_backup[lesson.lesson_number]
                
                from app.modules.lesson_system.models.lesson_models import StudentLessonProgress
                for progress_dict in backup_data['progress_records']:
                    new_progress = StudentLessonProgress(
                        student_id=progress_dict['student_id'],
                        lesson_id=lesson.id,
                        started_at=datetime.fromisoformat(progress_dict['started_at']) if progress_dict.get('started_at') else None,
                        completed_at=datetime.fromisoformat(progress_dict['completed_at']) if progress_dict.get('completed_at') else None,
                        # 実際のDBスキーマに存在しないフィールドはコメントアウト
                        # time_spent_minutes=progress_dict.get('time_spent_minutes', 0),
                        # understanding_level=progress_dict.get('understanding_level'),
                        # difficulty_level=progress_dict.get('difficulty_level'),
                        # reflection=progress_dict.get('reflection'),
                        # is_completed=progress_dict.get('is_completed', False),
                        # completion_percentage=progress_dict.get('completion_percentage', 0),
                        approval_status=progress_dict.get('approval_status', 'none'),
                        completion_request_date=datetime.fromisoformat(progress_dict['completion_request_date']) if progress_dict.get('completion_request_date') else None,
                        teacher_comments=progress_dict.get('teacher_comments'),
                        approved_by=progress_dict.get('approved_by')
                    )
                    db.session.add(new_progress)
                    restored_count += 1
        
        db.session.commit()
        
        return {
            'success': True,
            'message': f'{len(created_lessons)}個のレッスンを更新しました',
            'created_count': len(created_lessons),
            'restored_progress_count': restored_count
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"[DIRECT_API] Error in batch_update_lessons_direct: {e}")
        return {
            'success': False,
            'message': f'レッスン更新に失敗しました: {str(e)}'
        }