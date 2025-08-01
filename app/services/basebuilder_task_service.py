# app/services/basebuilder_task_service.py
"""
BaseBuilder Task Integration Service
====================================
BaseBuilderテキスト・問題と学生タスクの連携、達成率による自動完了処理
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.models import db
# Lesson system removed - legacy imports disabled
# from app.modules.lesson_system.models.lesson_models import LessonTask, StudentTaskCheck, TaskCheckStatus
from basebuilder.models import (
    TextSet, BasicKnowledgeItem, AnswerRecord, 
    WordProficiency, TextProficiencyRecord
)


class BaseBuilderTaskService:
    """BaseBuilderとタスクシステムの統合サービス"""
    
    @staticmethod
    def get_task_basebuilder_info(task) -> Optional[Dict]:
        """タスクのBaseBuilder情報を取得"""
        if not task.description:
            return None
            
        # タスク説明からBaseBuilder情報を抽出
        description = task.description
        
        # BaseBuilderテキストが設定されているかチェック
        if "BaseBuilderテキスト:" in description:
            try:
                # 説明からテキストIDを抽出
                # 形式: "BaseBuilderテキスト: \"title\" (ID: text_id)"
                import re
                pattern = r'BaseBuilderテキスト:\s*"([^"]+)"\s*\(ID:\s*(\d+)\)'
                match = re.search(pattern, description)
                
                if match:
                    text_title = match.group(1)
                    text_id = int(match.group(2))
                    
                    # TextSetを取得
                    text_set = TextSet.query.get(text_id)
                    if text_set:
                        return {
                            'type': 'text',
                            'text_id': text_id,
                            'text_title': text_title,
                            'text_set': text_set,
                            'achievement_threshold': 90  # 90%で完了
                        }
            except Exception as e:
                print(f"[ERROR] BaseBuilder info extraction failed: {e}")
                
        return None
    
    @staticmethod
    def calculate_text_achievement_rate(student_id: int, text_id: int) -> float:
        """テキストの達成率を計算（0-100%）"""
        try:
            # テキストに含まれる問題を取得
            text_set = TextSet.query.get(text_id)
            if not text_set:
                return 0.0
            
            # テキスト内の問題を取得
            problems = BasicKnowledgeItem.query.filter_by(
                text_set_id=text_id,
                is_active=True
            ).all()
            
            if not problems:
                return 0.0
            
            total_problems = len(problems)
            
            # 各問題の熟練度を取得
            mastered_count = 0
            total_proficiency = 0
            
            for problem in problems:
                # 単語熟練度レコードを取得
                word_proficiency = WordProficiency.query.filter_by(
                    student_id=student_id,
                    problem_id=problem.id
                ).first()
                
                if word_proficiency and word_proficiency.level >= 4:
                    # レベル4以上で習得とみなす
                    mastered_count += 1
                    total_proficiency += word_proficiency.level
                elif word_proficiency:
                    total_proficiency += word_proficiency.level
            
            # 達成率計算: 習得した問題数 / 総問題数 * 100
            achievement_rate = (mastered_count / total_problems) * 100
            
            # より詳細な達成率: 熟練度合計 / (総問題数 * 5) * 100
            detailed_rate = (total_proficiency / (total_problems * 5)) * 100
            
            # 2つの方法の平均を使用
            final_rate = (achievement_rate + detailed_rate) / 2
            
            return min(100.0, max(0.0, final_rate))
            
        except Exception as e:
            print(f"[ERROR] Achievement rate calculation failed: {e}")
            return 0.0
    
    @staticmethod
    def check_and_update_task_completion(student_id: int, task_id: int) -> bool:
        """タスクのBaseBuilder達成率をチェックし、必要に応じて自動完了"""
        try:
            # タスクを取得
            from app.modules.lesson_system.models.lesson_models import LessonTask
            task = LessonTask.query.get(task_id)
            if not task:
                return False
            
            # BaseBuilder情報を取得
            bb_info = BaseBuilderTaskService.get_task_basebuilder_info(task)
            if not bb_info or bb_info['type'] != 'text':
                return False
            
            # 達成率を計算
            achievement_rate = BaseBuilderTaskService.calculate_text_achievement_rate(
                student_id, bb_info['text_id']
            )
            
            # 90%以上で自動完了
            if achievement_rate >= bb_info['achievement_threshold']:
                return BaseBuilderTaskService.auto_complete_task(
                    student_id, task_id, achievement_rate
                )
            
            return False
            
        except Exception as e:
            print(f"[ERROR] Task completion check failed: {e}")
            return False
    
    @staticmethod
    def auto_complete_task(student_id: int, task_id: int, achievement_rate: float) -> bool:
        """BaseBuilder達成率に基づいてタスクを自動完了"""
        try:
            # タスクを取得
            from app.modules.lesson_system.models.lesson_models import LessonTask
            task = LessonTask.query.get(task_id)
            if not task:
                return False
            
            # 学生の進捗を取得
            from app.modules.lesson_system.models.lesson_models import StudentLessonProgress
            lesson_progress = StudentLessonProgress.query.filter_by(
                student_id=student_id,
                lesson_id=task.lesson_id
            ).first()
            
            if not lesson_progress:
                # 進捗レコードを作成
                lesson_progress = StudentLessonProgress(
                    student_id=student_id,
                    lesson_id=task.lesson_id,
                    started_at=datetime.utcnow()
                )
                db.session.add(lesson_progress)
                db.session.flush()
            
            # タスクチェック記録を取得または作成
            task_check = StudentTaskCheck.query.filter_by(
                student_id=student_id,
                lesson_progress_id=lesson_progress.id,
                task_id=task_id
            ).first()
            
            if not task_check:
                task_check = StudentTaskCheck(
                    student_id=student_id,
                    lesson_progress_id=lesson_progress.id,
                    task_id=task_id,
                    status=TaskCheckStatus.NOT_CHECKED
                )
                db.session.add(task_check)
            
            # 自動完了処理
            task_check.status = TaskCheckStatus.COMPLETED
            task_check.checked_at = datetime.utcnow()
            task_check.completed_at = datetime.utcnow()
            task_check.time_spent_minutes = 0  # BaseBuilderでの学習時間
            task_check.notes = f"BaseBuilder達成率{achievement_rate:.1f}%により自動完了"
            
            # 進捗の最終活動時刻更新
            lesson_progress.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            print(f"[SUCCESS] Auto-completed task {task_id} for student {student_id} "
                  f"(achievement: {achievement_rate:.1f}%)")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Auto completion failed: {e}")
            return False
    
    @staticmethod
    def get_all_basebuilder_linked_tasks(student_id: int) -> List[Dict]:
        """学生のBaseBuilder連携タスクを全て取得してチェック"""
        try:
            # 学生が受講中のレッスンのタスクを取得
            from app.modules.lesson_system.models.lesson_models import StudentLessonProgress
            
            # 学生の進捗があるレッスンを取得
            lesson_progresses = StudentLessonProgress.query.filter_by(
                student_id=student_id
            ).all()
            
            basebuilder_tasks = []
            
            for progress in lesson_progresses:
                # レッスンのタスクを取得
                tasks = LessonTask.query.filter_by(lesson_id=progress.lesson_id).all()
                
                for task in tasks:
                    bb_info = BaseBuilderTaskService.get_task_basebuilder_info(task)
                    if bb_info and bb_info['type'] == 'text':
                        # 達成率を計算
                        achievement_rate = BaseBuilderTaskService.calculate_text_achievement_rate(
                            student_id, bb_info['text_id']
                        )
                        
                        # タスクチェック状況を取得
                        task_check = StudentTaskCheck.query.filter_by(
                            student_id=student_id,
                            lesson_progress_id=progress.id,
                            task_id=task.id
                        ).first()
                        
                        status = task_check.status.value if task_check else 'not_checked'
                        
                        basebuilder_tasks.append({
                            'task_id': task.id,
                            'task_title': task.title,
                            'lesson_id': task.lesson_id,
                            'lesson_title': task.lesson.title,
                            'text_id': bb_info['text_id'],
                            'text_title': bb_info['text_title'],
                            'achievement_rate': achievement_rate,
                            'threshold': bb_info['achievement_threshold'],
                            'status': status,
                            'auto_complete_eligible': (
                                achievement_rate >= bb_info['achievement_threshold'] 
                                and status != 'completed'
                            )
                        })
            
            return basebuilder_tasks
            
        except Exception as e:
            print(f"[ERROR] Getting BaseBuilder tasks failed: {e}")
            return []
    
    @staticmethod
    def check_all_student_basebuilder_tasks(student_id: int) -> Dict[str, int]:
        """学生の全BaseBuilderタスクをチェックし、必要に応じて自動完了"""
        try:
            basebuilder_tasks = BaseBuilderTaskService.get_all_basebuilder_linked_tasks(student_id)
            
            stats = {
                'total_tasks': len(basebuilder_tasks),
                'auto_completed': 0,
                'already_completed': 0,
                'in_progress': 0
            }
            
            for task_info in basebuilder_tasks:
                if task_info['status'] == 'completed':
                    stats['already_completed'] += 1
                elif task_info['auto_complete_eligible']:
                    # 自動完了を試行
                    if BaseBuilderTaskService.check_and_update_task_completion(
                        student_id, task_info['task_id']
                    ):
                        stats['auto_completed'] += 1
                    else:
                        stats['in_progress'] += 1
                else:
                    stats['in_progress'] += 1
            
            return stats
            
        except Exception as e:
            print(f"[ERROR] Checking all BaseBuilder tasks failed: {e}")
            return {'total_tasks': 0, 'auto_completed': 0, 'already_completed': 0, 'in_progress': 0}


def check_student_basebuilder_progress(student_id: int) -> Dict:
    """学生のBaseBuilder進捗をチェックする便利関数"""
    return BaseBuilderTaskService.check_all_student_basebuilder_tasks(student_id)


def get_task_basebuilder_achievement(student_id: int, task_id: int) -> Optional[Dict]:
    """特定タスクのBaseBuilder達成状況を取得"""
    try:
        from app.modules.lesson_system.models.lesson_models import LessonTask
        task = LessonTask.query.get(task_id)
        if not task:
            return None
            
        bb_info = BaseBuilderTaskService.get_task_basebuilder_info(task)
        if not bb_info or bb_info['type'] != 'text':
            return None
        
        achievement_rate = BaseBuilderTaskService.calculate_text_achievement_rate(
            student_id, bb_info['text_id']
        )
        
        return {
            'text_id': bb_info['text_id'],
            'text_title': bb_info['text_title'],
            'achievement_rate': achievement_rate,
            'threshold': bb_info['achievement_threshold'],
            'is_achievable': achievement_rate >= bb_info['achievement_threshold'],
            'progress_description': f"{achievement_rate:.1f}% / {bb_info['achievement_threshold']}%"
        }
        
    except Exception as e:
        print(f"[ERROR] Getting task BaseBuilder achievement failed: {e}")
        return None