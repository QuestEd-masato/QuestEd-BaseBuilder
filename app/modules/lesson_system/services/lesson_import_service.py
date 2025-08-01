"""
レッスンシステム CSVインポートサービス

CSVファイルからレッスンとタスクを一括インポートする機能
"""

import csv
import io
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.models import db
from ..models.lesson_models import CurriculumLesson, LessonTask, LessonType, TaskCheckStatus
from app.models import Curriculum


class LessonImportService:
    """レッスンCSVインポートサービス"""

    @staticmethod
    def import_lessons_from_csv(file_data, curriculum_id: int, teacher_id: int) -> Dict[str, Any]:
        """
        CSVファイルからレッスンを一括インポート
        
        CSV形式:
        レッスン番号,タイトル,説明,タイプ,所要時間,学習目標,重要ポイント,タスク番号,タスクタイトル,タスク説明,タスク所要時間,必須フラグ
        
        Args:
            file_data: CSVファイルデータ
            curriculum_id: カリキュラムID
            teacher_id: 教師ID
            
        Returns:
            Dict: インポート結果
        """
        try:
            # カリキュラムの存在確認
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {
                    "success": False,
                    "message": "指定されたカリキュラムが見つかりません。"
                }

            # CSVデータの読み込み
            csv_content = file_data.read().decode('utf-8-sig')  # BOM対応
            csv_reader = csv.reader(io.StringIO(csv_content))
            
            lessons_data = {}
            imported_lessons = 0
            imported_tasks = 0
            errors = []
            
            # ヘッダー行をスキップ
            header = next(csv_reader, None)
            if not header:
                return {
                    "success": False,
                    "message": "CSVファイルが空です。"
                }
            
            current_app.logger.info(f"CSV Header: {header}")
            
            for row_num, row in enumerate(csv_reader, start=2):
                try:
                    if len(row) < 8:  # 最小必要列数
                        continue
                    
                    # レッスンデータの取得
                    lesson_number = int(row[0]) if row[0].strip() else None
                    lesson_title = row[1].strip() if len(row) > 1 else ""
                    lesson_description = row[2].strip() if len(row) > 2 else ""
                    lesson_type_str = row[3].strip() if len(row) > 3 else "lecture"
                    duration_minutes = int(row[4]) if len(row) > 4 and row[4].strip() else 50
                    learning_objectives = row[5].strip().split(';') if len(row) > 5 and row[5].strip() else []
                    key_points = row[6].strip().split(';') if len(row) > 6 and row[6].strip() else []
                    
                    # タスクデータの取得
                    task_number = int(row[7]) if len(row) > 7 and row[7].strip() else None
                    task_title = row[8].strip() if len(row) > 8 else ""
                    task_description = row[9].strip() if len(row) > 9 else ""
                    task_time = int(row[10]) if len(row) > 10 and row[10].strip() else 10
                    is_required = row[11].strip().lower() in ['true', '1', 'yes', '必須'] if len(row) > 11 else True
                    
                    if not lesson_number or not lesson_title:
                        continue
                    
                    # レッスンタイプの変換
                    lesson_type = LessonImportService._get_lesson_type(lesson_type_str)
                    
                    # レッスンが既に処理済みかチェック
                    if lesson_number not in lessons_data:
                        # 新しいレッスンを作成
                        lesson_data = {
                            'lesson_number': lesson_number,
                            'title': lesson_title,
                            'description': lesson_description,
                            'lesson_type': lesson_type,
                            'duration_minutes': duration_minutes,
                            'learning_objectives': learning_objectives,
                            'key_points': key_points,
                            'tasks': []
                        }
                        lessons_data[lesson_number] = lesson_data
                    
                    # タスクを追加
                    if task_number and task_title:
                        task_data = {
                            'task_number': task_number,
                            'title': task_title,
                            'description': task_description,
                            'expected_time_minutes': task_time,
                            'is_required': is_required
                        }
                        lessons_data[lesson_number]['tasks'].append(task_data)
                        
                except (ValueError, IndexError) as e:
                    error_msg = f"行 {row_num}: データ形式エラー - {str(e)}"
                    errors.append(error_msg)
                    current_app.logger.warning(error_msg)
                    continue
            
            if not lessons_data:
                return {
                    "success": False,
                    "message": "有効なレッスンデータが見つかりませんでした。"
                }
            
            # データベースに保存
            try:
                for lesson_num, lesson_data in lessons_data.items():
                    # 重複チェック
                    existing_lesson = CurriculumLesson.query.filter_by(
                        curriculum_id=curriculum_id,
                        lesson_number=lesson_num
                    ).first()
                    
                    if existing_lesson:
                        error_msg = f"レッスン {lesson_num} は既に存在します。スキップされました。"
                        errors.append(error_msg)
                        continue
                    
                    # レッスンを作成
                    lesson = CurriculumLesson(
                        curriculum_id=curriculum_id,
                        lesson_number=lesson_data['lesson_number'],
                        title=lesson_data['title'],
                        description=lesson_data['description'],
                        lesson_type=lesson_data['lesson_type'],
                        duration_minutes=lesson_data['duration_minutes'],
                        learning_objectives=lesson_data['learning_objectives'],
                        key_points=lesson_data['key_points'],
                        created_by=teacher_id
                    )
                    
                    db.session.add(lesson)
                    db.session.flush()  # IDを取得するためflush
                    
                    imported_lessons += 1
                    
                    # タスクを作成
                    for task_data in lesson_data['tasks']:
                        task = LessonTask(
                            lesson_id=lesson.id,
                            task_number=task_data['task_number'],
                            title=task_data['title'],
                            description=task_data['description'],
                            expected_time_minutes=task_data['expected_time_minutes'],
                            is_required=task_data['is_required']
                        )
                        db.session.add(task)
                        imported_tasks += 1
                
                db.session.commit()
                
                current_app.logger.info(f"Successfully imported {imported_lessons} lessons and {imported_tasks} tasks")
                
                result_message = f"{imported_lessons}個のレッスンと{imported_tasks}個のタスクをインポートしました。"
                if errors:
                    result_message += f" {len(errors)}件のエラーがありました。"
                
                return {
                    "success": True,
                    "message": result_message,
                    "imported_lessons": imported_lessons,
                    "imported_tasks": imported_tasks,
                    "errors": errors
                }
                
            except SQLAlchemyError as e:
                db.session.rollback()
                error_msg = f"データベースエラー: {str(e)}"
                current_app.logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg
                }
                
        except Exception as e:
            current_app.logger.error(f"CSV import error: {str(e)}")
            return {
                "success": False,
                "message": f"CSVインポート中にエラーが発生しました: {str(e)}"
            }
    
    @staticmethod 
    def _get_lesson_type(type_str: str) -> LessonType:
        """文字列からLessonTypeを取得"""
        type_mapping = {
            'lecture': LessonType.LECTURE,
            '講義': LessonType.LECTURE,
            'practice': LessonType.PRACTICE,
            '演習': LessonType.PRACTICE,
            'discussion': LessonType.DISCUSSION,
            '討論': LessonType.DISCUSSION,
            'presentation': LessonType.PRESENTATION,
            '発表': LessonType.PRESENTATION,
            'experiment': LessonType.EXPERIMENT,
            '実験': LessonType.EXPERIMENT,
            'review': LessonType.REVIEW,
            '復習': LessonType.REVIEW
        }
        
        return type_mapping.get(type_str.lower(), LessonType.LECTURE)
    
    @staticmethod
    def generate_csv_template() -> str:
        """
        CSVテンプレートを生成
        
        Returns:
            str: CSV形式のテンプレート
        """
        template_data = [
            ['レッスン番号', 'タイトル', '説明', 'タイプ', '所要時間(分)', '学習目標(;区切り)', '重要ポイント(;区切り)', 'タスク番号', 'タスクタイトル', 'タスク説明', 'タスク所要時間(分)', '必須フラグ(true/false)'],
            [1, '導入レッスン', '基礎概念の理解', '講義', 50, '基本概念を理解する;重要なポイントを把握する', '定義;歴史;応用例', 1, '概念確認', '基本概念の理解を確認する', 10, 'true'],
            [1, '', '', '', '', '', '', 2, '練習問題', '基礎問題を解く', 15, 'true'],
            [1, '', '', '', '', '', '', 3, '振り返り', '学習内容を振り返る', 5, 'false'],
            [2, '応用レッスン', '応用問題に挑戦', '演習', 50, '応用力を身につける;問題解決能力を向上させる', '応用のコツ;よくある間違い', 1, '応用問題1', '基本から応用へのステップ', 20, 'true'],
            [2, '', '', '', '', '', '', 2, '応用問題2', '難易度の高い問題に挑戦', 25, 'true'],
        ]
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(template_data)
        
        return output.getvalue()