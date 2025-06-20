"""
復習システム管理サービス

弱点分析に基づく復習問題の自動生成と間隔反復学習の管理
"""
import random
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from extensions import db
from app.models import (
    ReviewSet, ReviewSetItem, User
)
# StudentWeakness, ReviewSchedule, ReviewPerformance, ReviewGenerationRule は RDSに存在しないためコメントアウト
from basebuilder.models import BasicKnowledgeItem, AnswerRecord


class ReviewService:
    """復習システム管理サービス"""
    
    @staticmethod
    def generate_review_set(student_id: int, generation_type: str = 'ai_generated',
                          target_weakness_areas: List[str] = None,
                          difficulty_level: int = 2, total_problems: int = 10,
                          review_type: str = 'weakness_focused',
                          estimated_time_minutes: int = 30) -> Dict:
        """
        復習問題セットを生成
        
        Args:
            student_id: 生徒ID
            generation_type: 生成タイプ
            target_weakness_areas: 対象弱点分野
            difficulty_level: 難易度レベル
            total_problems: 総問題数
            review_type: 復習タイプ
            estimated_time_minutes: 推定時間
            
        Returns:
            生成された復習セット
        """
        # 生徒の弱点分析
        if not target_weakness_areas:
            target_weakness_areas = ReviewService._identify_weakness_areas(student_id)
        
        # タイトル生成
        if target_weakness_areas:
            title = f"{', '.join(target_weakness_areas[:3])} 復習セット"
        else:
            title = "総合復習セット"
        
        # 復習セット作成
        review_set = ReviewSet(
            student_id=student_id,
            title=title,
            description=f"弱点分野の強化を目的とした復習セット",
            generation_type=generation_type,
            target_weakness_areas=target_weakness_areas,
            difficulty_level=difficulty_level,
            total_problems=total_problems,
            estimated_time_minutes=estimated_time_minutes,
            review_type=review_type,
            status='draft',
            expires_at=datetime.utcnow() + timedelta(days=7)  # 7日間有効
        )
        
        db.session.add(review_set)
        db.session.flush()  # IDを取得するため
        
        # 問題選択
        if generation_type == 'ai_generated':
            problems = ReviewService._select_problems_ai(
                student_id, target_weakness_areas, difficulty_level, total_problems
            )
        else:
            problems = ReviewService._select_problems_rule_based(
                student_id, target_weakness_areas, difficulty_level, total_problems
            )
        
        # 復習セット問題を作成
        for i, problem_data in enumerate(problems):
            review_item = ReviewSetItem(
                review_set_id=review_set.id,
                problem_id=problem_data['problem_id'],
                order_index=i + 1,
                weight=problem_data.get('weight', 1.0),
                expected_difficulty=problem_data.get('expected_difficulty'),
                weakness_category=problem_data.get('weakness_category'),
                selection_reason=problem_data.get('selection_reason', '')
            )
            db.session.add(review_item)
        
        # ステータスをアクティブに変更
        review_set.activate()
        
        db.session.commit()
        
        # プレビュー問題の取得
        preview_problems = []
        for problem_data in problems[:3]:  # 最初の3問をプレビュー
            problem = BasicKnowledgeItem.query.get(problem_data['problem_id'])
            if problem:
                preview_problems.append({
                    'id': problem.id,
                    'title': problem.title,
                    'difficulty_level': problem.difficulty,
                    'selection_reason': problem_data.get('selection_reason', '')
                })
        
        return {
            'review_set_id': review_set.id,
            'title': review_set.title,
            'total_problems': review_set.total_problems,
            'estimated_time_minutes': review_set.estimated_time_minutes,
            'status': review_set.status,
            'expires_at': review_set.expires_at.isoformat(),
            'problems_preview': preview_problems
        }
    
    @staticmethod
    def get_review_sets(student_id: int, status: str = None, 
                       review_type: str = None, limit: int = 10, 
                       offset: int = 0) -> Dict:
        """
        復習セット一覧を取得
        
        Args:
            student_id: 生徒ID
            status: ステータスフィルタ
            review_type: 復習タイプフィルタ
            limit: 取得件数
            offset: オフセット
            
        Returns:
            復習セット一覧
        """
        query = ReviewSet.query.filter_by(student_id=student_id)
        
        if status:
            query = query.filter(ReviewSet.status == status)
        if review_type:
            query = query.filter(ReviewSet.review_type == review_type)
        
        total = query.count()
        
        review_sets = query.order_by(ReviewSet.created_at.desc())\
                          .offset(offset)\
                          .limit(limit)\
                          .all()
        
        # 各セットの進捗情報を追加
        result_sets = []
        for review_set in review_sets:
            set_data = review_set.to_dict()
            set_data.update({
                'completed_problems': review_set.get_completed_items_count(),
                'accuracy_rate': review_set.get_accuracy_rate()
            })
            result_sets.append(set_data)
        
        return {
            'review_sets': result_sets,
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_next': offset + limit < total
            }
        }
    
    @staticmethod
    def get_review_set_detail(set_id: int, student_id: int) -> Optional[Dict]:
        """
        復習セット詳細を取得
        
        Args:
            set_id: 復習セットID
            student_id: 生徒ID
            
        Returns:
            復習セット詳細
        """
        review_set = ReviewSet.query.filter_by(
            id=set_id,
            student_id=student_id
        ).first()
        
        if not review_set:
            return None
        
        set_data = review_set.to_dict()
        
        # 復習問題詳細を取得
        items_query = db.session.query(ReviewSetItem, BasicKnowledgeItem)\
            .join(BasicKnowledgeItem, ReviewSetItem.problem_id == BasicKnowledgeItem.id)\
            .filter(ReviewSetItem.review_set_id == set_id)\
            .order_by(ReviewSetItem.order_index)
        
        items = []
        completed_items = 0
        correct_items = 0
        total_time = 0
        
        for review_item, problem in items_query:
            item_data = review_item.to_dict()
            item_data.update({
                'title': problem.title,
                'question': problem.question,
                'answer_options': problem.answer_options,
                'explanation': problem.explanation if review_item.is_completed else None
            })
            
            if review_item.is_completed:
                completed_items += 1
                if review_item.is_correct:
                    correct_items += 1
                if review_item.time_spent_seconds:
                    total_time += review_item.time_spent_seconds
            
            items.append(item_data)
        
        # パフォーマンスサマリー
        performance_summary = {
            'completed_items': completed_items,
            'correct_items': correct_items,
            'accuracy_rate': (correct_items / completed_items * 100) if completed_items > 0 else 0.0,
            'average_time_per_problem': total_time / completed_items if completed_items > 0 else 0,
            'total_study_time': total_time
        }
        
        set_data.update({
            'items': items,
            'performance_summary': performance_summary
        })
        
        return set_data
    
    @staticmethod
    def submit_answer(set_id: int, item_id: int, student_id: int,
                     student_answer: str, time_spent_seconds: int = None) -> Dict:
        """
        復習問題の回答を提出
        
        Args:
            set_id: 復習セットID
            item_id: 復習問題アイテムID
            student_id: 生徒ID
            student_answer: 生徒の回答
            time_spent_seconds: 解答時間
            
        Returns:
            採点結果
        """
        # 復習アイテムとオリジナル問題を取得
        review_item = ReviewSetItem.query.filter_by(
            id=item_id,
            review_set_id=set_id
        ).first()
        
        if not review_item:
            raise ValueError("復習問題が見つかりません")
        
        # 復習セットの所有者確認
        review_set = ReviewSet.query.filter_by(
            id=set_id,
            student_id=student_id
        ).first()
        
        if not review_set:
            raise ValueError("アクセス権限がありません")
        
        if review_item.is_completed:
            raise ValueError("この問題は既に回答済みです")
        
        # オリジナル問題を取得
        problem = BasicKnowledgeItem.query.get(review_item.problem_id)
        if not problem:
            raise ValueError("問題データが見つかりません")
        
        # 採点
        is_correct = ReviewService._grade_answer(problem, student_answer)
        
        # 回答を記録
        review_item.answer(student_answer, is_correct, time_spent_seconds)
        
        # 復習パフォーマンスの記録（ReviewPerformanceテーブル未実装のためスキップ）
        # 将来の実装では、answer_recordsテーブルや新しい統計テーブルに記録
        
        # 弱点分析を更新
        if review_item.weakness_category:
            ReviewService._update_weakness_analysis(
                student_id, review_item.weakness_category, is_correct
            )
        
        # 間隔反復学習スケジュール更新
        ReviewService._update_spaced_repetition_schedule(
            student_id, review_item.problem_id, is_correct
        )
        
        db.session.commit()
        
        # 復習セット完了チェック
        completed_count = ReviewSetItem.query.filter_by(
            review_set_id=set_id,
            is_completed=True
        ).count()
        
        if completed_count == review_set.total_problems:
            review_set.complete()
            db.session.commit()
        
        return {
            'is_correct': is_correct,
            'correct_answer': problem.correct_answer,
            'explanation': problem.explanation,
            'review_set_completed': completed_count == review_set.total_problems,
            'next_item_id': ReviewService._get_next_item_id(set_id, item_id)
        }
    
    @staticmethod
    def complete_review_set(set_id: int, student_id: int,
                          completion_time_minutes: int = None,
                          self_assessment: str = None,
                          feedback: str = None) -> Dict:
        """
        復習セット完了処理
        
        Args:
            set_id: 復習セットID
            student_id: 生徒ID
            completion_time_minutes: 完了時間
            self_assessment: 自己評価
            feedback: フィードバック
            
        Returns:
            完了結果
        """
        review_set = ReviewSet.query.filter_by(
            id=set_id,
            student_id=student_id
        ).first()
        
        if not review_set:
            raise ValueError("復習セットが見つかりません")
        
        if review_set.status == 'completed':
            raise ValueError("この復習セットは既に完了しています")
        
        # 完了処理
        review_set.complete()
        
        # 完了時のパフォーマンス計算
        accuracy_rate = review_set.get_accuracy_rate()
        completed_count = review_set.get_completed_items_count()
        
        db.session.commit()
        
        # 次の推薦生成をキュー
        if accuracy_rate >= 80:
            # 正解率が高い場合は難易度を上げた復習を推薦
            next_difficulty = min(5, review_set.difficulty_level + 1)
        else:
            # 正解率が低い場合は同じ難易度で復習を推薦
            next_difficulty = review_set.difficulty_level
        
        return {
            'completion_summary': {
                'total_problems': review_set.total_problems,
                'completed_problems': completed_count,
                'accuracy_rate': accuracy_rate,
                'completion_time_minutes': completion_time_minutes
            },
            'achievements': ReviewService._generate_achievements(accuracy_rate, completion_time_minutes),
            'next_recommendations': {
                'difficulty_level': next_difficulty,
                'recommended_areas': review_set.target_weakness_areas
            }
        }
    
    @staticmethod
    def get_weakness_analysis(student_id: int, subject_id: int = None,
                            severity_level: int = None, is_active: bool = True) -> Dict:
        """
        生徒の弱点分析データを取得
        
        Args:
            student_id: 生徒ID
            subject_id: 教科ID
            severity_level: 深刻度レベル
            is_active: 有効フラグ
            
        Returns:
            弱点分析データ
        """
        # StudentWeaknessテーブルが存在しないため、空の結果を返す
        # 将来の実装では、answer_recordsテーブルから弱点を分析
        
        return {
            'weaknesses': [],
            'summary': {
                'total_weaknesses': 0,
                'critical_weaknesses': 0,
                'improving_weaknesses': 0,
                'stable_weaknesses': 0
            }
        }
    
    @staticmethod
    def get_spaced_repetition_schedule(student_id: int, due_only: bool = True) -> Dict:
        """
        間隔反復学習スケジュールを取得
        
        Args:
            student_id: 生徒ID
            due_only: 復習期限が来た問題のみ取得するか
            
        Returns:
            復習スケジュール
        """
        # ReviewScheduleテーブルが存在しないため、空のスケジュールを返す
        # 将来の実装では、answer_recordsやreview_setsからスケジュールを算出
        
        return {
            'due_reviews': [],
            'upcoming_reviews': [],
            'mastery_distribution': {},
            'total_scheduled': 0
        }
    
    @staticmethod
    def _identify_weakness_areas(student_id: int) -> List[str]:
        """生徒の弱点分野を特定（簡易版 - StudentWeaknessテーブル未実装のため）"""
        # TODO: StudentWeaknessテーブル実装後に本格実装
        # 暫定的に空リストを返す
        return []
    
    @staticmethod
    def _select_problems_ai(student_id: int, weakness_areas: List[str],
                          difficulty_level: int, total_problems: int) -> List[Dict]:
        """AI による問題選択"""
        # 簡易実装：ルールベースと同じロジック
        # 本格実装では OpenAI API を使用
        return ReviewService._select_problems_rule_based(
            student_id, weakness_areas, difficulty_level, total_problems
        )
    
    @staticmethod
    def _select_problems_rule_based(student_id: int, weakness_areas: List[str],
                                  difficulty_level: int, total_problems: int) -> List[Dict]:
        """ルールベースによる問題選択"""
        selected_problems = []
        
        # 弱点分野の問題を優先選択
        for area in weakness_areas:
            problems = BasicKnowledgeItem.query.filter(
                BasicKnowledgeItem.title.contains(area),
                BasicKnowledgeItem.difficulty <= difficulty_level,
                BasicKnowledgeItem.is_active == True
            ).limit(total_problems // len(weakness_areas) if weakness_areas else total_problems).all()
            
            for problem in problems:
                if len(selected_problems) >= total_problems:
                    break
                
                selected_problems.append({
                    'problem_id': problem.id,
                    'weight': 1.0,
                    'expected_difficulty': problem.difficulty,
                    'weakness_category': area,
                    'selection_reason': f"{area}の理解強化のため"
                })
        
        # 不足分を一般問題で補完
        if len(selected_problems) < total_problems:
            remaining = total_problems - len(selected_problems)
            selected_ids = [p['problem_id'] for p in selected_problems]
            
            additional_problems = BasicKnowledgeItem.query.filter(
                BasicKnowledgeItem.difficulty == difficulty_level,
                BasicKnowledgeItem.is_active == True,
                ~BasicKnowledgeItem.id.in_(selected_ids)
            ).limit(remaining).all()
            
            for problem in additional_problems:
                selected_problems.append({
                    'problem_id': problem.id,
                    'weight': 0.8,
                    'expected_difficulty': problem.difficulty,
                    'weakness_category': None,
                    'selection_reason': '総合的な理解確認のため'
                })
        
        # ランダムに並び替え
        random.shuffle(selected_problems)
        
        return selected_problems[:total_problems]
    
    @staticmethod
    def _grade_answer(problem: BasicKnowledgeItem, student_answer: str) -> bool:
        """回答を採点"""
        if not problem.correct_answer or not student_answer:
            return False
        
        # 簡易採点：完全一致
        return problem.correct_answer.strip().lower() == student_answer.strip().lower()
    
    @staticmethod
    def _update_weakness_analysis(student_id: int, category: str, is_correct: bool):
        """弱点分析を更新"""
        # StudentWeaknessテーブルが存在しないため、弱点分析更新はスキップ
        # 将来の実装では、answer_recordsテーブルから統計を算出するか、
        # 新しい弱点追跡テーブルを作成することを推奨
        pass
    
    @staticmethod
    def _update_spaced_repetition_schedule(student_id: int, problem_id: int, is_correct: bool):
        """間隔反復学習スケジュールを更新"""
        # ReviewScheduleテーブルが存在しないため、スケジュール更新はスキップ
        # 将来の実装では、専用の復習スケジュールテーブルを作成するか、
        # 既存のテーブルにスケジュール機能を追加することを推奨
        pass
    
    @staticmethod
    def _get_next_item_id(set_id: int, current_item_id: int) -> Optional[int]:
        """次の復習問題IDを取得"""
        current_item = ReviewSetItem.query.get(current_item_id)
        if not current_item:
            return None
        
        next_item = ReviewSetItem.query.filter(
            ReviewSetItem.review_set_id == set_id,
            ReviewSetItem.order_index > current_item.order_index,
            ReviewSetItem.is_completed == False
        ).order_by(ReviewSetItem.order_index).first()
        
        return next_item.id if next_item else None
    
    @staticmethod
    def _generate_achievements(accuracy_rate: float, completion_time: int = None) -> List[str]:
        """成果バッジを生成"""
        achievements = []
        
        if accuracy_rate >= 95:
            achievements.append("完璧マスター")
        elif accuracy_rate >= 90:
            achievements.append("優秀な成績")
        elif accuracy_rate >= 80:
            achievements.append("良好な理解")
        
        if completion_time and completion_time <= 15:
            achievements.append("スピードマスター")
        
        return achievements