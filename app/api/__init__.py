# app/api/__init__.py
from flask import Blueprint, jsonify, request, session, make_response
from flask_login import login_required, current_user
import json
import logging
from datetime import datetime

from app.models import (db, ChatHistory, InquiryTheme, Class, ClassEnrollment, StudentEvaluation, User, Subject,
                      CurriculumUnit, StudentUnitSelection, UnitItemMapping, ClassLearningSettings,
                      AIRecommendation, ReviewSet, ReviewSetItem, StudentWeakness, School, Ranking, RankingCache)
from app.ai import generate_chat_response
from app.utils.rate_limiting import smart_ai_limit, api_limit

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/chat', methods=['GET', 'POST'])
@login_required
@smart_ai_limit()
def chat():
    """チャットAPIエンドポイント - AIチャット応答を生成"""
    # GETリクエストの場合はエラーを返す
    if request.method == 'GET':
        return jsonify({"error": "このエンドポイントはPOSTメソッドのみ対応しています"}), 405
    
    try:
        # リクエストデータを取得
        if request.is_json:
            data = request.get_json()
            message = data.get('message', '')
            step_id = data.get('step', '')
            function_id = data.get('function', '')
            class_id = data.get('class_id')
        else:
            # フォームデータの場合
            message = request.form.get('message', '')
            step_id = request.form.get('step', '')
            function_id = request.form.get('function', '')
            class_id = request.form.get('class_id', type=int)
        
        # 教師ロールの場合は常に teacher_free ステップを使用
        if current_user.role == 'teacher':
            step_id = 'teacher_free'
            function_id = ''
        
        # メッセージが空でないことを確認
        if not message:
            return jsonify({"error": "メッセージが空です"}), 400
        
        # クラスと教科情報を取得
        class_obj = None
        subject = None
        if class_id:
            class_obj = Class.query.get(class_id)
            if class_obj and class_obj.subject_id:
                subject = Subject.query.get(class_obj.subject_id)
        
        # コンテキストの準備
        context_data = []
        
        # チャット履歴の取得（新しい順に10件）
        if class_id:
            chat_history = ChatHistory.query.filter_by(
                user_id=current_user.id,
                class_id=class_id
            ).order_by(ChatHistory.timestamp.desc()).limit(10).all()
        else:
            chat_history = ChatHistory.query.filter_by(
                user_id=current_user.id,
                class_id=None
            ).order_by(ChatHistory.timestamp.desc()).limit(10).all()
        
        # 古い順に並べ直してコンテキストに追加
        for chat in reversed(chat_history):
            context_data.append({
                'is_user': chat.is_user,
                'message': chat.message
            })
        
        # 選択中のテーマを取得（学生の場合）
        theme_context = None
        if current_user.role == 'student':
            if class_id:
                theme = InquiryTheme.query.filter_by(
                    student_id=current_user.id,
                    class_id=class_id,
                    is_selected=True
                ).first()
            else:
                theme = InquiryTheme.query.filter_by(
                    student_id=current_user.id, 
                    is_selected=True
                ).first()
            if theme:
                theme_context = f"現在の探究テーマ: {theme.title}"
                if theme.question:
                    theme_context += f"\n探究の問い: {theme.question}"
        
        # メッセージにテーマ情報を追加
        full_message = message
        if theme_context:
            full_message = f"{theme_context}\n\nユーザーの質問: {message}"
        
        # AI応答を生成（教科別プロンプト対応）
        ai_response = generate_chat_response(full_message, context_data, subject=subject)
        
        # チャット履歴を保存
        # ユーザーのメッセージを保存
        user_chat = ChatHistory(
            user_id=current_user.id,
            class_id=class_id,
            subject_id=subject.id if subject else None,
            message=message, 
            is_user=True
        )
        db.session.add(user_chat)
        
        # AIの返答を保存
        ai_chat = ChatHistory(
            user_id=current_user.id,
            class_id=class_id,
            subject_id=subject.id if subject else None,
            message=ai_response, 
            is_user=False
        )
        db.session.add(ai_chat)
        
        db.session.commit()
        
        return jsonify({
            "message": ai_response,
            "status": "success"
        })
        
    except Exception as e:
        logging.error(f"チャットAPIエラー: {str(e)}")
        db.session.rollback()
        return jsonify({
            "error": "エラーが発生しました。もう一度お試しください。",
            "status": "error"
        }), 500

