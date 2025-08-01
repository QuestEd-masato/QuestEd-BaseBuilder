# app/auth/mfa_routes.py
"""
Multi-Factor Authentication Routes
MFA認証関連のWebルーティング

機能:
- MFA設定画面
- MFA認証画面
- バックアップコード管理
- 信頼済みデバイス管理
"""

import logging
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required

from app.auth.mfa import MFAService, is_mfa_enabled, is_mfa_required
from app.models import User, db
from app.utils.mfa_decorators import (
    admin_mfa_required,
    clear_mfa_verification,
    get_mfa_redirect_url,
    mark_mfa_verified,
    mfa_setup_required,
    sensitive_operation_mfa,
)
from app.utils.rate_limiting import auth_limit

logger = logging.getLogger(__name__)

# Blueprintを作成
mfa_bp = Blueprint('mfa', __name__, url_prefix='/mfa')
mfa_service = MFAService()


@mfa_bp.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    """MFA設定画面"""
    try:
        if request.method == 'GET':
            # MFA設定状況を確認
            mfa_status = mfa_service.get_mfa_status(current_user.id)
            
            if mfa_status.get('enabled'):
                flash('多要素認証は既に設定済みです。', 'info')
                return redirect(url_for('mfa.manage'))
            
            # 新規設定開始
            setup_data = mfa_service.setup_mfa_for_user(current_user.id)
            
            return render_template(
                'mfa/setup.html',
                qr_code=setup_data['qr_code'],
                secret=setup_data['secret'],
                backup_codes=setup_data['backup_codes'],
                is_required=is_mfa_required(current_user)
            )
        
        elif request.method == 'POST':
            # 設定完了の検証
            totp_code = request.form.get('totp_code', '').strip()
            
            if not totp_code:
                flash('認証コードを入力してください。', 'error')
                return redirect(url_for('mfa.setup'))
            
            # TOTP検証してMFA有効化
            if mfa_service.verify_and_enable_mfa(current_user.id, totp_code):
                flash('多要素認証の設定が完了しました！', 'success')
                
                # 設定後は認証済み状態にする
                mark_mfa_verified(current_user.id)
                
                # リダイレクト先を決定
                if current_user.role == 'admin':
                    return redirect(url_for('admin_panel.dashboard'))
                elif current_user.role == 'teacher':
                    return redirect(url_for('teacher_dashboard.dashboard'))
                else:
                    return redirect(url_for('student_dashboard.dashboard'))
            else:
                flash('認証コードが正しくありません。もう一度お試しください。', 'error')
                return redirect(url_for('mfa.setup'))
    
    except Exception as e:
        logger.error(f"MFA setup error for user {current_user.id}: {e}")
        flash('設定中にエラーが発生しました。しばらく後でお試しください。', 'error')
        return redirect(url_for('index'))


@mfa_bp.route('/verify', methods=['GET', 'POST'])
@login_required
@auth_limit()
def verify():
    """MFA認証画面"""
    try:
        # MFAが無効な場合は設定画面へ
        if not is_mfa_enabled(current_user):
            if is_mfa_required(current_user):
                flash('多要素認証の設定が必要です。', 'warning')
                return redirect(url_for('mfa.setup'))
            else:
                flash('多要素認証が有効になっていません。', 'info')
                return redirect(url_for('index'))
        
        if request.method == 'GET':
            # MFA状態を取得
            mfa_status = mfa_service.get_mfa_status(current_user.id)
            
            if mfa_status.get('is_locked'):
                flash('アカウントが一時的にロックされています。しばらく後でお試しください。', 'error')
                return redirect(url_for('index'))
            
            return render_template(
                'mfa/verify.html',
                backup_codes_remaining=mfa_status.get('backup_codes_remaining', 0),
                failed_attempts=mfa_status.get('failed_attempts', 0)
            )
        
        elif request.method == 'POST':
            # 認証コード検証
            code = request.form.get('code', '').strip()
            trust_device = request.form.get('trust_device') == 'on'
            
            if not code:
                flash('認証コードを入力してください。', 'error')
                return redirect(url_for('mfa.verify'))
            
            # MFA検証
            result = mfa_service.verify_mfa_code(
                current_user.id, 
                code, 
                request.remote_addr
            )
            
            if result['success']:
                # 認証成功
                mark_mfa_verified(current_user.id, trust_device)
                
                # バックアップコード使用の場合は警告
                if 'backup_codes_remaining' in result:
                    remaining = result['backup_codes_remaining']
                    if remaining <= 2:
                        flash(f'バックアップコードの残り数が少なくなっています（残り{remaining}個）。新しいコードを生成することをお勧めします。', 'warning')
                
                # リダイレクト
                redirect_url = get_mfa_redirect_url()
                if redirect_url:
                    return redirect(redirect_url)
                else:
                    # デフォルトのダッシュボードへ
                    if current_user.role == 'admin':
                        return redirect(url_for('admin_panel.dashboard'))
                    elif current_user.role == 'teacher':
                        return redirect(url_for('teacher_dashboard.dashboard'))
                    else:
                        return redirect(url_for('student_dashboard.dashboard'))
            else:
                # 認証失敗
                flash(f'認証に失敗しました: {result.get("error", "不明なエラー")}', 'error')
                return redirect(url_for('mfa.verify'))
    
    except Exception as e:
        logger.error(f"MFA verification error for user {current_user.id}: {e}")
        flash('認証中にエラーが発生しました。しばらく後でお試しください。', 'error')
        return redirect(url_for('index'))


