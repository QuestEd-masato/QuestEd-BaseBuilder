"""
QuestEd AI推薦エンジンモジュール

このモジュールは、OpenAI GPT-4を活用した個別化学習推薦システムを提供します。
学生の学習パターン、成績、興味を分析し、最適な学習コンテンツを推薦します。

主な機能:
- 学習パターン分析に基づく個別推薦
- BaseBuilderとの統合による詳細な語彙データ活用
- OpenAI API障害時のフォールバック機能
- 推薦履歴の管理と効果測定

新規開発者向けガイド:
1. OpenAI APIキーの設定が必要（環境変数: OPENAI_API_KEY）
2. 推薦生成は非同期処理を推奨（時間がかかる場合がある）
3. フォールバック機能により、API障害時も基本機能は動作
4. 学習データが少ない場合は推薦精度が低下する可能性あり

使用例:
    engine = AIRecommendationEngine()
    recommendations = engine.generate_recommendations(student_id=123)

Author: QuestEd Development Team
Created: 2025
Last Modified: 2025-01-15
Version: 2.1.0
"""

import json
import logging
import openai
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import and_, or_, desc, func
from flask import current_app

from app.models import (
    User, AIRecommendation, LearningPattern, RecommendationSettings,
    CurriculumUnit, StudentUnitSelection, Subject, ActivityLog, Todo, Goal,
    BasicKnowledgeItem, ProficiencyRecord, WordProficiency, TextSet, 
    LearningPath, PathAssignment, AnswerRecord
)
from app.services.pattern_analyzer import PatternAnalyzerService
from app.utils.exceptions import AIRecommendationError, InsufficientDataError
from extensions import db

logger = logging.getLogger(__name__)