@api_bp.route('/teacher/first_class', methods=['GET'])
@login_required
def teacher_first_class():
    """教師の最初のクラスを取得"""
    if current_user.role != 'teacher':
        return jsonify({'error': '教師のみアクセス可能です'}), 403
    
    # 教師の最初のクラスを取得
    first_class = Class.query.filter_by(teacher_id=current_user.id).first()
    if first_class:
        return jsonify({
            'class_id': first_class.id,
            'class_name': first_class.name
        })
    else:
        return jsonify({'class_id': None})

@api_bp.route('/export/evaluations', methods=['POST'])
@login_required
def export_evaluations():
    """評価データのエクスポート"""
    if current_user.role != 'teacher':
        return jsonify({'error': '教師のみアクセス可能です'}), 403
    
    try:
        # セッションから評価データを取得
        evaluations_json = session.get('evaluations')
        class_name = session.get('class_name', 'クラス')
        class_id = session.get('class_id')
        
        if not evaluations_json:
            # セッションにデータがない場合は、class_idから取得を試みる
            if class_id:
                evaluations = []
                db_evaluations = StudentEvaluation.query.filter_by(class_id=class_id).all()
                
                for eval_obj in db_evaluations:
                    student = User.query.get(eval_obj.student_id)
                    if student:
                        evaluations.append({
                            'student_name': student.username,
                            'evaluation': eval_obj.evaluation_text
                        })
            else:
                return jsonify({'error': 'エクスポートするデータがありません'}), 400
        else:
            evaluations = json.loads(evaluations_json)
        
        # レスポンスデータを作成
        return jsonify({
            'evaluations': evaluations,
            'class_name': class_name,
            'status': 'success'
        })
        
    except Exception as e:
        logging.error(f"評価エクスポートエラー: {str(e)}")
        return jsonify({
            'error': 'エクスポート中にエラーが発生しました',
            'status': 'error'
        }), 500

@api_bp.route('/theme/<int:theme_id>/select', methods=['POST'])
@login_required
@api_limit()
def select_theme(theme_id):
    """テーマ選択API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    theme = InquiryTheme.query.get_or_404(theme_id)
    
    # 権限チェック
    if theme.student_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        # 既存の選択を解除
        InquiryTheme.query.filter_by(
            student_id=current_user.id, 
            is_selected=True
        ).update({'is_selected': False})
        
        # 新しいテーマを選択
        theme.is_selected = True
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'テーマ「{theme.title}」を選択しました'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"テーマ選択エラー: {str(e)}")
        return jsonify({
            'error': 'テーマの選択に失敗しました',
            'status': 'error'
        }), 500

@api_bp.route('/todo/<int:todo_id>/toggle', methods=['POST'])
@login_required
@api_limit()
def toggle_todo(todo_id):
    """To Do完了状態切り替えAPI"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    from app.models import Todo
    todo = Todo.query.get_or_404(todo_id)
    
    # 権限チェック
    if todo.student_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        # 完了状態を切り替え
        todo.is_completed = not todo.is_completed
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'is_completed': todo.is_completed,
            'message': f'To Doを{"完了" if todo.is_completed else "未完了"}にしました'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"To Do切り替えエラー: {str(e)}")
        return jsonify({
            'error': 'To Doの更新に失敗しました',
            'status': 'error'
        }), 500

