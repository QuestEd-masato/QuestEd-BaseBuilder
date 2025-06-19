"""
音声入力管理サービス

Web Speech APIによる音声認識結果の管理と処理を行う
"""
import re
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from extensions import db
from app.models import (
    SpeechTranscription, User
)
# SpeechSettings, SpeechStatistics は RDSに存在しないためコメントアウト


class SpeechService:
    """音声入力管理サービス"""
    
    @staticmethod
    def record_transcription(student_id: int, session_id: str, 
                           original_text: str, confidence_score: float,
                           language_code: str = 'ja-JP', audio_duration: float = None,
                           input_context: str = 'chat', context_id: int = None) -> Dict:
        """
        音声認識結果を記録
        
        Args:
            student_id: 生徒ID
            session_id: セッションID
            original_text: 音声認識された原文
            confidence_score: 認識精度スコア
            language_code: 言語コード
            audio_duration: 音声の長さ（秒）
            input_context: 入力コンテキスト
            context_id: コンテキストに関連するID
            
        Returns:
            記録結果と処理されたテキスト
        """
        # 設定確認
        settings = SpeechService.get_settings(student_id)
        if not settings['is_enabled']:
            raise ValueError("音声入力が無効になっています")
        
        if confidence_score < settings['min_confidence']:
            raise ValueError(f"認識精度が不足しています（最低{settings['min_confidence']}必要）")
        
        # テキストクリーニング
        cleaned_text = SpeechService._clean_text(original_text, settings)
        
        # 記録作成
        transcription = SpeechTranscription(
            student_id=student_id,
            session_id=session_id,
            original_audio_text=original_text,
            cleaned_text=cleaned_text,
            confidence_score=confidence_score,
            language_code=language_code,
            audio_duration=audio_duration,
            input_context=input_context,
            context_id=context_id,
            is_processed=True
        )
        
        db.session.add(transcription)
        
        # 統計情報更新
        SpeechService._update_statistics(student_id, {
            'is_successful': True,
            'duration': audio_duration,
            'confidence_score': confidence_score,
            'context': input_context
        })
        
        db.session.commit()
        
        # 学習支援提案の生成
        suggestions = SpeechService._generate_suggestions(cleaned_text, input_context)
        
        return {
            'transcription_id': transcription.id,
            'cleaned_text': cleaned_text,
            'is_processed': True,
            'confidence_level': transcription.get_confidence_level(),
            'suggestions': suggestions
        }
    
    @staticmethod
    def get_transcription_history(student_id: int, limit: int = 20, offset: int = 0,
                                context: str = None, start_date: date = None, 
                                end_date: date = None) -> Dict:
        """
        音声入力履歴を取得
        
        Args:
            student_id: 生徒ID
            limit: 取得件数
            offset: オフセット
            context: 入力コンテキストでフィルタ
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            音声入力履歴
        """
        query = SpeechTranscription.query.filter_by(student_id=student_id)
        
        # コンテキストフィルタ
        if context:
            query = query.filter(SpeechTranscription.input_context == context)
        
        # 日付フィルタ
        if start_date:
            query = query.filter(SpeechTranscription.created_at >= start_date)
        if end_date:
            query = query.filter(SpeechTranscription.created_at <= end_date)
        
        # 総件数取得
        total = query.count()
        
        # ページング
        transcriptions = query.order_by(SpeechTranscription.created_at.desc())\
                              .offset(offset)\
                              .limit(limit)\
                              .all()
        
        return {
            'transcriptions': [t.to_dict() for t in transcriptions],
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_next': offset + limit < total
            }
        }
    
    @staticmethod
    def get_settings(student_id: int) -> Dict:
        """
        音声入力設定を取得
        
        Args:
            student_id: 生徒ID
            
        Returns:
            音声入力設定
        """
        settings = SpeechSettings.query.filter_by(student_id=student_id).first()
        
        if not settings:
            # デフォルト設定を作成
            settings = SpeechSettings(student_id=student_id)
            db.session.add(settings)
            db.session.commit()
        
        return settings.to_dict()
    
    @staticmethod
    def update_settings(student_id: int, settings_data: Dict) -> Dict:
        """
        音声入力設定を更新
        
        Args:
            student_id: 生徒ID
            settings_data: 更新する設定値
            
        Returns:
            更新後の設定
        """
        settings = SpeechSettings.query.filter_by(student_id=student_id).first()
        
        if not settings:
            settings = SpeechSettings(student_id=student_id)
            db.session.add(settings)
        
        # 設定値の更新
        settings.update_settings(**settings_data)
        db.session.commit()
        
        return settings.to_dict()
    
    @staticmethod
    def get_statistics(student_id: int, days: int = 30) -> Dict:
        """
        音声入力統計を取得
        
        Args:
            student_id: 生徒ID
            days: 過去何日分の統計を取得するか
            
        Returns:
            統計情報
        """
        end_date = date.today()
        start_date = date.fromordinal(end_date.toordinal() - days + 1)
        
        # 期間内の統計データを取得
        stats = SpeechStatistics.query.filter(
            SpeechStatistics.student_id == student_id,
            SpeechStatistics.date >= start_date,
            SpeechStatistics.date <= end_date
        ).order_by(SpeechStatistics.date).all()
        
        # 集計
        total_inputs = sum(s.total_inputs for s in stats)
        successful_inputs = sum(s.successful_inputs for s in stats)
        total_duration = sum(float(s.total_duration) for s in stats if s.total_duration)
        
        # 平均信頼度の計算
        confidence_scores = [float(s.average_confidence) for s in stats if s.average_confidence]
        average_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # 日別データ
        daily_data = [s.to_dict() for s in stats]
        
        # 最も使用されたコンテキスト
        context_usage = {}
        for stat in stats:
            if stat.most_used_context:
                context_usage[stat.most_used_context] = context_usage.get(stat.most_used_context, 0) + stat.total_inputs
        
        most_used_context = max(context_usage.items(), key=lambda x: x[1])[0] if context_usage else None
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'summary': {
                'total_inputs': total_inputs,
                'successful_inputs': successful_inputs,
                'success_rate': (successful_inputs / total_inputs * 100) if total_inputs > 0 else 0.0,
                'total_duration_seconds': total_duration,
                'average_confidence': average_confidence,
                'most_used_context': most_used_context
            },
            'daily_data': daily_data
        }
    
    @staticmethod
    def _clean_text(original_text: str, settings: Dict) -> str:
        """
        音声認識テキストをクリーニング
        
        Args:
            original_text: 元のテキスト
            settings: 音声設定
            
        Returns:
            クリーニング後のテキスト
        """
        if not original_text:
            return ""
        
        text = original_text.strip()
        
        # 自動句読点挿入
        if settings.get('auto_punctuation', True):
            # 文末に句点がない場合は追加
            if text and not text.endswith(('。', '！', '？', '.', '!', '?')):
                if re.search(r'[ぁ-んァ-ン一-龯]', text):  # 日本語を含む場合
                    text += '。'
                else:
                    text += '.'
        
        # 複数の空白を一つに統合
        text = re.sub(r'\s+', ' ', text)
        
        # 不要な文字を除去
        text = re.sub(r'[^\w\s\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF。！？、.,!?]', '', text)
        
        return text.strip()
    
    @staticmethod
    def _update_statistics(student_id: int, transcription_data: Dict):
        """
        音声入力統計を更新
        
        Args:
            student_id: 生徒ID
            transcription_data: 音声認識データ
        """
        stat = SpeechStatistics.get_or_create_today(student_id)
        stat.update_statistics(transcription_data)
        
        # 最も使用されたコンテキストの更新
        if transcription_data.get('context'):
            # 簡易実装：今日のコンテキスト使用回数を記録
            # 本格実装では別テーブルで管理することを推奨
            stat.most_used_context = transcription_data['context']
    
    @staticmethod
    def _generate_suggestions(text: str, context: str) -> List[str]:
        """
        音声入力テキストから学習支援提案を生成
        
        Args:
            text: クリーニング済みテキスト
            context: 入力コンテキスト
            
        Returns:
            提案リスト
        """
        suggestions = []
        
        # キーワード抽出による提案
        if context == 'activity_log':
            # 理科関連キーワード
            science_keywords = {
                '電流': ['電気回路', 'オームの法則', '電圧'],
                '電圧': ['電気回路', '電流', '抵抗'],
                '磁場': ['電磁気学', '磁力', '電磁誘導'],
                '光': ['光学', '反射', '屈折'],
                '音': ['音波', '振動', '周波数'],
                '力': ['力学', '運動', '加速度']
            }
            
            for keyword, related in science_keywords.items():
                if keyword in text:
                    suggestions.extend(related)
        
        elif context == 'chat':
            # 質問形式の検出
            if '?' in text or '？' in text or 'なぜ' in text or 'どうして' in text:
                suggestions.append('詳しく調べてみる')
                suggestions.append('関連問題に挑戦')
        
        # 重複除去と最大5個まで
        return list(set(suggestions))[:5]
    
    @staticmethod
    def record_error(student_id: int, session_id: str, error_message: str,
                    input_context: str = 'unknown') -> int:
        """
        音声入力エラーを記録
        
        Args:
            student_id: 生徒ID
            session_id: セッションID
            error_message: エラーメッセージ
            input_context: 入力コンテキスト
            
        Returns:
            記録ID
        """
        transcription = SpeechTranscription(
            student_id=student_id,
            session_id=session_id,
            original_audio_text="",
            cleaned_text="",
            confidence_score=0.0,
            input_context=input_context,
            is_processed=False,
            error_message=error_message
        )
        
        db.session.add(transcription)
        
        # 統計情報更新（失敗として記録）
        SpeechService._update_statistics(student_id, {
            'is_successful': False,
            'context': input_context
        })
        
        db.session.commit()
        
        return transcription.id
    
    @staticmethod
    def get_session_transcriptions(session_id: str) -> List[Dict]:
        """
        セッション内の音声入力履歴を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            セッション内の音声入力履歴
        """
        transcriptions = SpeechTranscription.query.filter_by(
            session_id=session_id
        ).order_by(SpeechTranscription.created_at).all()
        
        return [t.to_dict() for t in transcriptions]
    
    @staticmethod
    def validate_audio_duration(duration: float, max_duration: int = 300) -> bool:
        """
        音声時間の妥当性をチェック
        
        Args:
            duration: 音声時間（秒）
            max_duration: 最大許可時間（秒）
            
        Returns:
            妥当性
        """
        return 0 < duration <= max_duration
    
    @staticmethod
    def get_usage_analytics(student_id: int) -> Dict:
        """
        音声入力の使用分析データを取得
        
        Args:
            student_id: 生徒ID
            
        Returns:
            使用分析データ
        """
        # 過去30日間のデータ
        stats_30days = SpeechService.get_statistics(student_id, 30)
        
        # コンテキスト別使用状況
        context_query = db.session.query(
            SpeechTranscription.input_context,
            db.func.count(SpeechTranscription.id).label('count'),
            db.func.avg(SpeechTranscription.confidence_score).label('avg_confidence')
        ).filter(
            SpeechTranscription.student_id == student_id,
            SpeechTranscription.created_at >= datetime.now().replace(day=1)  # 今月
        ).group_by(SpeechTranscription.input_context).all()
        
        context_stats = [
            {
                'context': row.input_context,
                'usage_count': row.count,
                'average_confidence': float(row.avg_confidence) if row.avg_confidence else 0.0
            }
            for row in context_query
        ]
        
        # 時間帯別使用傾向
        time_query = db.session.query(
            db.func.extract('hour', SpeechTranscription.created_at).label('hour'),
            db.func.count(SpeechTranscription.id).label('count')
        ).filter(
            SpeechTranscription.student_id == student_id,
            SpeechTranscription.created_at >= datetime.now().replace(day=1)
        ).group_by(db.func.extract('hour', SpeechTranscription.created_at)).all()
        
        time_stats = [
            {
                'hour': int(row.hour),
                'usage_count': row.count
            }
            for row in time_query
        ]
        
        return {
            'monthly_summary': stats_30days['summary'],
            'context_usage': context_stats,
            'time_distribution': time_stats,
            'improvement_suggestions': SpeechService._generate_improvement_suggestions(
                stats_30days['summary'], context_stats
            )
        }
    
    @staticmethod
    def _generate_improvement_suggestions(summary: Dict, context_stats: List[Dict]) -> List[str]:
        """
        音声入力改善提案を生成
        
        Args:
            summary: 統計サマリー
            context_stats: コンテキスト別統計
            
        Returns:
            改善提案リスト
        """
        suggestions = []
        
        # 成功率による提案
        success_rate = summary.get('success_rate', 0)
        if success_rate < 70:
            suggestions.append("静かな環境での音声入力を心がけましょう")
            suggestions.append("マイクに近づいてゆっくり話してみてください")
        
        # 平均信頼度による提案
        avg_confidence = summary.get('average_confidence', 0)
        if avg_confidence < 0.7:
            suggestions.append("はっきりとした発音を意識してみてください")
        
        # 使用頻度による提案
        total_inputs = summary.get('total_inputs', 0)
        if total_inputs < 10:
            suggestions.append("音声入力をもっと活用して学習効率を向上させましょう")
        
        return suggestions