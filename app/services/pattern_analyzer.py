"""
学習パターン分析サービス
学生の学習行動と傾向を分析してAI推薦エンジンにデータを提供する
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, time
from collections import defaultdict, Counter
import json
import statistics
from sqlalchemy import and_, or_, func
from app.models import (
    User, StudentUnitSelection, ChatHistory, 
    ActivityLog, AIRecommendation, CurriculumUnit, Subject
)
# LearningPattern は RDSに存在しないためコメントアウト
from app.services.base_service import BaseService
from app import db


class PatternAnalyzerService(BaseService):
    """学習パターン分析のメインサービス"""
    
    def __init__(self):
        super().__init__()
        self.time_analyzer = TimePreferenceAnalyzer()
        self.difficulty_analyzer = DifficultyPreferenceAnalyzer()
        self.subject_analyzer = SubjectStrengthAnalyzer()
        self.style_analyzer = LearningStyleAnalyzer()
    
    def _has_permission(self, user, action: str, resource: Any = None) -> bool:
        """権限チェック"""
        if user.role == 'admin':
            return True
        
        if action == 'read':
            if user.role == 'teacher':
                # 教師は自分の学校の生徒のみ分析可能
                if resource and hasattr(resource, 'school_id'):
                    return resource.school_id == user.school_id
                return True
            return resource == user  # 生徒は自分のみ
        
        return user.role in ['admin', 'teacher']
    
    def analyze_student_patterns(self, student_id: int, requester=None) -> Dict[str, Any]:
        """学生の全パターンを分析"""
        student = User.query.get(student_id)
        if not student:
            raise ValueError(f"Student with id {student_id} not found")
        
        if requester:
            self.validate_permissions(requester, 'read', student)
        
        results = {}
        
        # 各パターンを分析
        try:
            results['time_preference'] = self.time_analyzer.analyze(student_id)
            results['difficulty_preference'] = self.difficulty_analyzer.analyze(student_id)
            results['subject_strength'] = self.subject_analyzer.analyze(student_id)
            results['learning_style'] = self.style_analyzer.analyze(student_id)
            
            # 結果をデータベースに保存
            self._save_patterns(student_id, results)
            
            return {
                'student_id': student_id,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'patterns': results,
                'overall_confidence': self._calculate_overall_confidence(results)
            }
            
        except Exception as e:
            print(f"Error analyzing patterns for student {student_id}: {str(e)}")
            return {
                'student_id': student_id,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'patterns': {},
                'error': str(e)
            }
    
    def get_student_patterns(self, student_id: int, requester=None) -> Dict[str, Any]:
        """学生の保存されたパターンを取得"""
        student = User.query.get(student_id)
        if not student:
            raise ValueError(f"Student with id {student_id} not found")
        
        if requester:
            self.validate_permissions(requester, 'read', student)
        
        patterns = LearningPattern.query.filter_by(student_id=student_id, is_active=True).all()
        
        result = {
            'student_id': student_id,
            'patterns': {},
            'last_updated': None
        }
        
        for pattern in patterns:
            result['patterns'][pattern.pattern_type] = {
                'data': pattern.pattern_data,
                'confidence': float(pattern.confidence_level),
                'sample_size': pattern.sample_size,
                'last_analyzed': pattern.last_analyzed_at.isoformat() if pattern.last_analyzed_at else None
            }
            
            # 最新の更新日時を記録
            if not result['last_updated'] or pattern.last_analyzed_at > datetime.fromisoformat(result['last_updated']):
                result['last_updated'] = pattern.last_analyzed_at.isoformat()
        
        return result
    
    def _save_patterns(self, student_id: int, patterns: Dict[str, Any]):
        """パターン分析結果をデータベースに保存"""
        for pattern_type, data in patterns.items():
            if not data or 'confidence' not in data:
                continue
            
            # 既存のパターンを更新または新規作成
            pattern = LearningPattern.query.filter_by(
                student_id=student_id,
                pattern_type=pattern_type
            ).first()
            
            if pattern:
                pattern.pattern_data = data['data']
                pattern.confidence_level = data['confidence']
                pattern.sample_size = data.get('sample_size', 0)
                pattern.last_analyzed_at = datetime.utcnow()
                pattern.updated_at = datetime.utcnow()
            else:
                pattern = LearningPattern(
                    student_id=student_id,
                    pattern_type=pattern_type,
                    pattern_data=data['data'],
                    confidence_level=data['confidence'],
                    sample_size=data.get('sample_size', 0),
                    last_analyzed_at=datetime.utcnow()
                )
                db.session.add(pattern)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
    
    def _calculate_overall_confidence(self, patterns: Dict[str, Any]) -> float:
        """全体的な信頼度を計算"""
        confidences = []
        for pattern_data in patterns.values():
            if pattern_data and 'confidence' in pattern_data:
                confidences.append(pattern_data['confidence'])
        
        if not confidences:
            return 0.0
        
        return statistics.mean(confidences)


class TimePreferenceAnalyzer:
    """時間帯別学習傾向分析"""
    
    def analyze(self, student_id: int) -> Dict[str, Any]:
        """学生の時間帯別学習傾向を分析"""
        
        # 学習活動データを取得（過去30日間）
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # 単元学習データ
        unit_activities = StudentUnitSelection.query.filter(
            and_(
                StudentUnitSelection.student_id == student_id,
                StudentUnitSelection.last_activity_at >= cutoff_date,
                StudentUnitSelection.last_activity_at.isnot(None)
            )
        ).all()
        
        # チャット活動データ
        chat_activities = ChatHistory.query.filter(
            and_(
                ChatHistory.user_id == student_id,
                ChatHistory.timestamp >= cutoff_date,
                ChatHistory.is_user == True
            )
        ).all()
        
        # 活動記録データ
        activity_logs = ActivityLog.query.filter(
            and_(
                ActivityLog.student_id == student_id,
                ActivityLog.timestamp >= cutoff_date
            )
        ).all()
        
        if not unit_activities and not chat_activities and not activity_logs:
            return self._insufficient_data_response()
        
        # 時間帯別活動量を分析
        hourly_activity = defaultdict(int)
        total_activities = 0
        
        # 単元学習の時間帯を分析
        for activity in unit_activities:
            hour = activity.last_activity_at.hour
            hourly_activity[hour] += activity.study_time_minutes or 1
            total_activities += 1
        
        # チャット活動の時間帯を分析
        for chat in chat_activities:
            hour = chat.timestamp.hour
            hourly_activity[hour] += 1
            total_activities += 1
        
        # 活動記録の時間帯を分析
        for log in activity_logs:
            hour = log.timestamp.hour
            hourly_activity[hour] += 1
            total_activities += 1
        
        if total_activities == 0:
            return self._insufficient_data_response()
        
        # 時間帯別傾向を計算
        time_periods = {
            'morning': list(range(6, 12)),      # 6:00-11:59
            'afternoon': list(range(12, 18)),   # 12:00-17:59
            'evening': list(range(18, 22)),     # 18:00-21:59
            'night': list(range(22, 24)) + list(range(0, 6))  # 22:00-5:59
        }
        
        period_scores = {}
        for period, hours in time_periods.items():
            period_activity = sum(hourly_activity[hour] for hour in hours)
            period_scores[period] = period_activity / total_activities
        
        # 最も活発な時間帯を特定
        preferred_period = max(period_scores, key=period_scores.get)
        
        # 信頼度を計算（データ量とばらつきに基づく）
        confidence = min(total_activities / 50.0, 1.0)  # 50活動で最大信頼度
        if max(period_scores.values()) < 0.4:  # 特定の時間帯に偏りがない場合は信頼度を下げる
            confidence *= 0.7
        
        return {
            'data': {
                'preferred_period': preferred_period,
                'period_scores': period_scores,
                'hourly_distribution': dict(hourly_activity),
                'peak_hours': self._find_peak_hours(hourly_activity)
            },
            'confidence': round(confidence, 2),
            'sample_size': total_activities,
            'analysis_date': datetime.utcnow().isoformat()
        }
    
    def _find_peak_hours(self, hourly_activity: Dict[int, int]) -> List[int]:
        """最も活発な時間を特定"""
        if not hourly_activity:
            return []
        
        max_activity = max(hourly_activity.values())
        peak_hours = [hour for hour, activity in hourly_activity.items() 
                     if activity >= max_activity * 0.8]
        return sorted(peak_hours)
    
    def _insufficient_data_response(self) -> Dict[str, Any]:
        """データ不足時のレスポンス"""
        return {
            'data': {
                'preferred_period': None,
                'period_scores': {},
                'message': 'データが不足しています'
            },
            'confidence': 0.0,
            'sample_size': 0,
            'analysis_date': datetime.utcnow().isoformat()
        }


class DifficultyPreferenceAnalyzer:
    """難易度別学習傾向分析"""
    
    def analyze(self, student_id: int) -> Dict[str, Any]:
        """学生の難易度別学習傾向を分析"""
        
        # 過去60日間の学習データを取得
        cutoff_date = datetime.utcnow() - timedelta(days=60)
        
        # 単元学習データと難易度情報を結合して取得
        query = db.session.query(
            StudentUnitSelection,
            CurriculumUnit.difficulty_level,
            CurriculumUnit.estimated_minutes
        ).join(
            CurriculumUnit,
            StudentUnitSelection.unit_id == CurriculumUnit.id
        ).filter(
            and_(
                StudentUnitSelection.student_id == student_id,
                StudentUnitSelection.started_at >= cutoff_date,
                StudentUnitSelection.started_at.isnot(None)
            )
        ).all()
        
        if not query:
            return self._insufficient_data_response()
        
        # 難易度別のパフォーマンスを分析
        difficulty_stats = defaultdict(lambda: {
            'attempts': 0,
            'completed': 0,
            'total_time': 0,
            'progress_sum': 0,
            'correct_rate': 0
        })
        
        total_attempts = 0
        
        for selection, difficulty, estimated_time in query:
            difficulty_stats[difficulty]['attempts'] += 1
            total_attempts += 1
            
            if selection.status == 'completed':
                difficulty_stats[difficulty]['completed'] += 1
            
            difficulty_stats[difficulty]['total_time'] += selection.study_time_minutes or 0
            difficulty_stats[difficulty]['progress_sum'] += float(selection.progress_percentage or 0)
            
            # 正答率を計算
            if selection.total_items and selection.total_items > 0:
                correct_rate = (selection.correct_items or 0) / selection.total_items
                difficulty_stats[difficulty]['correct_rate'] += correct_rate
        
        # 難易度別スコアを計算
        difficulty_scores = {}
        preferred_difficulty = None
        max_score = 0
        
        for difficulty, stats in difficulty_stats.items():
            if stats['attempts'] == 0:
                continue
            
            completion_rate = stats['completed'] / stats['attempts']
            avg_progress = stats['progress_sum'] / stats['attempts']
            avg_correct_rate = stats['correct_rate'] / stats['attempts'] if stats['attempts'] > 0 else 0
            
            # 総合スコア = 完了率 * 0.4 + 進捗率 * 0.3 + 正答率 * 0.3
            score = (completion_rate * 0.4 + avg_progress / 100 * 0.3 + avg_correct_rate * 0.3)
            
            difficulty_scores[f'level_{difficulty}'] = {
                'score': round(score, 3),
                'completion_rate': round(completion_rate, 3),
                'avg_progress': round(avg_progress, 2),
                'avg_correct_rate': round(avg_correct_rate, 3),
                'attempts': stats['attempts'],
                'total_time': stats['total_time']
            }
            
            if score > max_score:
                max_score = score
                preferred_difficulty = difficulty
        
        # 信頼度を計算
        confidence = min(total_attempts / 20.0, 1.0)  # 20試行で最大信頼度
        
        # 難易度間のスコア差が小さい場合は信頼度を下げる
        if len(difficulty_scores) > 1:
            scores = [data['score'] for data in difficulty_scores.values()]
            if max(scores) - min(scores) < 0.2:
                confidence *= 0.7
        
        return {
            'data': {
                'preferred_difficulty': preferred_difficulty,
                'difficulty_scores': difficulty_scores,
                'recommendation': self._generate_difficulty_recommendation(preferred_difficulty, difficulty_scores)
            },
            'confidence': round(confidence, 2),
            'sample_size': total_attempts,
            'analysis_date': datetime.utcnow().isoformat()
        }
    
    def _generate_difficulty_recommendation(self, preferred_difficulty: Optional[int], 
                                          difficulty_scores: Dict[str, Any]) -> str:
        """難易度推薦メッセージを生成"""
        if not preferred_difficulty:
            return "十分なデータがありません"
        
        if preferred_difficulty == 1:
            return "基礎レベルの問題で確実に理解を深めることをお勧めします"
        elif preferred_difficulty == 2:
            return "標準レベルの問題が適切です。着実に学習を進めましょう"
        elif preferred_difficulty == 3:
            return "応用レベルの問題にチャレンジしてスキルアップを図りましょう"
        else:
            return "あなたのレベルに合わせた問題を提供します"
    
    def _insufficient_data_response(self) -> Dict[str, Any]:
        """データ不足時のレスポンス"""
        return {
            'data': {
                'preferred_difficulty': None,
                'difficulty_scores': {},
                'message': 'データが不足しています'
            },
            'confidence': 0.0,
            'sample_size': 0,
            'analysis_date': datetime.utcnow().isoformat()
        }


class SubjectStrengthAnalyzer:
    """科目別強み分析"""
    
    def analyze(self, student_id: int) -> Dict[str, Any]:
        """学生の科目別強みを分析"""
        
        # 過去90日間のデータを取得
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        # 科目別の学習データを取得
        subject_activities = db.session.query(
            ChatHistory.subject_id,
            Subject.name,
            func.count(ChatHistory.id).label('chat_count')
        ).join(
            Subject,
            ChatHistory.subject_id == Subject.id
        ).filter(
            and_(
                ChatHistory.user_id == student_id,
                ChatHistory.timestamp >= cutoff_date,
                ChatHistory.subject_id.isnot(None)
            )
        ).group_by(ChatHistory.subject_id, Subject.name).all()
        
        # 活動記録から科目関連のタグを分析
        activity_logs = ActivityLog.query.filter(
            and_(
                ActivityLog.student_id == student_id,
                ActivityLog.timestamp >= cutoff_date,
                ActivityLog.tags.isnot(None)
            )
        ).all()
        
        if not subject_activities and not activity_logs:
            return self._insufficient_data_response()
        
        # 科目別スコアリング
        subject_scores = defaultdict(lambda: {
            'activity_count': 0,
            'engagement_score': 0,
            'consistency_score': 0
        })
        
        total_activities = 0
        
        # チャット履歴から科目別活動量を集計
        for subject_id, subject_name, chat_count in subject_activities:
            subject_scores[subject_name]['activity_count'] += chat_count
            total_activities += chat_count
        
        # 活動記録のタグから科目関連性を分析
        for log in activity_logs:
            if log.tags:
                tags = log.tags.split(',')
                for tag in tags:
                    tag = tag.strip().lower()
                    # 科目関連のタグをマッピング
                    subject = self._map_tag_to_subject(tag)
                    if subject:
                        subject_scores[subject]['activity_count'] += 1
                        total_activities += 1
        
        if total_activities == 0:
            return self._insufficient_data_response()
        
        # 科目別の相対スコアを計算
        final_scores = {}
        for subject, data in subject_scores.items():
            if data['activity_count'] > 0:
                # 活動量の相対スコア
                activity_ratio = data['activity_count'] / total_activities
                
                # エンゲージメントスコア（仮の計算）
                engagement = min(data['activity_count'] / 10.0, 1.0)
                
                final_scores[subject] = {
                    'strength_score': round(activity_ratio * 0.7 + engagement * 0.3, 3),
                    'activity_count': data['activity_count'],
                    'activity_ratio': round(activity_ratio, 3)
                }
        
        # 最強の科目を特定
        strongest_subject = max(final_scores, key=lambda x: final_scores[x]['strength_score']) if final_scores else None
        
        # 信頼度を計算
        confidence = min(total_activities / 30.0, 1.0)  # 30活動で最大信頼度
        
        return {
            'data': {
                'strongest_subject': strongest_subject,
                'subject_scores': final_scores,
                'recommendations': self._generate_subject_recommendations(final_scores)
            },
            'confidence': round(confidence, 2),
            'sample_size': total_activities,
            'analysis_date': datetime.utcnow().isoformat()
        }
    
    def _map_tag_to_subject(self, tag: str) -> Optional[str]:
        """タグを科目にマッピング"""
        subject_mappings = {
            'math': '数学',
            'mathematics': '数学',
            'science': '理科',
            'physics': '物理',
            'chemistry': '化学',
            'biology': '生物',
            'english': '英語',
            'japanese': '国語',
            'history': '歴史',
            'geography': '地理',
            'art': '美術',
            'music': '音楽',
            'pe': '体育',
            'programming': 'プログラミング',
            'computer': 'コンピュータ'
        }
        
        for key, subject in subject_mappings.items():
            if key in tag:
                return subject
        return None
    
    def _generate_subject_recommendations(self, subject_scores: Dict[str, Any]) -> List[str]:
        """科目別推薦を生成"""
        if not subject_scores:
            return ["様々な科目に取り組んでみましょう"]
        
        recommendations = []
        sorted_subjects = sorted(subject_scores.items(), 
                               key=lambda x: x[1]['strength_score'], 
                               reverse=True)
        
        if len(sorted_subjects) >= 1:
            strongest = sorted_subjects[0][0]
            recommendations.append(f"{strongest}が得意科目のようです。さらに深く学習を進めましょう")
        
        if len(sorted_subjects) >= 2:
            second = sorted_subjects[1][0]
            recommendations.append(f"{second}も興味があるようです。バランス良く学習を続けましょう")
        
        return recommendations
    
    def _insufficient_data_response(self) -> Dict[str, Any]:
        """データ不足時のレスポンス"""
        return {
            'data': {
                'strongest_subject': None,
                'subject_scores': {},
                'message': 'データが不足しています'
            },
            'confidence': 0.0,
            'sample_size': 0,
            'analysis_date': datetime.utcnow().isoformat()
        }


class LearningStyleAnalyzer:
    """学習スタイル分析"""
    
    def analyze(self, student_id: int) -> Dict[str, Any]:
        """学生の学習スタイルを分析"""
        
        # 過去60日間のデータを取得
        cutoff_date = datetime.utcnow() - timedelta(days=60)
        
        # セッション持続時間の分析
        unit_sessions = StudentUnitSelection.query.filter(
            and_(
                StudentUnitSelection.student_id == student_id,
                StudentUnitSelection.started_at >= cutoff_date,
                StudentUnitSelection.study_time_minutes.isnot(None),
                StudentUnitSelection.study_time_minutes > 0
            )
        ).all()
        
        # チャットセッションの分析
        chat_sessions = self._analyze_chat_sessions(student_id, cutoff_date)
        
        if not unit_sessions and not chat_sessions:
            return self._insufficient_data_response()
        
        # セッション時間の分析
        session_times = []
        
        for session in unit_sessions:
            session_times.append(session.study_time_minutes)
        
        for session_time in chat_sessions:
            session_times.append(session_time)
        
        if not session_times:
            return self._insufficient_data_response()
        
        # 学習スタイルの特徴を分析
        avg_session_time = statistics.mean(session_times)
        median_session_time = statistics.median(session_times)
        
        # 学習パターンの分類
        learning_style = self._classify_learning_style(avg_session_time, session_times)
        
        # 学習頻度の分析
        learning_frequency = self._analyze_learning_frequency(student_id, cutoff_date)
        
        # 学習の一貫性分析
        consistency_score = self._calculate_consistency(student_id, cutoff_date)
        
        # 信頼度を計算
        confidence = min(len(session_times) / 15.0, 1.0)  # 15セッションで最大信頼度
        
        return {
            'data': {
                'primary_style': learning_style,
                'session_stats': {
                    'avg_session_minutes': round(avg_session_time, 1),
                    'median_session_minutes': round(median_session_time, 1),
                    'total_sessions': len(session_times),
                    'session_range': {
                        'min': min(session_times),
                        'max': max(session_times)
                    }
                },
                'learning_frequency': learning_frequency,
                'consistency_score': consistency_score,
                'recommendations': self._generate_style_recommendations(learning_style, avg_session_time)
            },
            'confidence': round(confidence, 2),
            'sample_size': len(session_times),
            'analysis_date': datetime.utcnow().isoformat()
        }
    
    def _analyze_chat_sessions(self, student_id: int, cutoff_date: datetime) -> List[int]:
        """チャットセッション時間を分析"""
        chats = ChatHistory.query.filter(
            and_(
                ChatHistory.user_id == student_id,
                ChatHistory.timestamp >= cutoff_date,
                ChatHistory.is_user == True
            )
        ).order_by(ChatHistory.timestamp).all()
        
        if not chats:
            return []
        
        sessions = []
        current_session_start = chats[0].timestamp
        last_timestamp = chats[0].timestamp
        
        for chat in chats[1:]:
            time_diff = (chat.timestamp - last_timestamp).total_seconds() / 60  # 分単位
            
            if time_diff > 30:  # 30分以上空いたら新しいセッション
                session_duration = (last_timestamp - current_session_start).total_seconds() / 60
                if session_duration > 1:  # 1分以上のセッションのみ記録
                    sessions.append(int(session_duration))
                current_session_start = chat.timestamp
            
            last_timestamp = chat.timestamp
        
        # 最後のセッションを追加
        final_duration = (last_timestamp - current_session_start).total_seconds() / 60
        if final_duration > 1:
            sessions.append(int(final_duration))
        
        return sessions
    
    def _classify_learning_style(self, avg_time: float, session_times: List[int]) -> str:
        """学習スタイルを分類"""
        if avg_time < 15:
            return "短時間集中型"
        elif avg_time < 45:
            return "標準学習型"
        elif avg_time < 90:
            return "長時間集中型"
        else:
            return "深い学習型"
    
    def _analyze_learning_frequency(self, student_id: int, cutoff_date: datetime) -> Dict[str, Any]:
        """学習頻度を分析"""
        # 日別の学習日数を計算
        learning_days = db.session.query(
            func.date(StudentUnitSelection.last_activity_at).label('date')
        ).filter(
            and_(
                StudentUnitSelection.student_id == student_id,
                StudentUnitSelection.last_activity_at >= cutoff_date
            )
        ).distinct().count()
        
        total_days = (datetime.utcnow() - cutoff_date).days
        frequency_rate = learning_days / total_days if total_days > 0 else 0
        
        if frequency_rate >= 0.8:
            frequency_type = "毎日型"
        elif frequency_rate >= 0.5:
            frequency_type = "定期型"
        elif frequency_rate >= 0.3:
            frequency_type = "不定期型"
        else:
            frequency_type = "散発型"
        
        return {
            'type': frequency_type,
            'learning_days': learning_days,
            'total_days': total_days,
            'frequency_rate': round(frequency_rate, 3)
        }
    
    def _calculate_consistency(self, student_id: int, cutoff_date: datetime) -> float:
        """学習の一貫性を計算"""
        # 週ごとの学習時間のばらつきを計算
        weekly_times = defaultdict(int)
        
        activities = StudentUnitSelection.query.filter(
            and_(
                StudentUnitSelection.student_id == student_id,
                StudentUnitSelection.last_activity_at >= cutoff_date,
                StudentUnitSelection.study_time_minutes.isnot(None)
            )
        ).all()
        
        for activity in activities:
            week_key = activity.last_activity_at.strftime('%Y-%W')
            weekly_times[week_key] += activity.study_time_minutes or 0
        
        if len(weekly_times) < 2:
            return 0.5  # デフォルト値
        
        times = list(weekly_times.values())
        if not times or statistics.mean(times) == 0:
            return 0.0
        
        # 変動係数を使用（標準偏差/平均）
        cv = statistics.stdev(times) / statistics.mean(times)
        consistency = max(0, 1 - cv)  # 変動が小さいほど一貫性が高い
        
        return round(consistency, 3)
    
    def _generate_style_recommendations(self, style: str, avg_time: float) -> List[str]:
        """スタイル別推薦を生成"""
        recommendations = []
        
        if style == "短時間集中型":
            recommendations.append("短時間で集中して学習するスタイルが向いています")
            recommendations.append("ポモドーロテクニックを活用してみましょう")
        elif style == "標準学習型":
            recommendations.append("バランスの取れた学習時間で着実に進めましょう")
            recommendations.append("定期的な復習を心がけましょう")
        elif style == "長時間集中型":
            recommendations.append("じっくりと時間をかけて学習することが得意です")
            recommendations.append("適度な休憩を取りながら効率を維持しましょう")
        else:
            recommendations.append("深く学習に取り組む姿勢が素晴らしいです")
            recommendations.append("疲労に注意して持続可能な学習を心がけましょう")
        
        return recommendations
    
    def _insufficient_data_response(self) -> Dict[str, Any]:
        """データ不足時のレスポンス"""
        return {
            'data': {
                'primary_style': None,
                'session_stats': {},
                'message': 'データが不足しています'
            },
            'confidence': 0.0,
            'sample_size': 0,
            'analysis_date': datetime.utcnow().isoformat()
        }