@api_bp.route('/goal/<int:goal_id>/progress', methods=['POST'])
@login_required
@api_limit()
def update_goal_progress(goal_id):
    """目標進捗更新API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    from app.models import Goal
    goal = Goal.query.get_or_404(goal_id)
    
    # 権限チェック
    if goal.student_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        data = request.get_json()
        progress = data.get('progress', 0)
        
        # 進捗を0-100の範囲に制限
        goal.progress = max(0, min(100, int(progress)))
        
        # 100%になったら完了フラグを立てる
        if goal.progress >= 100:
            goal.is_completed = True
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'progress': goal.progress,
            'is_completed': goal.is_completed,
            'message': f'進捗を{goal.progress}%に更新しました'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"目標進捗更新エラー: {str(e)}")
        return jsonify({
            'error': '進捗の更新に失敗しました',
            'status': 'error'
        }), 500

@api_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """ユーザー統計情報を取得"""
    stats = {}
    
    if current_user.role == 'admin':
        # 管理者用統計
        stats = {
            'total_users': User.query.count(),
            'total_students': User.query.filter_by(role='student').count(),
            'total_teachers': User.query.filter_by(role='teacher').count(),
            'total_classes': Class.query.count(),
            'pending_approvals': User.query.filter_by(
                role='student', 
                email_confirmed=True, 
                is_approved=False
            ).count()
        }
        
    elif current_user.role == 'teacher':
        # 教師用統計
        from app.models import ClassEnrollment
        
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
        total_students = 0
        for class_obj in classes:
            total_students += ClassEnrollment.query.filter_by(class_id=class_obj.id).count()
        
        stats = {
            'total_classes': len(classes),
            'total_students': total_students,
            'pending_approvals': User.query.filter_by(
                role='student',
                school_id=current_user.school_id,
                email_confirmed=True,
                is_approved=False
            ).count()
        }
        
    elif current_user.role == 'student':
        # 学生用統計
        from app.models import Todo, Goal, ActivityLog
        
        stats = {
            'total_activities': ActivityLog.query.filter_by(student_id=current_user.id).count(),
            'pending_todos': Todo.query.filter_by(
                student_id=current_user.id, 
                is_completed=False
            ).count(),
            'active_goals': Goal.query.filter_by(
                student_id=current_user.id, 
                is_completed=False
            ).count(),
            'completed_goals': Goal.query.filter_by(
                student_id=current_user.id, 
                is_completed=True
            ).count()
        }
    
    return jsonify(stats)

# ========================
# 自由進度学習 API エンドポイント  
# ========================

@api_bp.route('/units', methods=['GET'])
@login_required
@api_limit()
def get_units():
    """単元一覧取得API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    try:
        # パラメータ取得
        include_progress = request.args.get('include_progress', 'true').lower() == 'true'
        difficulty_filter = request.args.get('difficulty', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)  # 最大100件まで
        
        # 基本クエリ
        query = CurriculumUnit.query
        
        # 難易度フィルタ
        if difficulty_filter:
            query = query.filter(CurriculumUnit.difficulty_level == difficulty_filter)
        
        # ページネーション
        units_pagination = query.order_by(CurriculumUnit.order_index).paginate(
            page=page, per_page=per_page, error_out=False)
        
        units_data = []
        for unit in units_pagination.items:
            unit_dict = {
                'id': unit.id,
                'title': unit.title,
                'description': unit.description,
                'difficulty_level': unit.difficulty_level,
                'estimated_minutes': unit.estimated_minutes,
                'order_index': unit.order_index,
                'prerequisites': unit.prerequisites or []
            }
            
            # 進捗情報を含める場合
            if include_progress:
                selection = StudentUnitSelection.query.filter_by(
                    student_id=current_user.id,
                    unit_id=unit.id
                ).first()
                
                if selection:
                    unit_dict['progress'] = {
                        'status': selection.status,
                        'percentage': float(selection.progress_percentage),
                        'completed_items': selection.completed_items,
                        'total_items': selection.total_items,
                        'study_time_minutes': selection.study_time_minutes,
                        'last_activity_at': selection.last_activity_at.isoformat() if selection.last_activity_at else None
                    }
                else:
                    unit_dict['progress'] = {
                        'status': 'not_started',
                        'percentage': 0.0,
                        'completed_items': 0,
                        'total_items': 0,
                        'study_time_minutes': 0,
                        'last_activity_at': None
                    }
            
            units_data.append(unit_dict)
        
        return jsonify({
            'status': 'success',
            'data': {
                'units': units_data,
                'total': units_pagination.total,
                'pages': units_pagination.pages,
                'current_page': page,
                'per_page': per_page
            }
        })
        
    except Exception as e:
        logging.error(f"単元一覧取得エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '単元一覧の取得に失敗しました'
        }), 500

