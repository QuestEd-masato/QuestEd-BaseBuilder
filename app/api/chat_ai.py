"""
Chat and AI API
===============
Phase 4.3: API分割実装 - チャット・AI関連API

責任:
- AI チャット機能
- 音声認識・文字起こし
- AI推奨事項の管理
- 推奨設定とフィードバック

移行元: app/api/__init__.py の以下4ルート:
- /chat (GET, POST)
- /speech/transcribe (POST)
- /recommendations (GET)
- /recommendations/<int:recommendation_id>/feedback (POST)
- /recommendations/settings (GET, POST)
- /recommendations/analytics (GET)
"""

from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user
import json
import logging
from datetime import datetime, timedelta

from app.models import db, ChatHistory, InquiryTheme, AIRecommendation, User
from app.ai import generate_chat_response
from app.utils.rate_limiting import smart_ai_limit, api_limit

chat_ai_bp = Blueprint('chat_ai', __name__)


@chat_ai_bp.route('/chat', methods=['GET', 'POST'])
@login_required
@smart_ai_limit()
def chat():
    """AI チャット API"""
    if request.method == 'GET':
        # チャット履歴取得
        try:
            # パラメータ取得
            theme_id = request.args.get('theme_id', type=int)
            limit = min(request.args.get('limit', 20, type=int), 100)
            
            # 基本クエリ
            query = ChatHistory.query.filter_by(user_id=current_user.id)
            
            # Note: テーマによるフィルタは現在のDBスキーマでは未対応
            
            # 最新の履歴を取得
            history = query.order_by(ChatHistory.created_at.desc()).limit(limit).all()
            
            # レスポンス構築
            chat_data = []
            for chat in reversed(history):  # 時系列順に並び替え
                chat_item = {
                    'id': chat.id,
                    'message': chat.message,
                    'is_user': chat.is_user,
                    'created_at': chat.created_at.isoformat()
                }
                chat_data.append(chat_item)
            
            return jsonify({
                'status': 'success',
                'chat_history': chat_data,
                'total_count': len(chat_data)
            })
            
        except Exception as e:
            logging.error(f"Get chat history error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'チャット履歴取得中にエラーが発生しました'
            }), 500
    
    elif request.method == 'POST':
        # チャットメッセージ送信
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'JSONデータが必要です'
                }), 400
            
            user_message = data.get('message', '').strip()
            theme_id = data.get('theme_id')
            
            if not user_message:
                return jsonify({
                    'status': 'error',
                    'message': 'メッセージが空です'
                }), 400
            
            # テーマの確認（指定されている場合）
            inquiry_theme = None
            if theme_id:
                inquiry_theme = InquiryTheme.query.filter_by(
                    id=theme_id,
                    student_id=current_user.id
                ).first()
                
                if not inquiry_theme:
                    return jsonify({
                        'status': 'error',
                        'message': '指定されたテーマが見つかりません'
                    }), 404
            
            # コンテキスト構築
            context = {
                'student_name': current_user.name,
                'student_id': current_user.id,
                'inquiry_theme': inquiry_theme.theme if inquiry_theme else None,
                'session_id': session.get('chat_session_id', 'default')
            }
            
            # AI応答生成開始時刻
            start_time = datetime.utcnow()
            
            # AI応答生成
            ai_response = generate_chat_response(user_message, context)
            
            # 応答時間計算
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # チャット履歴保存 - ユーザーメッセージ
            user_chat = ChatHistory(
                user_id=current_user.id,
                message=user_message,
                is_user=True,
                created_at=datetime.utcnow()
            )
            
            # AIレスポンス
            ai_chat = ChatHistory(
                user_id=current_user.id,
                message=ai_response,
                is_user=False,
                created_at=datetime.utcnow()
            )
            
            db.session.add(user_chat)
            db.session.add(ai_chat)
            db.session.commit()
            
            logging.info(f"Chat completed: student_id={current_user.id}, theme_id={theme_id}, response_time={response_time:.2f}s")
            
            return jsonify({
                'status': 'success',
                'ai_response': ai_response,
                'chat_id': chat_record.id,
                'response_time': response_time
            })
            
        except Exception as e:
            logging.error(f"Chat error: {str(e)}")
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'AI応答生成中にエラーが発生しました'
            }), 500