class AIRecommendationEngine:
    """
    AI推薦エンジン - OpenAI APIを活用した個別学習推薦システム
    
    このクラスは、学生の学習履歴と行動パターンを分析し、
    個別化された学習推薦を生成する核となる機能を提供します。
    
    処理フロー:
    1. 学生の学習データ収集（単元進捗、BaseBuilder語彙データなど）
    2. 学習パターン分析（時間帯、難易度傾向、科目強度など）
    3. OpenAI GPT-4による推薦生成
    4. フォールバック推薦（API障害時）
    5. 推薦履歴の保存と効果測定
    
    依存関係:
    - PatternAnalyzerService: 学習パターン分析
    - OpenAI API: AI推薦生成
    - 各種モデル: 学習データアクセス
    
    セキュリティ考慮事項:
    - OpenAI APIキーの安全な管理
    - 学習データのプライバシー保護
    - API レート制限の遵守
    """
    
    def __init__(self):
        """
        AI推薦エンジンの初期化
        
        初期化処理:
        1. パターン分析サービスの初期化
        2. OpenAI クライアントの設定
        3. API接続の確認
        """
        self.pattern_analyzer = PatternAnalyzerService()
        self.openai_client = openai
        self._setup_openai()
    
    def _setup_openai(self):
        """OpenAI APIの設定"""
        api_key = current_app.config.get('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OpenAI APIキーが設定されていません。AI推薦機能が無効になります。")
            self.openai_client = None
        else:
            self.openai_client.api_key = api_key
    
    def generate_recommendations(
        self,
        student_id: int,
        recommendation_type: str = 'unit',
        max_recommendations: int = 5,
        force_regenerate: bool = False
    ) -> List[Dict[str, Any]]:
        """
        学生に対する個別化推薦を生成
        
        Args:
            student_id: 学生ID
            recommendation_type: 推薦タイプ ('unit', 'problem', 'study_path', 'review', 'challenge')
            max_recommendations: 最大推薦数
            force_regenerate: 強制再生成フラグ
            
        Returns:
            推薦リスト
        """
        try:
            student = User.query.get(student_id)
            if not student or student.role != 'student':
                raise AIRecommendationError("有効な学生が見つかりません")
            
            # 推薦設定を取得
            settings = RecommendationSettings.query.filter_by(student_id=student_id).first()
            if not settings:
                settings = self._create_default_settings(student_id)
            
            if not settings.enable_ai_recommendations:
                logger.info(f"学生 {student_id} はAI推薦を無効にしています")
                return []
            
            # 既存の推薦をチェック（強制再生成でない場合）
            if not force_regenerate:
                recent_recommendations = self._get_recent_recommendations(
                    student_id, recommendation_type, hours=24
                )
                if recent_recommendations:
                    logger.info(f"学生 {student_id} の24時間以内の推薦を返却")
                    return recent_recommendations
            
            # 学習パターンを取得・更新
            learning_patterns = self._get_or_update_learning_patterns(student_id)
            
            # 学習データの収集
            learning_data = self._collect_learning_data(student_id)
            
            # AI推薦の生成
            recommendations = self._generate_ai_recommendations(
                student, learning_patterns, learning_data, 
                recommendation_type, max_recommendations, settings
            )
            
            # 推薦履歴の保存
            self._save_recommendations(student_id, recommendations, recommendation_type)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"推薦生成エラー (学生ID: {student_id}): {str(e)}")
            raise AIRecommendationError(f"推薦生成中にエラーが発生しました: {str(e)}")
    
    def _create_default_settings(self, student_id: int) -> RecommendationSettings:
        """デフォルトの推薦設定を作成"""
        settings = RecommendationSettings(
            student_id=student_id,
            enable_ai_recommendations=True,
            recommendation_frequency='daily',
            max_recommendations_per_session=5,
            preferred_difficulty_adjustment=0.0,
            enable_challenge_problems=True,
            enable_review_recommendations=True,
            privacy_level='full'
        )
        db.session.add(settings)
        db.session.commit()
        return settings
    
    def _get_recent_recommendations(
        self, 
        student_id: int, 
        recommendation_type: str, 
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """最近の推薦を取得"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent = AIRecommendation.query.filter(
            and_(
                AIRecommendation.student_id == student_id,
                AIRecommendation.recommendation_type == recommendation_type,
                AIRecommendation.created_at >= cutoff_time
            )
        ).order_by(desc(AIRecommendation.created_at)).first()
        
        if recent and recent.recommended_items:
            return recent.recommended_items
        return []
    
    def _get_or_update_learning_patterns(self, student_id: int) -> Dict[str, Any]:
        """学習パターンを取得または更新"""
        try:
            # 最新の学習パターンを分析
            self.pattern_analyzer.analyze_all_patterns(student_id)
            
            # データベースからパターンを取得
            patterns = LearningPattern.query.filter_by(
                student_id=student_id,
                is_active=True
            ).all()
            
            pattern_data = {}
            for pattern in patterns:
                pattern_data[pattern.pattern_type] = {
                    'data': pattern.pattern_data,
                    'confidence': float(pattern.confidence_level),
                    'sample_size': pattern.sample_size
                }
            
            return pattern_data
            
        except Exception as e:
            logger.warning(f"学習パターン取得エラー (学生ID: {student_id}): {str(e)}")
            return {}
    
    def _collect_learning_data(self, student_id: int) -> Dict[str, Any]:
        """学習データを収集"""
        data = {
            'unit_selections': [],
            'proficiency_records': [],
            'activity_logs': [],
            'todos': [],
            'goals': [],
            'recent_performance': {}
        }
        
        try:
            # 単元選択履歴
            unit_selections = StudentUnitSelection.query.filter_by(
                student_id=student_id
            ).order_by(desc(StudentUnitSelection.last_activity_at)).limit(20).all()
            
            for selection in unit_selections:
                data['unit_selections'].append({
                    'unit_id': selection.unit_id,
                    'unit_title': selection.unit.title if selection.unit else 'Unknown',
                    'status': selection.status,
                    'progress': float(selection.progress_percentage) if selection.progress_percentage else 0,
                    'study_time': selection.study_time_minutes,
                    'difficulty': selection.unit.difficulty_level if selection.unit else 2,
                    'last_activity': selection.last_activity_at.isoformat() if selection.last_activity_at else None
                })
            
            # 熟練度記録（BaseBuilderモジュール）
            proficiency_records = ProficiencyRecord.query.filter_by(
                student_id=student_id
            ).order_by(desc(ProficiencyRecord.last_updated)).limit(30).all()
            
            for record in proficiency_records:
                data['proficiency_records'].append({
                    'category_id': record.category_id,
                    'category_name': record.category.name if record.category else 'Unknown',
                    'level': record.level,
                    'adjusted_proficiency': record.adjusted_proficiency,
                    'last_updated': record.last_updated.isoformat() if record.last_updated else None,
                    'review_date': record.review_date.isoformat() if record.review_date else None
                })
            
            # 単語レベルの熟練度記録
            word_proficiency = WordProficiency.query.filter_by(
                student_id=student_id
            ).order_by(desc(WordProficiency.last_updated)).limit(50).all()
            
            data['word_proficiency'] = []
            for wp in word_proficiency:
                try:
                    data['word_proficiency'].append({
                        'problem_id': wp.problem_id,
                        'word_title': wp.problem.title if wp.problem else 'Unknown',
                        'category_name': wp.problem.category.name if (wp.problem and wp.problem.category) else 'Unknown',
                        'level': getattr(wp, 'level', 0),
                        'last_updated': wp.last_updated.isoformat() if wp.last_updated else None,
                        'review_date': wp.review_date.isoformat() if wp.review_date else None,
                        'difficulty': wp.problem.difficulty if wp.problem else 2
                    })
                except Exception as e:
                    logger.warning(f"AI推薦用単語熟練度記録処理エラー (ID: {wp.id}): {str(e)}")
            
            # 学習パス進捗
            path_assignments = PathAssignment.query.filter_by(
                student_id=student_id
            ).order_by(desc(PathAssignment.assigned_at)).limit(10).all()
            
            data['learning_paths'] = []
            for assignment in path_assignments:
                data['learning_paths'].append({
                    'path_id': assignment.path_id,
                    'path_title': assignment.path.title if assignment.path else 'Unknown',
                    'progress': assignment.progress,
                    'completed': assignment.completed,
                    'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
                    'assigned_at': assignment.assigned_at.isoformat() if assignment.assigned_at else None
                })
            
            # 活動記録
            recent_activities = ActivityLog.query.filter_by(
                student_id=student_id
            ).order_by(desc(ActivityLog.timestamp)).limit(10).all()
            
            for activity in recent_activities:
                data['activity_logs'].append({
                    'title': activity.title,
                    'content_length': len(activity.content) if activity.content else 0,
                    'reflection_length': len(activity.reflection) if activity.reflection else 0,
                    'timestamp': activity.timestamp.isoformat() if activity.timestamp else None
                })
            
            # タスクと目標
            active_todos = Todo.query.filter_by(
                student_id=student_id,
                is_completed=False
            ).count()
            
            active_goals = Goal.query.filter_by(
                student_id=student_id,
                is_completed=False
            ).count()
            
            data['todos'] = {'active_count': active_todos}
            data['goals'] = {'active_count': active_goals}
            
            # 最近のパフォーマンス分析
            data['recent_performance'] = self._analyze_recent_performance(student_id)
            
        except Exception as e:
            logger.warning(f"学習データ収集エラー (学生ID: {student_id}): {str(e)}")
        
        return data
    
    def _analyze_recent_performance(self, student_id: int) -> Dict[str, Any]:
        """最近のパフォーマンスを分析"""
        performance = {
            'average_accuracy': 0.0,
            'study_streak_days': 0,
            'preferred_subjects': [],
            'improvement_trend': 'stable'
        }
        
        try:
            # 過去30日の熟練度記録から平均正答率を計算
            recent_records = ProficiencyRecord.query.filter(
                and_(
                    ProficiencyRecord.student_id == student_id,
                    ProficiencyRecord.last_updated >= datetime.utcnow() - timedelta(days=30)
                )
            ).all()
            
            if recent_records:
                total_accuracy = sum(record.accuracy_rate for record in recent_records)
                performance['average_accuracy'] = total_accuracy / len(recent_records)
            
            # 学習継続日数を計算
            performance['study_streak_days'] = self._calculate_study_streak(student_id)
            
            # 得意科目を特定
            performance['preferred_subjects'] = self._identify_preferred_subjects(student_id)
            
        except Exception as e:
            logger.warning(f"パフォーマンス分析エラー (学生ID: {student_id}): {str(e)}")
        
        return performance
    
    def _calculate_study_streak(self, student_id: int) -> int:
        """学習継続日数を計算"""
        try:
            # 単元選択の最新活動日から継続日数を計算
            recent_activities = StudentUnitSelection.query.filter(
                and_(
                    StudentUnitSelection.student_id == student_id,
                    StudentUnitSelection.last_activity_at.isnot(None)
                )
            ).order_by(desc(StudentUnitSelection.last_activity_at)).all()
            
            if not recent_activities:
                return 0
            
            streak_days = 0
            current_date = datetime.utcnow().date()
            
            for activity in recent_activities:
                activity_date = activity.last_activity_at.date()
                if (current_date - activity_date).days == streak_days:
                    streak_days += 1
                    current_date = activity_date
                else:
                    break
            
            return streak_days
            
        except Exception:
            return 0
    
    def _identify_preferred_subjects(self, student_id: int) -> List[str]:
        """得意科目を特定"""
        try:
            # 熟練度記録から高い正答率の科目を特定
            high_performance_records = ProficiencyRecord.query.filter(
                and_(
                    ProficiencyRecord.student_id == student_id,
                    ProficiencyRecord.accuracy_rate >= 0.8,
                    ProficiencyRecord.total_attempted >= 5
                )
            ).order_by(desc(ProficiencyRecord.accuracy_rate)).limit(3).all()
            
            subjects = []
            for record in high_performance_records:
                if record.category and record.category.name:
                    subjects.append(record.category.name)
            
            return subjects
            
        except Exception:
            return []
    
    def _generate_ai_recommendations(
        self,
        student: User,
        learning_patterns: Dict[str, Any],
        learning_data: Dict[str, Any],
        recommendation_type: str,
        max_recommendations: int,
        settings: RecommendationSettings
    ) -> List[Dict[str, Any]]:
        """OpenAI APIを使用してAI推薦を生成"""
        
        # プロンプトテンプレートを構築
        prompt = self._build_recommendation_prompt(
            student, learning_patterns, learning_data, recommendation_type, settings
        )
        
        try:
            # OpenAI APIが設定されているかチェック
            if not self.openai_client:
                logger.warning("OpenAI APIが設定されていません。フォールバック推薦を使用します。")
                return self._generate_fallback_recommendations(
                    student.id, recommendation_type, max_recommendations
                )
            
            # OpenAI APIへのリクエスト
            response = self.openai_client.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは個別化学習推薦の専門家です。学生の学習データとパターンを分析し、最適な学習内容を推薦してください。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            # レスポンスを解析
            ai_response = response.choices[0].message.content
            recommendations = self._parse_ai_response(
                ai_response, recommendation_type, max_recommendations
            )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"OpenAI API エラー: {str(e)}")
            # フォールバック推薦を生成
            return self._generate_fallback_recommendations(
                student.id, recommendation_type, max_recommendations
            )
    
    def _build_recommendation_prompt(
        self,
        student: User,
        learning_patterns: Dict[str, Any],
        learning_data: Dict[str, Any],
        recommendation_type: str,
        settings: RecommendationSettings
    ) -> str:
        """推薦用プロンプトを構築"""
        
        prompt_parts = [
            f"学生情報:",
            f"- 名前: {student.get_display_name()}",
            f"- 学習パターン: {json.dumps(learning_patterns, ensure_ascii=False, indent=2)}",
            f"- 最近の学習データ: {json.dumps(learning_data, ensure_ascii=False, indent=2)}",
            f"",
            f"推薦タイプ: {recommendation_type}",
            f"最大推薦数: {settings.max_recommendations_per_session}",
            f"難易度調整: {settings.preferred_difficulty_adjustment}",
            f"チャレンジ問題有効: {settings.enable_challenge_problems}",
            f"復習推薦有効: {settings.enable_review_recommendations}",
            f"",
            f"以下の形式でJSON配列として推薦を返してください:",
            f"[",
            f"  {{",
            f"    \"item_id\": 単元またはアイテムID,",
            f"    \"title\": \"推薦タイトル\",",
            f"    \"description\": \"推薦理由の説明\",",
            f"    \"confidence_score\": 0.0-1.0の信頼度,",
            f"    \"reasoning\": \"推薦の根拠\",",
            f"    \"estimated_time_minutes\": 予想学習時間,",
            f"    \"difficulty_level\": 1-3の難易度",
            f"  }}",
            f"]"
        ]
        
        return "\n".join(prompt_parts)
    
    def _parse_ai_response(
        self, 
        ai_response: str, 
        recommendation_type: str, 
        max_recommendations: int
    ) -> List[Dict[str, Any]]:
        """AI応答を解析して推薦リストに変換"""
        try:
            # JSONの抽出を試行
            start_idx = ai_response.find('[')
            end_idx = ai_response.rfind(']') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = ai_response[start_idx:end_idx]
                recommendations = json.loads(json_str)
                
                # 推薦数を制限
                if len(recommendations) > max_recommendations:
                    recommendations = recommendations[:max_recommendations]
                
                # 各推薦にメタデータを追加
                for rec in recommendations:
                    rec['recommendation_type'] = recommendation_type
                    rec['generated_at'] = datetime.utcnow().isoformat()
                    
                    # 必須フィールドのバリデーション
                    if 'confidence_score' not in rec:
                        rec['confidence_score'] = 0.5
                    if 'estimated_time_minutes' not in rec:
                        rec['estimated_time_minutes'] = 30
                    if 'difficulty_level' not in rec:
                        rec['difficulty_level'] = 2
                
                return recommendations
            else:
                raise ValueError("有効なJSONが見つかりません")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"AI応答の解析に失敗: {str(e)}")
            # フォールバック処理
            return []
    
    def _generate_fallback_recommendations(
        self, 
        student_id: int, 
        recommendation_type: str, 
        max_recommendations: int
    ) -> List[Dict[str, Any]]:
        """フォールバック推薦を生成（ルールベース）"""
        try:
            recommendations = []
            
            if recommendation_type == 'unit':
                # 未開始の単元から推薦
                unstarted_units = db.session.query(CurriculumUnit).filter(
                    ~CurriculumUnit.id.in_(
                        db.session.query(StudentUnitSelection.unit_id).filter_by(student_id=student_id)
                    )
                ).order_by(CurriculumUnit.order_index).limit(max_recommendations).all()
                
                for unit in unstarted_units:
                    recommendations.append({
                        'item_id': unit.id,
                        'title': unit.title,
                        'description': f"基礎的な学習単元: {unit.description or '詳細なし'}",
                        'confidence_score': 0.6,
                        'reasoning': "まだ学習していない基礎単元です",
                        'estimated_time_minutes': unit.estimated_minutes,
                        'difficulty_level': unit.difficulty_level,
                        'recommendation_type': recommendation_type,
                        'generated_at': datetime.utcnow().isoformat()
                    })
            
            elif recommendation_type == 'review':
                # 低い正答率の科目から復習推薦
                weak_records = ProficiencyRecord.query.filter(
                    and_(
                        ProficiencyRecord.student_id == student_id,
                        ProficiencyRecord.accuracy_rate < 0.7,
                        ProficiencyRecord.total_attempted >= 3
                    )
                ).order_by(ProficiencyRecord.accuracy_rate).limit(max_recommendations).all()
                
                for record in weak_records:
                    recommendations.append({
                        'item_id': record.category_id,
                        'title': f"{record.category.name if record.category else '復習'} の復習",
                        'description': f"正答率 {record.accuracy_rate:.1%} の科目を復習しましょう",
                        'confidence_score': 0.7,
                        'reasoning': "正答率が低い分野の復習が必要です",
                        'estimated_time_minutes': 45,
                        'difficulty_level': 2,
                        'recommendation_type': recommendation_type,
                        'generated_at': datetime.utcnow().isoformat()
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"フォールバック推薦生成エラー: {str(e)}")
            return []
    
    def _save_recommendations(
        self, 
        student_id: int, 
        recommendations: List[Dict[str, Any]], 
        recommendation_type: str
    ):
        """推薦履歴をデータベースに保存"""
        try:
            ai_recommendation = AIRecommendation(
                student_id=student_id,
                recommendation_type=recommendation_type,
                context_data={
                    'generation_method': 'ai' if recommendations else 'fallback',
                    'recommendation_count': len(recommendations)
                },
                ai_model='gpt-4',
                ai_response="Generated recommendations",
                recommended_items=recommendations,
                confidence_score=sum(rec.get('confidence_score', 0.5) for rec in recommendations) / len(recommendations) if recommendations else 0.0,
                reasoning="AI-generated personalized recommendations based on learning patterns and performance data"
            )
            
            db.session.add(ai_recommendation)
            db.session.commit()
            
            logger.info(f"推薦履歴を保存 (学生ID: {student_id}, 推薦数: {len(recommendations)})")
            
        except Exception as e:
            logger.error(f"推薦履歴保存エラー: {str(e)}")
            db.session.rollback()
    
    def get_recommendation_feedback(
        self, 
        recommendation_id: int, 
        is_accepted: bool, 
        is_effective: Optional[bool] = None, 
        feedback_text: Optional[str] = None
    ):
        """推薦に対するフィードバックを記録"""
        try:
            recommendation = AIRecommendation.query.get(recommendation_id)
            if not recommendation:
                raise AIRecommendationError("推薦が見つかりません")
            
            recommendation.is_accepted = is_accepted
            recommendation.is_effective = is_effective
            recommendation.feedback_text = feedback_text
            recommendation.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"推薦フィードバックを記録 (ID: {recommendation_id})")
            
        except Exception as e:
            logger.error(f"推薦フィードバック記録エラー: {str(e)}")
            db.session.rollback()
            raise AIRecommendationError(f"フィードバック記録中にエラーが発生しました: {str(e)}")
    
    def update_recommendation_settings(
        self, 
        student_id: int, 
        settings_data: Dict[str, Any]
    ):
        """推薦設定を更新"""
        try:
            settings = RecommendationSettings.query.filter_by(student_id=student_id).first()
            if not settings:
                settings = RecommendationSettings(student_id=student_id)
                db.session.add(settings)
            
            # 設定を更新
            for key, value in settings_data.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
            
            settings.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"推薦設定を更新 (学生ID: {student_id})")
            
        except Exception as e:
            logger.error(f"推薦設定更新エラー: {str(e)}")
            db.session.rollback()
            raise AIRecommendationError(f"設定更新中にエラーが発生しました: {str(e)}")


class RecommendationAnalytics:
    """推薦システムの分析とメトリクス"""
    
    @staticmethod
    def get_recommendation_metrics(student_id: Optional[int] = None) -> Dict[str, Any]:
        """推薦システムのメトリクスを取得"""
        try:
            query = AIRecommendation.query
            if student_id:
                query = query.filter_by(student_id=student_id)
            
            recommendations = query.all()
            
            if not recommendations:
                return {
                    'total_recommendations': 0,
                    'acceptance_rate': 0.0,
                    'effectiveness_rate': 0.0,
                    'average_confidence': 0.0
                }
            
            total = len(recommendations)
            accepted = sum(1 for r in recommendations if r.is_accepted is True)
            effective = sum(1 for r in recommendations if r.is_effective is True)
            avg_confidence = sum(r.confidence_score for r in recommendations) / total
            
            return {
                'total_recommendations': total,
                'acceptance_rate': accepted / total if total > 0 else 0.0,
                'effectiveness_rate': effective / total if total > 0 else 0.0,
                'average_confidence': avg_confidence
            }
            
        except Exception as e:
            logger.error(f"推薦メトリクス取得エラー: {str(e)}")
            return {}