@api_bp.route('/units/select', methods=['POST'])
@login_required
@api_limit()
def select_unit():
    """単元選択API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    try:
        data = request.get_json()
        unit_id = data.get('unit_id')
        class_id = data.get('class_id')
        selection_reason = data.get('selection_reason', 'self_selected')
        
        if not unit_id:
            return jsonify({
                'status': 'error',
                'message': '単元IDが必要です'
            }), 400
        
        # 単元の存在確認
        unit = CurriculumUnit.query.get(unit_id)
        if not unit:
            return jsonify({
                'status': 'error',
                'message': '指定された単元が見つかりません'
            }), 404
        
        # 既存の選択履歴をチェック
        existing_selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id,
            unit_id=unit_id,
            class_id=class_id
        ).first()
        
        if existing_selection:
            # 既に選択済みの場合は状態を更新
            if existing_selection.status == 'completed':
                return jsonify({
                    'status': 'error',
                    'message': 'この単元は既に完了しています'
                }), 400
            else:
                existing_selection.status = 'in_progress'
                existing_selection.last_activity_at = datetime.utcnow()
        else:
            # 新規選択
            # 単元の問題数を計算
            total_items = UnitItemMapping.query.filter_by(unit_id=unit_id).count()
            
            new_selection = StudentUnitSelection(
                student_id=current_user.id,
                unit_id=unit_id,
                class_id=class_id,
                status='in_progress',
                total_items=total_items,
                started_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow()
            )
            db.session.add(new_selection)
        
        db.session.commit()
        
        # ログ記録
        logging.info(f"User {current_user.id} selected unit {unit_id} via {selection_reason}")
        
        return jsonify({
            'status': 'success',
            'message': f'単元「{unit.title}」を選択しました',
            'data': {
                'unit_id': unit_id,
                'title': unit.title,
                'status': 'in_progress'
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"単元選択エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '単元の選択に失敗しました'
        }), 500

@api_bp.route('/units/<int:unit_id>/progress', methods=['POST'])
@login_required
@api_limit()
def update_unit_progress(unit_id):
    """単元進捗更新API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    try:
        data = request.get_json()
        completed_items = data.get('completed_items', 0)
        correct_items = data.get('correct_items', 0)
        study_time_minutes = data.get('study_time_minutes', 0)
        
        # 選択履歴を取得
        selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id,
            unit_id=unit_id
        ).first()
        
        if not selection:
            return jsonify({
                'status': 'error',
                'message': 'この単元は選択されていません'
            }), 404
        
        # 進捗を更新
        selection.completed_items = completed_items
        selection.correct_items = correct_items
        selection.study_time_minutes += study_time_minutes
        selection.last_activity_at = datetime.utcnow()
        
        # 進捗率を計算
        if selection.total_items > 0:
            selection.progress_percentage = (completed_items / selection.total_items) * 100
        
        # 完了判定
        if selection.progress_percentage >= 80:  # 80%以上で完了とする
            selection.status = 'completed'
            selection.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '進捗を更新しました',
            'data': {
                'progress_percentage': float(selection.progress_percentage),
                'status': selection.status,
                'completed_items': selection.completed_items,
                'correct_items': selection.correct_items,
                'study_time_minutes': selection.study_time_minutes
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"単元進捗更新エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '進捗の更新に失敗しました'
        }), 500

@api_bp.route('/speech/transcribe', methods=['POST'])
@login_required
@api_limit()
def transcribe_speech():
    """音声入力保存API"""
    try:
        data = request.get_json()
        transcription = data.get('transcription', '')
        usage_context = data.get('usage_context', 'chat')
        duration = data.get('duration', 0)
        
        if not transcription:
            return jsonify({
                'status': 'error',
                'message': '音声テキストが空です'
            }), 400
        
        # 音声入力履歴を保存
        from app.models import SpeechTranscription
        speech_record = SpeechTranscription(
            user_id=current_user.id,
            transcription=transcription,
            usage_context=usage_context
        )
        db.session.add(speech_record)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'data': {
                'id': speech_record.id,
                'saved_at': speech_record.created_at.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"音声入力保存エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '音声入力の保存に失敗しました'
        }), 500

# ========================
# AI推薦機能 API エンドポイント  
# ========================

@api_bp.route('/recommendations', methods=['GET'])
@login_required
@api_limit()
def get_recommendations():
    """AI推薦取得API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    try:
        # パラメータ取得
        recommendation_type = request.args.get('type', 'unit')
        max_recommendations = min(request.args.get('max', 5, type=int), 10)
        force_regenerate = request.args.get('force', 'false').lower() == 'true'
        
        # AI推薦エンジンを初期化
        from app.services.ai_recommender import AIRecommendationEngine
        recommender = AIRecommendationEngine()
        
        # 推薦を生成
        recommendations = recommender.generate_recommendations(
            student_id=current_user.id,
            recommendation_type=recommendation_type,
            max_recommendations=max_recommendations,
            force_regenerate=force_regenerate
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'recommendations': recommendations,
                'type': recommendation_type,
                'generated_at': datetime.utcnow().isoformat(),
                'total_count': len(recommendations)
            }
        })
        
    except Exception as e:
        logging.error(f"AI推薦取得エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'AI推薦の取得に失敗しました'
        }), 500

@api_bp.route('/recommendations/<int:recommendation_id>/feedback', methods=['POST'])
@login_required
@api_limit()
def submit_recommendation_feedback(recommendation_id):
    """AI推薦フィードバック送信API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    try:
        data = request.get_json()
        is_accepted = data.get('is_accepted', False)
        is_effective = data.get('is_effective')
        feedback_text = data.get('feedback_text', '')
        
        # 推薦の存在確認と権限チェック
        recommendation = AIRecommendation.query.get(recommendation_id)
        if not recommendation:
            return jsonify({
                'status': 'error',
                'message': '推薦が見つかりません'
            }), 404
        
        if recommendation.student_id != current_user.id:
            return jsonify({'error': '権限がありません'}), 403
        
        # AI推薦エンジンでフィードバックを処理
        from app.services.ai_recommender import AIRecommendationEngine
        recommender = AIRecommendationEngine()
        
        recommender.get_recommendation_feedback(
            recommendation_id=recommendation_id,
            is_accepted=is_accepted,
            is_effective=is_effective,
            feedback_text=feedback_text
        )
        
        return jsonify({
            'status': 'success',
            'message': 'フィードバックを記録しました'
        })
        
    except Exception as e:
        logging.error(f"推薦フィードバックエラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'フィードバックの送信に失敗しました'
        }), 500

