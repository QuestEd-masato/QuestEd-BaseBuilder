"""
承認システム ルーティング（簡易版）

3状態管理のAPIエンドポイント
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user

from app.utils.decorators import student_required, teacher_required
from ..services.approval_service import ApprovalService

approval_bp = Blueprint('approval_system', __name__, url_prefix='/approval-system')


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