@mfa_bp.route('/manage')
@login_required
def manage():
    """MFA管理画面"""
    try:
        if not is_mfa_enabled(current_user):
            flash('多要素認証が有効になっていません。', 'info')
            return redirect(url_for('mfa.setup'))
        
        # MFA状態を取得
        mfa_status = mfa_service.get_mfa_status(current_user.id)
        
        # 信頼済みデバイス一覧を取得
        from app.models.mfa_models import MFADeviceTrust
        trusted_devices = MFADeviceTrust.query.filter_by(
            user_id=current_user.id,
            is_trusted=True
        ).order_by(MFADeviceTrust.last_used_at.desc()).all()
        
        return render_template(
            'mfa/manage.html',
            mfa_status=mfa_status,
            trusted_devices=trusted_devices,
            is_required=is_mfa_required(current_user)
        )
    
    except Exception as e:
        logger.error(f"MFA manage error for user {current_user.id}: {e}")
        flash('管理画面の読み込み中にエラーが発生しました。', 'error')
        return redirect(url_for('index'))


@mfa_bp.route('/regenerate-backup-codes', methods=['POST'])
@login_required
@sensitive_operation_mfa
def regenerate_backup_codes():
    """バックアップコード再生成"""
    try:
        if not is_mfa_enabled(current_user):
            return jsonify({'success': False, 'error': 'MFA not enabled'}), 400
        
        new_codes = mfa_service.regenerate_backup_codes(current_user.id)
        
        if new_codes:
            return jsonify({
                'success': True,
                'backup_codes': new_codes
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to generate codes'}), 500
    
    except Exception as e:
        logger.error(f"Backup code regeneration error for user {current_user.id}: {e}")
        return jsonify({'success': False, 'error': 'System error'}), 500


@mfa_bp.route('/disable', methods=['POST'])
@login_required
@sensitive_operation_mfa
def disable():
    """MFA無効化"""
    try:
        # 管理者の場合は無効化を制限
        if current_user.role == 'admin':
            return jsonify({
                'success': False, 
                'error': '管理者アカウントのMFA無効化はできません。'
            }), 403
        
        if mfa_service.disable_mfa_for_user(current_user.id):
            clear_mfa_verification()
            flash('多要素認証を無効にしました。', 'info')
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to disable MFA'}), 500
    
    except Exception as e:
        logger.error(f"MFA disable error for user {current_user.id}: {e}")
        return jsonify({'success': False, 'error': 'System error'}), 500


@mfa_bp.route('/revoke-device/<int:device_id>', methods=['POST'])
@login_required
@sensitive_operation_mfa
def revoke_device(device_id):
    """信頼済みデバイスの取り消し"""
    try:
        from app.models.mfa_models import MFADeviceTrust
        
        device = MFADeviceTrust.query.filter_by(
            id=device_id,
            user_id=current_user.id
        ).first()
        
        if not device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        device.revoke_trust()
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Device revocation error for user {current_user.id}: {e}")
        return jsonify({'success': False, 'error': 'System error'}), 500


@mfa_bp.route('/admin/force-setup/<int:user_id>', methods=['POST'])
@login_required
@admin_mfa_required
def admin_force_setup(user_id):
    """管理者：ユーザーのMFA設定強制"""
    try:
        target_user = User.query.get_or_404(user_id)
        
        # MFA強制フラグを設定
        target_user.mfa_enforced = True
        db.session.commit()
        
        logger.info(f"Admin {current_user.id} enforced MFA for user {user_id}")
        
        return jsonify({
            'success': True,
            'message': f'{target_user.display_name}のMFA設定を必須にしました。'
        })
    
    except Exception as e:
        logger.error(f"Admin MFA enforcement error: {e}")
        return jsonify({'success': False, 'error': 'System error'}), 500


@mfa_bp.route('/admin/disable/<int:user_id>', methods=['POST'])
@login_required
@admin_mfa_required
def admin_disable_mfa(user_id):
    """管理者：ユーザーのMFA無効化"""
    try:
        target_user = User.query.get_or_404(user_id)
        
        # 管理者の場合は無効化を制限
        if target_user.role == 'admin':
            return jsonify({
                'success': False, 
                'error': '他の管理者のMFAは無効化できません。'
            }), 403
        
        if mfa_service.disable_mfa_for_user(user_id):
            target_user.mfa_enforced = False
            db.session.commit()
            
            logger.info(f"Admin {current_user.id} disabled MFA for user {user_id}")
            
            return jsonify({
                'success': True,
                'message': f'{target_user.display_name}のMFAを無効化しました。'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to disable MFA'}), 500
    
    except Exception as e:
        logger.error(f"Admin MFA disable error: {e}")
        return jsonify({'success': False, 'error': 'System error'}), 500


# エラーハンドラー
@mfa_bp.errorhandler(429)
def rate_limit_handler(e):
    """レート制限エラーハンドラー"""
    flash('認証試行回数が多すぎます。しばらく待ってから再試行してください。', 'error')
    return redirect(url_for('mfa.verify')), 429