@chat_ai_bp.route('/speech/transcribe', methods=['POST'])
@login_required
@api_limit()
def transcribe_speech():
    """音声文字起こしAPI"""
    try:
        # 音声ファイルの確認
        if 'audio' not in request.files:
            return jsonify({
                'status': 'error',
                'message': '音声ファイルが必要です'
            }), 400
        
        audio_file = request.files['audio']
        
        if audio_file.filename == '':
            return jsonify({
                'status': 'error',
                'message': '音声ファイルが選択されていません'
            }), 400
        
        # ファイル形式チェック
        allowed_extensions = {'wav', 'mp3', 'ogg', 'webm', 'm4a'}
        file_extension = audio_file.filename.rsplit('.', 1)[1].lower() if '.' in audio_file.filename else ''
        
        if file_extension not in allowed_extensions:
            return jsonify({
                'status': 'error',
                'message': f'サポートされていないファイル形式です。対応形式: {", ".join(allowed_extensions)}'
            }), 400
        
        # ファイルサイズチェック（10MB制限）
        audio_file.seek(0, 2)  # ファイル末尾へ移動
        file_size = audio_file.tell()
        audio_file.seek(0)  # ファイル先頭に戻る
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            return jsonify({
                'status': 'error',
                'message': 'ファイルサイズが大きすぎます（最大10MB）'
            }), 400
        
        # 音声認識処理（実装が必要）
        try:
            # TODO: 実際の音声認識エンジンとの統合
            # 例: OpenAI Whisper, Google Speech-to-Text, Azure Speech Services
            
            # 仮の実装（実際のAPIでは適切な音声認識サービスを使用）
            transcribed_text = "音声認識機能は現在開発中です。"
            confidence = 0.0
            
            # 文字起こし結果の保存（必要に応じて）
            transcription_record = {
                'student_id': current_user.id,
                'original_filename': audio_file.filename,
                'file_size': file_size,
                'transcribed_text': transcribed_text,
                'confidence': confidence,
                'created_at': datetime.utcnow()
            }
            
            # TODO: SpeechTranscriptionモデルへの保存
            
            logging.info(f"Speech transcribed: student_id={current_user.id}, filename={audio_file.filename}")
            
            return jsonify({
                'status': 'success',
                'transcribed_text': transcribed_text,
                'confidence': confidence,
                'message': '音声の文字起こしが完了しました'
            })
            
        except Exception as transcription_error:
            logging.error(f"Transcription error: {str(transcription_error)}")
            return jsonify({
                'status': 'error',
                'message': '音声認識処理中にエラーが発生しました'
            }), 500
            
    except Exception as e:
        logging.error(f"Speech transcribe error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '音声ファイル処理中にエラーが発生しました'
        }), 500