@api_bp.route('/recommendations/settings', methods=['GET', 'POST'])
@login_required
@api_limit()
def recommendation_settings():
    """推薦設定API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    from app.models import RecommendationSettings
    
    if request.method == 'GET':
        # 設定取得
        try:
            settings = RecommendationSettings.query.filter_by(
                student_id=current_user.id
            ).first()
            
            if settings:
                settings_data = {
                    'enable_ai_recommendations': settings.enable_ai_recommendations,
                    'recommendation_frequency': settings.recommendation_frequency,
                    'max_recommendations_per_session': settings.max_recommendations_per_session,
                    'preferred_difficulty_adjustment': float(settings.preferred_difficulty_adjustment),
                    'enable_challenge_problems': settings.enable_challenge_problems,
                    'enable_review_recommendations': settings.enable_review_recommendations,
                    'privacy_level': settings.privacy_level,
                    'feedback_required': settings.feedback_required
                }
            else:
                # デフォルト設定
                settings_data = {
                    'enable_ai_recommendations': True,
                    'recommendation_frequency': 'daily',
                    'max_recommendations_per_session': 5,
                    'preferred_difficulty_adjustment': 0.0,
                    'enable_challenge_problems': True,
                    'enable_review_recommendations': True,
                    'privacy_level': 'full',
                    'feedback_required': False
                }
            
            return jsonify({
                'status': 'success',
                'data': settings_data
            })
            
        except Exception as e:
            logging.error(f"推薦設定取得エラー: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': '設定の取得に失敗しました'
            }), 500
    
    else:  # POST
        # 設定更新
        try:
            data = request.get_json()
            
            from app.services.ai_recommender import AIRecommendationEngine
            recommender = AIRecommendationEngine()
            
            recommender.update_recommendation_settings(
                student_id=current_user.id,
                settings_data=data
            )
            
            return jsonify({
                'status': 'success',
                'message': '設定を更新しました'
            })
            
        except Exception as e:
            logging.error(f"推薦設定更新エラー: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': '設定の更新に失敗しました'
            }), 500

@api_bp.route('/recommendations/analytics', methods=['GET'])
@login_required
@api_limit()
def recommendation_analytics():
    """推薦分析データ取得API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    try:
        from app.services.ai_recommender import RecommendationAnalytics
        
        metrics = RecommendationAnalytics.get_recommendation_metrics(
            student_id=current_user.id
        )
        
        return jsonify({
            'status': 'success',
            'data': metrics
        })
        
    except Exception as e:
        logging.error(f"推薦分析データ取得エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '分析データの取得に失敗しました'
        }), 500

# ========================
# 復習問題生成機能 API エンドポイント  
# ========================

