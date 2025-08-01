"""
承認システム ルーティング（簡易版）

3状態管理のAPIエンドポイント
"""

from flask import Blueprint, jsonify, request, current_app, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.utils.decorators import student_required, teacher_required
from ..services.approval_service import ApprovalService

approval_bp = Blueprint('approval_system', __name__, url_prefix='/approval-system')


# === 教師向けUIルート ===

@approval_bp.route('/teacher/pending-approvals')
@login_required
@teacher_required
def teacher_pending_approvals():
    """教師向け承認待ち一覧画面"""
    try:
        # 承認待ちの申請を取得
        pending_requests = ApprovalService.get_pending_approvals(current_user.id)
        
        return render_template(
            'teacher/approval_management.html',
            pending_requests=pending_requests,
            page_title="承認待ち一覧"
        )
    except Exception as e:
        current_app.logger.error(f"Error in teacher_pending_approvals: {e}")
        flash('承認待ち一覧の取得に失敗しました。', 'error')
        return redirect(url_for('teacher_dashboard.dashboard'))


@approval_bp.route('/teacher/approval-detail/<int:request_id>')
@login_required
@teacher_required
def teacher_approval_detail(request_id):
    """教師向け承認詳細画面"""
    try:
        # 承認詳細を取得
        approval_detail = ApprovalService.get_approval_detail(request_id, current_user.id)
        
        if not approval_detail:
            flash('承認詳細が見つかりません。', 'error')
            return redirect(url_for('approval_system.teacher_pending_approvals'))
        
        return render_template(
            'teacher/approval_detail.html',
            approval_detail=approval_detail,
            page_title="承認詳細"
        )
    except Exception as e:
        current_app.logger.error(f"Error in teacher_approval_detail: {e}")
        flash('承認詳細の取得に失敗しました。', 'error')
        return redirect(url_for('approval_system.teacher_pending_approvals'))


@approval_bp.route('/teacher/approve/<int:request_id>', methods=['POST'])
@login_required
@teacher_required
def teacher_approve_request(request_id):
    """教師による承認処理（タスクベース）"""
    try:
        data = request.get_json()
        comment = data.get('comment', '')
        request_type = data.get('type', 'task_completion')  # デフォルトはタスク
        
        if request_type == 'task_completion':
            success = ApprovalService.approve_task(
                request_id, current_user.id, comment
            )
        else:
            # 従来の単元承認
            success = ApprovalService.approve_request(
                request_id, current_user.id, comment
            )
        
        if success:
            return jsonify({
                'success': True,
                'message': '承認しました。'
            })
        else:
            return jsonify({
                'success': False,
                'message': '承認処理に失敗しました。'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error in teacher_approve_request: {e}")
        return jsonify({
            'success': False,
            'message': 'エラーが発生しました。'
        }), 500


@approval_bp.route('/teacher/reject/<int:request_id>', methods=['POST'])
@login_required
@teacher_required
def teacher_reject_request(request_id):
    """教師による却下処理（タスクベース）"""
    try:
        data = request.get_json()
        comment = data.get('comment', '')
        request_type = data.get('type', 'task_completion')  # デフォルトはタスク
        
        if not comment:
            return jsonify({
                'success': False,
                'message': '却下理由を入力してください。'
            }), 400
        
        if request_type == 'task_completion':
            success = ApprovalService.reject_task(
                request_id, current_user.id, comment
            )
        else:
            # 従来の単元却下
            success = ApprovalService.reject_request(
                request_id, current_user.id, comment
            )
        
        if success:
            return jsonify({
                'success': True,
                'message': '却下しました。'
            })
        else:
            return jsonify({
                'success': False,
                'message': '却下処理に失敗しました。'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error in teacher_reject_request: {e}")
        return jsonify({
            'success': False,
            'message': 'エラーが発生しました。'
        }), 500


# === 学生向けAPIルート ===

@approval_bp.route('/api/request-completion', methods=['POST'])
@login_required
@student_required
def request_completion():
    """学習完了申請API"""
    try:
        data = request.get_json()
        unit_id = data.get('unit_id')
        
        if not unit_id:
            return jsonify({'success': False, 'message': '単元IDが必要です。'}), 400
        
        success = ApprovalService.request_completion(
            current_user.id, unit_id, data
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': '完了申請を送信しました。'
            })
        else:
            return jsonify({
                'success': False,
                'message': '申請に失敗しました。進捗率を確認してください。'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error in request_completion: {e}")
        return jsonify({
            'success': False,
            'message': 'エラーが発生しました。'
        }), 500


@approval_bp.route('/api/resubmit-completion', methods=['POST'])
@login_required
@student_required
def resubmit_completion():
    """再申請API"""
    try:
        data = request.get_json()
        unit_id = data.get('unit_id')
        
        if not unit_id:
            return jsonify({'success': False, 'message': '単元IDが必要です。'}), 400
        
        success = ApprovalService.resubmit_completion(
            current_user.id, unit_id, data
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': '再申請を送信しました。'
            })
        else:
            return jsonify({
                'success': False,
                'message': '再申請に失敗しました。'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error in resubmit_completion: {e}")
        return jsonify({
            'success': False,
            'message': 'エラーが発生しました。'
        }), 500


# === 教師向け一括処理・統計API ===

@approval_bp.route('/teacher/batch-approve', methods=['POST'])
@login_required
@teacher_required
def batch_approve():
    """一括承認処理"""
    try:
        data = request.get_json()
        request_ids = data.get('request_ids', [])
        comment = data.get('comment', '一括承認')
        
        if not request_ids:
            return jsonify({
                'success': False,
                'message': '承認する申請を選択してください。'
            }), 400
        
        approved_count = 0
        failed_count = 0
        
        for request_id in request_ids:
            try:
                success = ApprovalService.approve_task(
                    request_id, current_user.id, comment
                )
                if success:
                    approved_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                current_app.logger.error(f"Error approving request {request_id}: {e}")
                failed_count += 1
        
        return jsonify({
            'success': True,
            'message': f'{approved_count}件の申請を承認しました。',
            'approved_count': approved_count,
            'failed_count': failed_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in batch_approve: {e}")
        return jsonify({
            'success': False,
            'message': 'エラーが発生しました。'
        }), 500


@approval_bp.route('/api/statistics')
@login_required
@teacher_required
def get_statistics():
    """承認統計API"""
    try:
        class_id = request.args.get('class_id', type=int)
        
        # 統計データを取得
        statistics = ApprovalService.get_approval_statistics(class_id)
        
        return jsonify({
            'success': True,
            'statistics': statistics
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_statistics: {e}")
        return jsonify({
            'success': False,
            'message': 'エラーが発生しました。'
        }), 500