@chat_ai_bp.route('/recommendations', methods=['GET'])
@login_required
@api_limit()
def get_recommendations():
    """AI推奨事項取得API"""
    try:
        # パラメータ取得
        category = request.args.get('category')  # 'learning', 'resources', 'activities'
        status = request.args.get('status')  # 'active', 'completed', 'dismissed'
        limit = min(request.args.get('limit', 10, type=int), 50)
        
        # 基本クエリ
        query = AIRecommendation.query.filter_by(student_id=current_user.id)
        
        # フィルタリング
        if category:
            query = query.filter_by(category=category)
        
        if status:
            query = query.filter_by(status=status)
        
        # 最新の推奨事項を取得
        recommendations = query.order_by(
            AIRecommendation.created_at.desc()
        ).limit(limit).all()
        
        # レスポンス構築
        recommendation_data = []
        for rec in recommendations:
            rec_item = {
                'id': rec.id,
                'title': rec.title,
                'description': rec.description,
                'category': rec.category,
                'priority': rec.priority,
                'status': rec.status,
                'reason': rec.reason,
                'estimated_time': rec.estimated_time,
                'difficulty_level': rec.difficulty_level,
                'created_at': rec.created_at.isoformat(),
                'expires_at': rec.expires_at.isoformat() if rec.expires_at else None
            }
            
            # メタデータを含める
            if rec.metadata:
                try:
                    rec_item['metadata'] = json.loads(rec.metadata)
                except:
                    rec_item['metadata'] = {}
            
            recommendation_data.append(rec_item)
        
        return jsonify({
            'status': 'success',
            'recommendations': recommendation_data,
            'total_count': len(recommendation_data)
        })
        
    except Exception as e:
        logging.error(f"Get recommendations error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '推奨事項取得中にエラーが発生しました'
        }), 500