@api_bp.route('/review/weaknesses', methods=['GET'])
@login_required
@api_limit()
def get_weaknesses():
    """弱点分析取得API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    try:
        force_update = request.args.get('force', 'false').lower() == 'true'
        
        from app.services.weakness_analyzer import WeaknessAnalyzer
        analyzer = WeaknessAnalyzer()
        
        weaknesses = analyzer.analyze_student_weaknesses(
            student_id=current_user.id,
            force_update=force_update
        )
        
        # サマリー情報も取得
        summary = analyzer.get_weakness_summary(current_user.id)
        
        return jsonify({
            'status': 'success',
            'data': {
                'weaknesses': weaknesses,
                'summary': summary,
                'analyzed_at': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logging.error(f"弱点分析取得エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '弱点分析の取得に失敗しました'
        }), 500

@api_bp.route('/review/sets', methods=['GET', 'POST'])
@login_required
@api_limit()
def review_sets():
    """復習セット管理API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    if request.method == 'GET':
        # 復習セット一覧取得
        try:
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 10, type=int), 50)
            status_filter = request.args.get('status')
            
            query = ReviewSet.query.filter_by(student_id=current_user.id)
            
            if status_filter:
                query = query.filter(ReviewSet.status == status_filter)
            
            review_sets_pagination = query.order_by(
                ReviewSet.created_at.desc()
            ).paginate(page=page, per_page=per_page, error_out=False)
            
            sets_data = []
            for review_set in review_sets_pagination.items:
                # 進捗情報を計算
                completed_items = ReviewSetItem.query.filter_by(
                    review_set_id=review_set.id,
                    is_completed=True
                ).count()
                
                sets_data.append({
                    'id': review_set.id,
                    'title': review_set.title,
                    'description': review_set.description,
                    'review_type': review_set.review_type,
                    'status': review_set.status,
                    'total_problems': review_set.total_problems,
                    'completed_problems': completed_items,
                    'estimated_time_minutes': review_set.estimated_time_minutes,
                    'expires_at': review_set.expires_at.isoformat() if review_set.expires_at else None,
                    'created_at': review_set.created_at.isoformat()
                })
            
            return jsonify({
                'status': 'success',
                'data': {
                    'review_sets': sets_data,
                    'total': review_sets_pagination.total,
                    'pages': review_sets_pagination.pages,
                    'current_page': page,
                    'per_page': per_page
                }
            })
            
        except Exception as e:
            logging.error(f"復習セット一覧取得エラー: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': '復習セット一覧の取得に失敗しました'
            }), 500
    
    else:  # POST
        # 復習セット作成
        try:
            data = request.get_json()
            review_type = data.get('review_type', 'spaced_repetition')
            target_problems = min(data.get('target_problems', 20), 50)  # 最大50問
            focus_weaknesses = data.get('focus_weaknesses', True)
            
            from app.services.spaced_repetition import SpacedRepetitionEngine
            engine = SpacedRepetitionEngine()
            
            review_set = engine.create_review_set(
                student_id=current_user.id,
                review_type=review_type,
                target_problems=target_problems,
                focus_weaknesses=focus_weaknesses
            )
            
            return jsonify({
                'status': 'success',
                'message': '復習セットを作成しました',
                'data': {
                    'id': review_set.id,
                    'title': review_set.title,
                    'total_problems': review_set.total_problems,
                    'estimated_time_minutes': review_set.estimated_time_minutes
                }
            })
            
        except Exception as e:
            logging.error(f"復習セット作成エラー: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': '復習セットの作成に失敗しました'
            }), 500

@api_bp.route('/review/sets/<int:set_id>/items', methods=['GET'])
@login_required
@api_limit()
def get_review_set_items(set_id):
    """復習セット問題取得API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    try:
        # 復習セットの存在確認と権限チェック
        review_set = ReviewSet.query.get(set_id)
        if not review_set:
            return jsonify({
                'status': 'error',
                'message': '復習セットが見つかりません'
            }), 404
        
        if review_set.student_id != current_user.id:
            return jsonify({'error': '権限がありません'}), 403
        
        # 復習問題一覧を取得
        items = ReviewSetItem.query.filter_by(
            review_set_id=set_id
        ).order_by(ReviewSetItem.order_index).all()
        
        items_data = []
        for item in items:
            items_data.append({
                'id': item.id,
                'problem_id': item.problem_id,
                'order_index': item.order_index,
                'weight': float(item.weight),
                'expected_difficulty': float(item.expected_difficulty) if item.expected_difficulty else 2.5,
                'weakness_category': item.weakness_category,
                'selection_reason': item.selection_reason,
                'is_completed': item.is_completed,
                'is_correct': item.is_correct,
                'time_spent_seconds': item.time_spent_seconds,
                'attempts_count': item.attempts_count,
                'completed_at': item.completed_at.isoformat() if item.completed_at else None
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'review_set': {
                    'id': review_set.id,
                    'title': review_set.title,
                    'description': review_set.description,
                    'review_type': review_set.review_type,
                    'status': review_set.status
                },
                'items': items_data,
                'total_count': len(items)
            }
        })
        
    except Exception as e:
        logging.error(f"復習問題取得エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '復習問題の取得に失敗しました'
        }), 500

@api_bp.route('/review/items/<int:item_id>/submit', methods=['POST'])
@login_required
@api_limit()
def submit_review_answer(item_id):
    """復習問題回答送信API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    try:
        data = request.get_json()
        student_answer = data.get('student_answer', '')
        is_correct = data.get('is_correct', False)
        time_spent_seconds = data.get('time_spent_seconds', 0)
        confidence_level = data.get('confidence_level', 3)
        
        # 復習問題の存在確認と権限チェック
        review_item = ReviewSetItem.query.get(item_id)
        if not review_item:
            return jsonify({
                'status': 'error',
                'message': '復習問題が見つかりません'
            }), 404
        
        if review_item.review_set.student_id != current_user.id:
            return jsonify({'error': '権限がありません'}), 403
        
        # 間隔反復エンジンで結果を処理
        from app.services.spaced_repetition import SpacedRepetitionEngine
        engine = SpacedRepetitionEngine()
        
        result = engine.process_review_result(
            review_set_item_id=item_id,
            student_answer=student_answer,
            is_correct=is_correct,
            time_spent_seconds=time_spent_seconds,
            confidence_level=confidence_level
        )
        
        return jsonify({
            'status': 'success',
            'message': '回答を記録しました',
            'data': result
        })
        
    except Exception as e:
        logging.error(f"復習問題回答エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '回答の記録に失敗しました'
        }), 500

