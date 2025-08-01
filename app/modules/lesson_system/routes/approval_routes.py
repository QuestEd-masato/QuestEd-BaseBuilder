"""
レッスン承認システム ルーティング

レッスン完了申請・承認機能のAPIエンドポイント定義
Phase5で追加された承認ワークフロー機能
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from app.student.utils import student_required
from app.teacher.common import teacher_required
from ..services.approval_service import LessonApprovalService

# Blueprint作成
approval_bp = Blueprint('lesson_approval', __name__, url_prefix='/lesson-approval')


# === 学生向けルート ===

@approval_bp.route('/lesson/<int:lesson_id>/submit-completion', methods=['POST'])
@login_required
@student_required
def submit_completion_request(lesson_id):
    """生徒からのレッスン完了申請
    
    Args:
        lesson_id: 申請対象のレッスンID
        
    Request JSON:
        notes (optional): 申請時のメモ
        
    Returns:
        JSON: 処理結果
            - success: bool
            - message: str
            - progress_id: int (成功時)
    """
    try:
        # リクエストデータの取得
        data = request.get_json() or {}
        notes = data.get('notes', '').strip() or None
        
        current_app.logger.info(f"Completion request received: student {current_user.id}, lesson {lesson_id}")
        
        # サービス層での処理実行
        result = LessonApprovalService.submit_completion_request(
            student_id=current_user.id,
            lesson_id=lesson_id,
            notes=notes
        )
        
        # HTTPステータスコードの設定
        status_code = 200 if result['success'] else 400
        
        return jsonify(result), status_code
        
    except Exception as e:
        current_app.logger.error(f"Error in submit_completion_request: {e}")
        return jsonify({
            'success': False,
            'message': 'サーバーエラーが発生しました。'
        }), 500


# === 教師向けルート ===

@approval_bp.route('/progress/<int:progress_id>/approve', methods=['POST'])
@login_required
@teacher_required
def approve_lesson_completion(progress_id):
    """教師によるレッスン完了承認
    
    Args:
        progress_id: 承認対象の進捗レコードID
        
    Request JSON:
        comments (optional): 承認時のコメント
        
    Returns:
        JSON: 処理結果
            - success: bool
            - message: str
            - lesson_title: str (成功時)
    """
    try:
        # リクエストデータの取得
        data = request.get_json() or {}
        comments = data.get('comments', '').strip() or None
        
        current_app.logger.info(f"Approval request received: teacher {current_user.id}, progress {progress_id}")
        
        # サービス層での処理実行
        result = LessonApprovalService.approve_lesson(
            teacher_id=current_user.id,
            progress_id=progress_id,
            comments=comments
        )
        
        # HTTPステータスコードの設定
        status_code = 200 if result['success'] else 400
        
        return jsonify(result), status_code
        
    except Exception as e:
        current_app.logger.error(f"Error in approve_lesson_completion: {e}")
        return jsonify({
            'success': False,
            'message': 'サーバーエラーが発生しました。'
        }), 500


@approval_bp.route('/progress/<int:progress_id>/reject', methods=['POST'])
@login_required
@teacher_required
def reject_lesson_completion(progress_id):
    """教師によるレッスン完了申請却下
    
    Args:
        progress_id: 却下対象の進捗レコードID
        
    Request JSON:
        reason (required): 却下理由
        
    Returns:
        JSON: 処理結果
            - success: bool
            - message: str
            - lesson_title: str (成功時)
    """
    try:
        # リクエストデータの取得
        data = request.get_json() or {}
        reason = data.get('reason', '').strip()
        
        # 却下理由の必須チェック
        if not reason:
            return jsonify({
                'success': False,
                'message': '却下理由を入力してください。'
            }), 400
        
        current_app.logger.info(f"Rejection request received: teacher {current_user.id}, progress {progress_id}")
        
        # サービス層での処理実行
        result = LessonApprovalService.reject_lesson(
            teacher_id=current_user.id,
            progress_id=progress_id,
            reason=reason
        )
        
        # HTTPステータスコードの設定
        status_code = 200 if result['success'] else 400
        
        return jsonify(result), status_code
        
    except Exception as e:
        current_app.logger.error(f"Error in reject_lesson_completion: {e}")
        return jsonify({
            'success': False,
            'message': 'サーバーエラーが発生しました。'
        }), 500


@approval_bp.route('/class/<int:class_id>/pending-approvals', methods=['GET'])
@login_required
@teacher_required
def get_pending_approvals(class_id):
    """教師の承認待ちレッスン一覧取得
    
    Args:
        class_id: 対象クラスID
        
    Returns:
        JSON: 承認待ちレッスンのリスト
            - success: bool
            - data: List[Dict] - 承認待ちレッスン情報
            - count: int - 件数
    """
    try:
        current_app.logger.info(f"Pending approvals request: teacher {current_user.id}, class {class_id}")
        
        # サービス層での処理実行
        pending_approvals = LessonApprovalService.get_pending_approvals(
            teacher_id=current_user.id,
            class_id=class_id
        )
        
        return jsonify({
            'success': True,
            'data': pending_approvals,
            'count': len(pending_approvals)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in get_pending_approvals: {e}")
        return jsonify({
            'success': False,
            'message': 'サーバーエラーが発生しました。',
            'data': [],
            'count': 0
        }), 500