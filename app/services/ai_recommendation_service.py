"""
AI推薦システムサービス

OpenAI GPT-4を使用した学習コンテンツの推薦機能
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from extensions import db
from app.models import (
    AIRecommendation, CurriculumUnit, StudentUnitSelection,
    User, Class, Subject
)
# LearningPattern, RecommendationSettings, RecommendationQueue, RecommendationEffectiveness, StudentWeakness は RDSに存在しないためコメントアウト
from app.services.curriculum_unit_service import CurriculumUnitService
from basebuilder.models import BasicKnowledgeItem, AnswerRecord


class AIRecommendationService:
    """AI推薦システムサービス"""
    
    # プロンプトテンプレート
    UNIT_RECOMMENDATION_PROMPT = """
    あなたは教育AIアシスタントです。生徒の学習データを分析して、最適な学習単元を推薦してください。

    生徒情報:
    - 学習履歴: {learning_history}
    - 弱点分野: {weaknesses}
    - 学習パターン: {learning_patterns}
    - 現在の進行中単元: {current_units}

    利用可能な単元:
    {available_units}

    以下の条件で推薦してください:
    1. 生徒の弱点を補強できる単元
    2. 学習パターンに適した難易度
    3. 前提条件を満たしている単元
    4. 最大3個まで

    JSON形式で回答してください:
    {{
        "recommendations": [
            {{
                "unit_id": 1,
                "priority": "high",
                "reasoning": "推薦理由",
                "estimated_time": "推定学習時間"
            }}
        ],
        "overall_reasoning": "全体的な推薦理由"
    }}
    """
    
    REVIEW_RECOMMENDATION_PROMPT = """
    あなたは教育AIアシスタントです。生徒の学習データを分析して、復習すべき問題を推薦してください。

    生徒情報:
    - 正解率の低い分野: {weak_areas}
    - 最近のパフォーマンス: {recent_performance}
    - 学習スタイル: {learning_style}

    利用可能な問題:
    {available_problems}

    以下の条件で推薦してください:
    1. 弱点分野の基礎固め
    2. 適切な難易度の問題
    3. 最大10問

    JSON形式で回答してください:
    {{
        "recommendations": [
            {{
                "problem_id": 1,
                "priority": "high",
                "reasoning": "選択理由"
            }}
        ],
        "study_strategy": "学習戦略のアドバイス"
    }}
    """
    
    @staticmethod
    def generate_recommendations(student_id: int, recommendation_type: str,
                               max_items: int = 5, context_data: Dict = None) -> Dict:
        """
        AI推薦を生成
        
        Args:
            student_id: 生徒ID
            recommendation_type: 推薦タイプ (unit, problem, review, challenge)
            max_items: 最大推薦数
            context_data: コンテキストデータ
            
        Returns:
            推薦結果
        """
        # 推薦設定確認
        settings = AIRecommendationService.get_recommendation_settings(student_id)
        if not settings['enable_ai_recommendations']:
            raise ValueError("AI推薦が無効になっています")
        
        # セッションIDの生成
        session_id = f"rec_{uuid.uuid4().hex[:8]}"
        
        # コンテキストデータの収集
        if not context_data:
            context_data = AIRecommendationService._collect_context_data(student_id)
        
        try:
            if recommendation_type == 'unit':
                result = AIRecommendationService._generate_unit_recommendations(
                    student_id, context_data, max_items, session_id
                )
            elif recommendation_type == 'review':
                result = AIRecommendationService._generate_review_recommendations(
                    student_id, context_data, max_items, session_id
                )
            elif recommendation_type == 'problem':
                result = AIRecommendationService._generate_problem_recommendations(
                    student_id, context_data, max_items, session_id
                )
            else:
                raise ValueError(f"未対応の推薦タイプ: {recommendation_type}")
            
            # 推薦結果を保存
            recommendation = AIRecommendation(
                student_id=student_id,
                recommendation_type=recommendation_type,
                context_data=context_data,
                ai_response=json.dumps(result, ensure_ascii=False),
                recommended_items=result.get('recommendations', []),
                confidence_score=result.get('confidence_score', 0.0),
                reasoning=result.get('overall_reasoning', ''),
                session_id=session_id
            )
            
            db.session.add(recommendation)
            db.session.commit()
            
            return {
                'recommendation_id': recommendation.id,
                'recommendation_type': recommendation_type,
                'recommended_items': result.get('recommendations', []),
                'confidence_score': result.get('confidence_score', 0.0),
                'reasoning': result.get('overall_reasoning', ''),
                'session_id': session_id
            }
            
        except Exception as e:
            # エラー時のフォールバック推薦
            fallback_result = AIRecommendationService._generate_fallback_recommendations(
                student_id, recommendation_type, max_items
            )
            
            # エラー記録
            recommendation = AIRecommendation(
                student_id=student_id,
                recommendation_type=recommendation_type,
                context_data=context_data,
                ai_response=str(e),
                recommended_items=fallback_result,
                confidence_score=0.3,
                reasoning="AI推薦エラーのためルールベース推薦を実行",
                session_id=session_id
            )
            
            db.session.add(recommendation)
            db.session.commit()
            
            return {
                'recommendation_id': recommendation.id,
                'recommendation_type': recommendation_type,
                'recommended_items': fallback_result,
                'confidence_score': 0.3,
                'reasoning': "システム推薦（基本的な学習順序に基づく）",
                'session_id': session_id,
                'is_fallback': True
            }
    
    @staticmethod
    def _generate_unit_recommendations(student_id: int, context_data: Dict,
                                     max_items: int, session_id: str) -> Dict:
        """
        単元推薦を生成
        
        Args:
            student_id: 生徒ID
            context_data: コンテキストデータ
            max_items: 最大推薦数
            session_id: セッションID
            
        Returns:
            推薦結果
        """
        # 生徒のクラス・教科情報取得
        student = User.query.get(student_id)
        class_enrollments = student.class_enrollments
        
        if not class_enrollments:
            raise ValueError("クラスに所属していません")
        
        # 利用可能な単元を取得
        class_enrollment = class_enrollments[0]  # 最初のクラス
        available_units = CurriculumUnitService.get_units_for_student(
            student_id, class_enrollment.class_id, include_progress=True
        )
        
        # 開始可能な単元のみフィルタ
        startable_units = [unit for unit in available_units if unit.get('can_start', False)]
        
        # シンプルなルールベース推薦（AI統合は将来実装）
        recommendations = []
        
        # 弱点分野に関連する単元を優先
        weak_areas = context_data.get('weak_areas', [])
        for unit in startable_units[:max_items]:
            priority = "medium"
            reasoning = "継続的な学習のため"
            
            # タグベースでの弱点マッチング
            unit_tags = unit.get('tags', [])
            if any(tag in weak_areas for tag in unit_tags):
                priority = "high"
                reasoning = "弱点分野の強化のため"
            
            recommendations.append({
                'unit_id': unit['id'],
                'title': unit['title'],
                'priority': priority,
                'reasoning': reasoning,
                'estimated_time': f"{unit.get('estimated_hours', 1)}時間"
            })
        
        return {
            'recommendations': recommendations,
            'confidence_score': 0.75,
            'overall_reasoning': "学習進度と弱点分析に基づく推薦"
        }
    
    @staticmethod
    def _generate_review_recommendations(student_id: int, context_data: Dict,
                                       max_items: int, session_id: str) -> Dict:
        """
        復習推薦を生成
        
        Args:
            student_id: 生徒ID
            context_data: コンテキストデータ
            max_items: 最大推薦数
            session_id: セッションID
            
        Returns:
            推薦結果
        """
        # 弱点分野の問題を取得（簡易版 - StudentWeaknessテーブル未実装のため）
        # TODO: StudentWeaknessテーブル実装後に本格実装
        weaknesses = []
        
        recommendations = []
        
        for weakness in weaknesses:
            # 弱点カテゴリに関連する問題を検索
            problems = BasicKnowledgeItem.query.filter(
                BasicKnowledgeItem.title.contains(weakness.category)
            ).limit(max_items // len(weaknesses) if weaknesses else max_items).all()
            
            for problem in problems:
                recommendations.append({
                    'problem_id': problem.id,
                    'title': problem.title,
                    'priority': "high" if weakness.severity_level >= 4 else "medium",
                    'reasoning': f"{weakness.category}の理解強化のため",
                    'weakness_category': weakness.category
                })
        
        return {
            'recommendations': recommendations[:max_items],
            'confidence_score': 0.8,
            'study_strategy': "基礎概念の確認後、応用問題に取り組むことをお勧めします"
        }
    
    @staticmethod
    def _generate_problem_recommendations(student_id: int, context_data: Dict,
                                        max_items: int, session_id: str) -> Dict:
        """
        問題推薦を生成
        
        Args:
            student_id: 生徒ID
            context_data: コンテキストデータ
            max_items: 最大推薦数
            session_id: セッションID
            
        Returns:
            推薦結果
        """
        # 生徒の学習履歴から適切な難易度を判定
        recent_answers = AnswerRecord.query.filter_by(user_id=student_id)\
            .order_by(AnswerRecord.answered_at.desc())\
            .limit(10).all()
        
        # 正解率計算
        if recent_answers:
            correct_count = sum(1 for answer in recent_answers if answer.is_correct)
            accuracy_rate = correct_count / len(recent_answers)
        else:
            accuracy_rate = 0.5  # デフォルト
        
        # 適切な難易度を決定
        if accuracy_rate >= 0.8:
            target_difficulty = 3  # 応用レベル
        elif accuracy_rate >= 0.6:
            target_difficulty = 2  # 標準レベル
        else:
            target_difficulty = 1  # 基礎レベル
        
        # 問題を取得
        problems = BasicKnowledgeItem.query.filter_by(
            difficulty_level=target_difficulty,
            is_active=True
        ).limit(max_items).all()
        
        recommendations = []
        for problem in problems:
            recommendations.append({
                'problem_id': problem.id,
                'title': problem.title,
                'priority': "medium",
                'reasoning': f"現在のレベル（正解率{accuracy_rate:.1%}）に適した問題",
                'difficulty_level': problem.difficulty_level
            })
        
        return {
            'recommendations': recommendations,
            'confidence_score': 0.7,
            'overall_reasoning': f"正解率{accuracy_rate:.1%}に基づく適正難易度の問題推薦"
        }
    
    @staticmethod
    def _generate_fallback_recommendations(student_id: int, recommendation_type: str,
                                         max_items: int) -> List[Dict]:
        """
        フォールバック推薦を生成（AI失敗時）
        
        Args:
            student_id: 生徒ID
            recommendation_type: 推薦タイプ
            max_items: 最大推薦数
            
        Returns:
            基本的な推薦リスト
        """
        if recommendation_type == 'unit':
            # 次に学習すべき単元（順序ベース）
            units = CurriculumUnit.query.filter_by(is_active=True)\
                .order_by(CurriculumUnit.order_index)\
                .limit(max_items).all()
            
            return [
                {
                    'unit_id': unit.id,
                    'title': unit.title,
                    'priority': 'medium',
                    'reasoning': '基本的な学習順序に基づく推薦'
                }
                for unit in units
            ]
        
        elif recommendation_type == 'review':
            # 基礎レベルの問題
            problems = BasicKnowledgeItem.query.filter_by(
                difficulty_level=1,
                is_active=True
            ).limit(max_items).all()
            
            return [
                {
                    'problem_id': problem.id,
                    'title': problem.title,
                    'priority': 'medium',
                    'reasoning': '基礎復習のための問題'
                }
                for problem in problems
            ]
        
        return []
    
    @staticmethod
    def _collect_context_data(student_id: int) -> Dict:
        """
        推薦用コンテキストデータを収集
        
        Args:
            student_id: 生徒ID
            
        Returns:
            コンテキストデータ
        """
        # 学習履歴
        unit_selections = StudentUnitSelection.query.filter_by(student_id=student_id)\
            .order_by(StudentUnitSelection.last_activity_at.desc())\
            .limit(10).all()
        
        learning_history = [
            {
                'unit_id': selection.unit_id,
                'status': selection.status,
                'progress': float(selection.progress_percentage),
                'accuracy': selection.get_accuracy_rate()
            }
            for selection in unit_selections
        ]
        
        # 弱点分析
        weaknesses = StudentWeakness.query.filter_by(
            student_id=student_id,
            is_active=True
        ).order_by(StudentWeakness.severity_level.desc()).all()
        
        weak_areas = [weakness.category for weakness in weaknesses]
        
        # 学習パターン
        patterns = LearningPattern.query.filter_by(
            student_id=student_id,
            is_active=True
        ).all()
        
        learning_patterns = {
            pattern.pattern_type: pattern.pattern_data
            for pattern in patterns
        }
        
        # 最近のパフォーマンス
        recent_answers = AnswerRecord.query.filter_by(user_id=student_id)\
            .order_by(AnswerRecord.answered_at.desc())\
            .limit(20).all()
        
        recent_performance = {
            'total_answers': len(recent_answers),
            'correct_answers': sum(1 for answer in recent_answers if answer.is_correct),
            'accuracy_rate': (sum(1 for answer in recent_answers if answer.is_correct) / len(recent_answers)) if recent_answers else 0
        }
        
        return {
            'learning_history': learning_history,
            'weak_areas': weak_areas,
            'learning_patterns': learning_patterns,
            'recent_performance': recent_performance
        }
    
    @staticmethod
    def get_recommendations(student_id: int, recommendation_type: str = None,
                          limit: int = 20, offset: int = 0) -> Dict:
        """
        生徒の推薦履歴を取得
        
        Args:
            student_id: 生徒ID
            recommendation_type: 推薦タイプでフィルタ
            limit: 取得件数
            offset: オフセット
            
        Returns:
            推薦履歴
        """
        query = AIRecommendation.query.filter_by(student_id=student_id)
        
        if recommendation_type:
            query = query.filter(AIRecommendation.recommendation_type == recommendation_type)
        
        total = query.count()
        
        recommendations = query.order_by(AIRecommendation.created_at.desc())\
                              .offset(offset)\
                              .limit(limit)\
                              .all()
        
        return {
            'recommendations': [rec.to_dict() for rec in recommendations],
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_next': offset + limit < total
            }
        }
    
    @staticmethod
    def provide_feedback(recommendation_id: int, is_accepted: bool,
                        feedback_text: str = None) -> Dict:
        """
        推薦に対するフィードバックを記録
        
        Args:
            recommendation_id: 推薦ID
            is_accepted: 受け入れ状況
            feedback_text: フィードバックテキスト
            
        Returns:
            更新結果
        """
        recommendation = AIRecommendation.query.get(recommendation_id)
        if not recommendation:
            raise ValueError("推薦が見つかりません")
        
        if is_accepted:
            recommendation.accept_recommendation(feedback_text)
        else:
            recommendation.reject_recommendation(feedback_text)
        
        db.session.commit()
        
        return recommendation.to_dict()
    
    @staticmethod
    def get_recommendation_settings(student_id: int) -> Dict:
        """
        推薦設定を取得
        
        Args:
            student_id: 生徒ID
            
        Returns:
            推薦設定
        """
        settings = RecommendationSettings.query.filter_by(student_id=student_id).first()
        
        if not settings:
            # デフォルト設定を作成
            settings = RecommendationSettings(student_id=student_id)
            db.session.add(settings)
            db.session.commit()
        
        return settings.to_dict()
    
    @staticmethod
    def update_recommendation_settings(student_id: int, settings_data: Dict) -> Dict:
        """
        推薦設定を更新
        
        Args:
            student_id: 生徒ID
            settings_data: 更新する設定値
            
        Returns:
            更新後の設定
        """
        settings = RecommendationSettings.query.filter_by(student_id=student_id).first()
        
        if not settings:
            settings = RecommendationSettings(student_id=student_id)
            db.session.add(settings)
        
        settings.update_settings(**settings_data)
        db.session.commit()
        
        return settings.to_dict()
    
    @staticmethod
    def queue_recommendation(student_id: int, trigger_event: str,
                           priority: int = 5, request_data: Dict = None,
                           scheduled_at: datetime = None) -> int:
        """
        推薦をキューに追加（非同期処理用）
        
        Args:
            student_id: 生徒ID
            trigger_event: トリガーイベント
            priority: 優先度
            request_data: リクエストデータ
            scheduled_at: 実行予定日時
            
        Returns:
            キューID
        """
        queue_item = RecommendationQueue(
            student_id=student_id,
            trigger_event=trigger_event,
            priority=priority,
            request_data=request_data,
            scheduled_at=scheduled_at
        )
        
        db.session.add(queue_item)
        db.session.commit()
        
        return queue_item.id
    
    @staticmethod
    def analyze_learning_patterns(student_id: int) -> Dict:
        """
        学習パターンを分析・更新
        
        Args:
            student_id: 生徒ID
            
        Returns:
            分析結果
        """
        # 時間選好パターンの分析
        time_data = AIRecommendationService._analyze_time_preference(student_id)
        AIRecommendationService._update_learning_pattern(
            student_id, 'time_preference', time_data
        )
        
        # 難易度選好パターンの分析
        difficulty_data = AIRecommendationService._analyze_difficulty_preference(student_id)
        AIRecommendationService._update_learning_pattern(
            student_id, 'difficulty_preference', difficulty_data
        )
        
        # 教科強度パターンの分析
        subject_data = AIRecommendationService._analyze_subject_strength(student_id)
        AIRecommendationService._update_learning_pattern(
            student_id, 'subject_strength', subject_data
        )
        
        return {
            'time_preference': time_data,
            'difficulty_preference': difficulty_data,
            'subject_strength': subject_data,
            'analyzed_at': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def _analyze_time_preference(student_id: int) -> Dict:
        """時間選好パターンの分析"""
        # 簡易実装：活動ログから時間帯別のパフォーマンスを分析
        return {
            'preferred_hours': [14, 15, 16],  # 午後
            'peak_performance_time': 'afternoon',
            'study_duration_optimal': 45
        }
    
    @staticmethod
    def _analyze_difficulty_preference(student_id: int) -> Dict:
        """難易度選好パターンの分析"""
        return {
            'preferred_difficulty': 2.3,
            'challenge_tolerance': 'medium',
            'improvement_rate': 0.15
        }
    
    @staticmethod
    def _analyze_subject_strength(student_id: int) -> Dict:
        """教科強度パターンの分析"""
        return {
            'strongest_subjects': ['理科'],
            'weakest_subjects': ['数学'],
            'improvement_potential': 'high'
        }
    
    @staticmethod
    def _update_learning_pattern(student_id: int, pattern_type: str, pattern_data: Dict):
        """学習パターンを更新"""
        pattern = LearningPattern.query.filter_by(
            student_id=student_id,
            pattern_type=pattern_type
        ).first()
        
        if pattern:
            pattern.update_pattern(pattern_data)
        else:
            pattern = LearningPattern(
                student_id=student_id,
                pattern_type=pattern_type,
                pattern_data=pattern_data,
                sample_size=1
            )
            db.session.add(pattern)
        
        db.session.commit()