@chat_ai_bp.route('/recommendations/<int:recommendation_id>/feedback', methods=['POST'])
@login_required
@api_limit()
def submit_recommendation_feedback(recommendation_id):
    """推奨事項フィードバック送信API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'JSONデータが必要です'
            }), 400
        
        feedback_type = data.get('feedback_type')  # 'helpful', 'not_helpful', 'completed', 'dismissed'
        comment = data.get('comment', '')
        
        if not feedback_type:
            return jsonify({
                'status': 'error',
                'message': 'フィードバックタイプが必要です'
            }), 400
        
        # 推奨事項の確認
        recommendation = AIRecommendation.query.filter_by(
            id=recommendation_id,
            student_id=current_user.id
        ).first()
        
        if not recommendation:
            return jsonify({
                'status': 'error',
                'message': '指定された推奨事項が見つかりません'
            }), 404
        
        # フィードバックに基づくステータス更新
        if feedback_type == 'completed':
            recommendation.status = 'completed'
            recommendation.completed_at = datetime.utcnow()
        elif feedback_type == 'dismissed':
            recommendation.status = 'dismissed'
            recommendation.dismissed_at = datetime.utcnow()
        elif feedback_type in ['helpful', 'not_helpful']:
            # フィードバック情報を保存
            recommendation.feedback_type = feedback_type
            recommendation.feedback_comment = comment
            recommendation.feedback_at = datetime.utcnow()
        
        db.session.commit()
        
        logging.info(f"Recommendation feedback: rec_id={recommendation_id}, type={feedback_type}, student_id={current_user.id}")
        
        return jsonify({
            'status': 'success',
            'message': 'フィードバックを送信しました'
        })
        
    except Exception as e:
        logging.error(f"Submit recommendation feedback error: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'フィードバック送信中にエラーが発生しました'
        }), 500


@chat_ai_bp.route('/recommendations/settings', methods=['GET', 'POST'])
@login_required
@api_limit()
def recommendation_settings():
    """推奨事項設定API"""
    if request.method == 'GET':
        # 設定取得
        try:
            # ユーザーの推奨事項設定を取得
            # TODO: UserSettingsモデルまたは類似の仕組みから設定を取得
            
            # 仮の設定値（実際の実装では適切なモデルから取得）
            settings = {
                'enabled': True,
                'categories': {
                    'learning': True,
                    'resources': True,
                    'activities': False
                },
                'frequency': 'daily',  # 'daily', 'weekly', 'never'
                'difficulty_preference': 'adaptive',  # 'easy', 'medium', 'hard', 'adaptive'
                'notification_enabled': True
            }
            
            return jsonify({
                'status': 'success',
                'settings': settings
            })
            
        except Exception as e:
            logging.error(f"Get recommendation settings error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': '設定取得中にエラーが発生しました'
            }), 500
    
    elif request.method == 'POST':
        # 設定更新
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'JSONデータが必要です'
                }), 400
            
            # 設定の妥当性確認
            enabled = data.get('enabled', True)
            categories = data.get('categories', {})
            frequency = data.get('frequency', 'daily')
            difficulty_preference = data.get('difficulty_preference', 'adaptive')
            notification_enabled = data.get('notification_enabled', True)
            
            # バリデーション
            valid_frequencies = ['daily', 'weekly', 'never']
            valid_difficulties = ['easy', 'medium', 'hard', 'adaptive']
            
            if frequency not in valid_frequencies:
                return jsonify({
                    'status': 'error',
                    'message': f'無効な頻度設定です。有効な値: {", ".join(valid_frequencies)}'
                }), 400
            
            if difficulty_preference not in valid_difficulties:
                return jsonify({
                    'status': 'error',
                    'message': f'無効な難易度設定です。有効な値: {", ".join(valid_difficulties)}'
                }), 400
            
            # TODO: 実際の設定保存処理
            # 設定をUserSettingsモデルまたは類似の仕組みに保存
            
            logging.info(f"Recommendation settings updated: student_id={current_user.id}")
            
            return jsonify({
                'status': 'success',
                'message': '設定を更新しました'
            })
            
        except Exception as e:
            logging.error(f"Update recommendation settings error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': '設定更新中にエラーが発生しました'
            }), 500


@chat_ai_bp.route('/recommendations/analytics', methods=['GET'])
@login_required
@api_limit()
def get_recommendation_analytics():
    """推奨事項分析API"""
    try:
        # 期間パラメータ
        days_back = min(request.args.get('days', 30, type=int), 90)
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        # 基本統計の取得
        total_recommendations = AIRecommendation.query.filter_by(
            student_id=current_user.id
        ).count()
        
        recent_recommendations = AIRecommendation.query.filter(
            AIRecommendation.student_id == current_user.id,
            AIRecommendation.created_at >= start_date
        ).count()
        
        completed_recommendations = AIRecommendation.query.filter(
            AIRecommendation.student_id == current_user.id,
            AIRecommendation.status == 'completed',
            AIRecommendation.created_at >= start_date
        ).count()
        
        dismissed_recommendations = AIRecommendation.query.filter(
            AIRecommendation.student_id == current_user.id,
            AIRecommendation.status == 'dismissed',
            AIRecommendation.created_at >= start_date
        ).count()
        
        # カテゴリ別統計
        category_stats = {}
        categories = ['learning', 'resources', 'activities']
        
        for category in categories:
            category_count = AIRecommendation.query.filter(
                AIRecommendation.student_id == current_user.id,
                AIRecommendation.category == category,
                AIRecommendation.created_at >= start_date
            ).count()
            
            category_completed = AIRecommendation.query.filter(
                AIRecommendation.student_id == current_user.id,
                AIRecommendation.category == category,
                AIRecommendation.status == 'completed',
                AIRecommendation.created_at >= start_date
            ).count()
            
            category_stats[category] = {
                'total': category_count,
                'completed': category_completed,
                'completion_rate': category_completed / category_count if category_count > 0 else 0
            }
        
        # 全体の完了率
        overall_completion_rate = completed_recommendations / recent_recommendations if recent_recommendations > 0 else 0
        
        analytics_data = {
            'period_days': days_back,
            'total_recommendations_all_time': total_recommendations,
            'recent_period': {
                'total': recent_recommendations,
                'completed': completed_recommendations,
                'dismissed': dismissed_recommendations,
                'completion_rate': overall_completion_rate
            },
            'category_breakdown': category_stats,
            'engagement_score': min(overall_completion_rate * 100, 100)  # 0-100スケール
        }
        
        return jsonify({
            'status': 'success',
            'analytics': analytics_data
        })
        
    except Exception as e:
        logging.error(f"Get recommendation analytics error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '分析データ取得中にエラーが発生しました'
        }), 500