@api_bp.route('/review/statistics', methods=['GET'])
@login_required
@api_limit()
def get_review_statistics():
    """復習統計取得API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    try:
        from app.services.spaced_repetition import SpacedRepetitionEngine
        engine = SpacedRepetitionEngine()
        
        statistics = engine.get_review_statistics(current_user.id)
        
        return jsonify({
            'status': 'success',
            'data': statistics
        })
        
    except Exception as e:
        logging.error(f"復習統計取得エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '統計データの取得に失敗しました'
        }), 500


# ランキングAPI
@api_bp.route('/rankings/<ranking_type>')
@login_required
@api_limit()
def get_ranking(ranking_type):
    """ランキング取得API"""
    from app.services.ranking_service import RankingService
    
    try:
        # パラメータ取得
        scope = request.args.get('scope', 'school')
        scope_id = request.args.get('scope_id', type=int)
        limit = request.args.get('limit', type=int, default=50)
        
        # 入力値検証
        try:
            from app.utils.validators import validate_ranking_params
            validated_params = validate_ranking_params(ranking_type, scope, scope_id, limit)
        except ImportError:
            # validators モジュールがない場合の基本検証
            valid_ranking_types = ['total_points', 'weekly_points', 'monthly_points', 
                                  'accuracy_rate', 'study_time', 'consistency']
            if ranking_type not in valid_ranking_types:
                return jsonify({'error': '無効なランキング種類です'}), 400
            
            if scope not in ['school', 'class']:
                return jsonify({'error': '無効なスコープです'}), 400
            
            if limit < 1 or limit > 1000:
                return jsonify({'error': '無効な取得件数です'}), 400
        
        # 権限チェック
        if scope == 'class' and scope_id:
            if current_user.role == 'student':
                # 学生は所属クラスのみアクセス可能
                enrollment = ClassEnrollment.query.filter_by(
                    student_id=current_user.id,
                    class_id=scope_id,
                    is_active=True
                ).first()
                if not enrollment:
                    return jsonify({'error': 'アクセス権限がありません'}), 403
            elif current_user.role == 'teacher':
                # 教師は担当クラスのみアクセス可能
                class_obj = Class.query.filter_by(
                    id=scope_id,
                    teacher_id=current_user.id,
                    is_active=True
                ).first()
                if not class_obj:
                    return jsonify({'error': 'アクセス権限がありません'}), 403
        
        # スコープIDの設定
        if scope == 'school' and not scope_id:
            scope_id = current_user.school_id
        
        ranking_data = RankingService.get_ranking(ranking_type, scope, scope_id, limit)
        
        # 学生の場合は自分のランキング情報も追加
        if current_user.role == 'student':
            my_rank = RankingService.get_student_rank(current_user.id, ranking_type, scope, scope_id)
            ranking_data['my_rank'] = my_rank
        
        return jsonify({
            'status': 'success',
            'data': ranking_data
        })
        
    except Exception as e:
        logging.error(f"ランキング取得エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'ランキングデータの取得に失敗しました'
        }), 500


@api_bp.route('/rankings/student/<int:student_id>')
@login_required
@api_limit()
def get_student_ranking(student_id):
    """特定学生のランキング情報取得API"""
    from app.services.ranking_service import RankingService
    
    try:
        # 権限チェック
        if current_user.role == 'student' and current_user.id != student_id:
            return jsonify({'error': '他の学生の情報は閲覧できません'}), 403
        elif current_user.role == 'teacher':
            # 教師は担当クラスの学生のみ閲覧可能
            student = User.query.get(student_id)
            if not student or student.role != 'student':
                return jsonify({'error': '学生が見つかりません'}), 404
            
            # 教師のクラスに所属している学生かチェック
            teacher_classes = [c.id for c in Class.query.filter_by(teacher_id=current_user.id).all()]
            student_classes = [e.class_id for e in ClassEnrollment.query.filter_by(student_id=student_id, is_active=True).all()]
            
            if not any(c in teacher_classes for c in student_classes):
                return jsonify({'error': 'アクセス権限がありません'}), 403
        
        ranking_type = request.args.get('type', 'total_points')
        scope = request.args.get('scope', 'school')
        scope_id = request.args.get('scope_id', type=int)
        
        if scope == 'school' and not scope_id:
            scope_id = current_user.school_id
        
        ranking_info = RankingService.get_student_rank(student_id, ranking_type, scope, scope_id)
        
        return jsonify({
            'status': 'success',
            'data': ranking_info
        })
        
    except Exception as e:
        logging.error(f"学生ランキング取得エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '学生ランキング情報の取得に失敗しました'
        }), 500


@api_bp.route('/rankings/analytics/<int:class_id>')
@login_required
@api_limit()
def get_ranking_analytics(class_id):
    """ランキング分析データ取得API（教師専用）"""
    if current_user.role != 'teacher':
        return jsonify({'error': '教師のみアクセス可能です'}), 403
    
    try:
        # 教師の権限チェック
        class_obj = Class.query.filter_by(
            id=class_id,
            teacher_id=current_user.id,
            is_active=True
        ).first()
        
        if not class_obj:
            return jsonify({'error': 'アクセス権限がありません'}), 403
        
        ranking_type = request.args.get('type', 'total_points')
        
        # 分析データを生成
        from app.teacher import _generate_class_analytics
        analytics = _generate_class_analytics(class_id, ranking_type)
        
        return jsonify({
            'status': 'success',
            'data': analytics
        })
        
    except Exception as e:
        logging.error(f"ランキング分析取得エラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '分析データの取得に失敗しました'
        }), 500


@api_bp.route('/rankings/cache/clear', methods=['POST'])
@login_required
@api_limit()
def clear_ranking_cache():
    """ランキングキャッシュクリアAPI（管理者専用）"""
    if current_user.role != 'admin':
        return jsonify({'error': '管理者のみアクセス可能です'}), 403
    
    try:
        from app.services.ranking_service import RankingService
        
        ranking_type = request.json.get('ranking_type') if request.json else None
        RankingService.clear_cache(ranking_type)
        
        return jsonify({
            'status': 'success',
            'message': 'ランキングキャッシュをクリアしました'
        })
        
    except Exception as e:
        logging.error(f"キャッシュクリアエラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'キャッシュクリアに失敗しました'
        }), 500

@api_bp.route('/rankings/export')
@login_required
@api_limit()
def export_ranking():
    """ランキングデータエクスポートAPI"""
    try:
        ranking_type = request.args.get('type', 'total_points')
        scope = request.args.get('scope', 'school')
        scope_id = request.args.get('scope_id', type=int)
        format_type = request.args.get('format', 'csv')
        
        # 基本的な検証
        if format_type not in ['csv', 'json']:
            return jsonify({'error': '無効なフォーマットです'}), 400
        
        # 権限チェック
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({'error': 'エクスポート権限がありません'}), 403
        
        # ランキングデータ取得
        from app.services.ranking_service import RankingService
        ranking_data = RankingService.get_ranking(ranking_type, scope, scope_id, 100)
        
        if format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # ヘッダー行
            writer.writerow(['順位', '学生名', 'スコア', '学校名', 'クラス名'])
            
            # データ行
            for student in ranking_data.get('rankings', []):
                writer.writerow([
                    student.get('rank', ''),
                    student.get('student_name', ''),
                    student.get('score', ''),
                    student.get('school_name', ''),
                    student.get('class_name', '')
                ])
            
            output.seek(0)
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=ranking_{ranking_type}.csv'
            return response
        
        else:  # JSON
            response = make_response(jsonify(ranking_data))
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Disposition'] = f'attachment; filename=ranking_{ranking_type}.json'
            return response
            
    except Exception as e:
        logging.error(f"ランキングエクスポートエラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'エクスポートに失敗しました'
        }), 500