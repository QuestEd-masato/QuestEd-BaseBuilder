# app/teacher/modules/synchronization.py
"""同期管理機能"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
import logging

from app.models import db, Class, Curriculum, CurriculumUnit, BasicKnowledgeItem
from app.services.curriculum_bridge_service import CurriculumBridgeService
from app.services.auto_sync_service import AutoSyncService, SyncTriggerType
from ..common import teacher_required

try:
    from app.services.sync_service import SyncService
except ImportError:
    SyncService = None

synchronization_bp = Blueprint('teacher_synchronization', __name__)

@synchronization_bp.route('/curriculum/<int:curriculum_id>/sync', methods=['POST'])
@login_required
@teacher_required
def manual_sync_curriculum(curriculum_id):
    """カリキュラム手動同期"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash('この同期を実行する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    try:
        # 手動同期実行
        result = AutoSyncService.execute_sync(
            curriculum_id=curriculum_id,
            trigger_type=SyncTriggerType.MANUAL,
            triggered_by=current_user.id
        )
        
        if result['success']:
            flash(f'同期が完了しました。{result["synced_units"]}個の単元が更新されました。', 'success')
        else:
            flash(f'同期に失敗しました: {result["error"]}', 'error')
    
    except Exception as e:
        current_app.logger.error(f"Manual sync error: {str(e)}")
        flash('同期処理中にエラーが発生しました。', 'error')
    
    return redirect(url_for('teacher_curriculum_management.view_curriculum', curriculum_id=curriculum_id))

@synchronization_bp.route('/teacher/sync-all', methods=['POST'])
@login_required
@teacher_required
def sync_all_curriculums():
    """全カリキュラム同期"""
    try:
        # 教師の全カリキュラムを取得
        curriculums = Curriculum.query.filter_by(
            teacher_id=current_user.id,
            is_converted_to_units=True
        ).all()
        
        if not curriculums:
            flash('同期対象のカリキュラムがありません。', 'info')
            return redirect(url_for('teacher_dashboard.dashboard'))
        
        sync_results = []
        success_count = 0
        
        for curriculum in curriculums:
            try:
                result = AutoSyncService.execute_sync(
                    curriculum_id=curriculum.id,
                    trigger_type=SyncTriggerType.BATCH,
                    triggered_by=current_user.id
                )
                
                sync_results.append({
                    'curriculum_id': curriculum.id,
                    'curriculum_title': curriculum.title,
                    'success': result['success'],
                    'synced_units': result.get('synced_units', 0),
                    'error': result.get('error')
                })
                
                if result['success']:
                    success_count += 1
                    
            except Exception as e:
                sync_results.append({
                    'curriculum_id': curriculum.id,
                    'curriculum_title': curriculum.title,
                    'success': False,
                    'error': str(e)
                })
        
        flash(f'{success_count}/{len(curriculums)}個のカリキュラムの同期が完了しました。', 
              'success' if success_count > 0 else 'warning')
        
        # 詳細結果をセッションに保存（必要に応じて）
        session['last_sync_results'] = sync_results
        
    except Exception as e:
        current_app.logger.error(f"Batch sync error: {str(e)}")
        flash('一括同期処理中にエラーが発生しました。', 'error')
    
    return redirect(url_for('teacher_dashboard.dashboard'))

@synchronization_bp.route('/api/curriculum/<int:curriculum_id>/sync-status')
@login_required
@teacher_required
def get_sync_status(curriculum_id):
    """同期ステータス取得"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        # 同期ステータスを取得
        sync_status = AutoSyncService.get_sync_status(curriculum_id)
        
        return jsonify({
            'success': True,
            'status': sync_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'ステータス取得に失敗しました: {str(e)}'
        }), 500

@synchronization_bp.route('/api/curriculum/<int:curriculum_id>/sync-stats')
@login_required
@teacher_required
def get_curriculum_sync_stats(curriculum_id):
    """カリキュラム同期統計取得"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        # 統計情報を生成
        conversion_status = CurriculumBridgeService.get_conversion_status(curriculum_id)
        
        # 関連単元数
        total_units = CurriculumUnit.query.filter_by(
            legacy_curriculum_id=curriculum_id,
            is_active=True
        ).count()
        
        # 最新同期情報
        from app.models import SyncLog
        latest_sync = SyncLog.query.filter_by(
            curriculum_id=curriculum_id
        ).order_by(SyncLog.created_at.desc()).first()
        
        stats = {
            'curriculum_id': curriculum_id,
            'curriculum_title': curriculum.title,
            'is_converted': conversion_status.get('is_converted', False),
            'total_units': total_units,
            'conversion_date': conversion_status.get('conversion_date'),
            'last_sync_date': latest_sync.created_at.isoformat() if latest_sync else None,
            'last_sync_status': latest_sync.status if latest_sync else None,
            'auto_sync_enabled': False  # デフォルト値
        }
        
        # 自動同期設定を確認
        from app.models import AutoSyncSettings
        auto_sync_settings = AutoSyncSettings.query.filter_by(
            curriculum_id=curriculum_id
        ).first()
        
        if auto_sync_settings:
            stats['auto_sync_enabled'] = auto_sync_settings.auto_sync_enabled
            stats['sync_on_curriculum_update'] = auto_sync_settings.sync_on_curriculum_update
            stats['last_sync_at'] = auto_sync_settings.last_sync_at.isoformat() if auto_sync_settings.last_sync_at else None
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'統計取得に失敗しました: {str(e)}'
        }), 500

@synchronization_bp.route('/teacher/integrated-management')
@login_required
@teacher_required
def integrated_management():
    """統合管理ダッシュボード"""
    try:
        # 教師の全クラスとカリキュラムを取得
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
        
        integrated_data = {
            'classes': [],
            'summary': {
                'total_classes': len(classes),
                'total_curriculums': 0,
                'converted_curriculums': 0,
                'total_units': 0,
                'pending_syncs': 0
            }
        }
        
        for class_obj in classes:
            curriculums = Curriculum.query.filter_by(
                class_id=class_obj.id,
                teacher_id=current_user.id
            ).all()
            
            class_data = {
                'class': class_obj,
                'curriculums': [],
                'stats': {
                    'total_curriculums': len(curriculums),
                    'converted_count': 0,
                    'total_units': 0
                }
            }
            
            for curriculum in curriculums:
                conversion_status = CurriculumBridgeService.get_conversion_status(curriculum.id)
                
                curriculum_data = {
                    'curriculum': curriculum,
                    'conversion_status': conversion_status,
                    'sync_needed': False  # 同期が必要かどうか
                }
                
                # 統計更新
                if conversion_status.get('is_converted', False):
                    class_data['stats']['converted_count'] += 1
                    class_data['stats']['total_units'] += conversion_status.get('converted_units', 0)
                
                class_data['curriculums'].append(curriculum_data)
            
            # 全体統計に加算
            integrated_data['summary']['total_curriculums'] += class_data['stats']['total_curriculums']
            integrated_data['summary']['converted_curriculums'] += class_data['stats']['converted_count']
            integrated_data['summary']['total_units'] += class_data['stats']['total_units']
            
            integrated_data['classes'].append(class_data)
        
        return render_template('teacher/integrated_management.html', 
                             integrated_data=integrated_data)
        
    except Exception as e:
        current_app.logger.error(f"Integrated management error: {str(e)}")
        flash('統合管理画面の読み込みに失敗しました。', 'error')
        return redirect(url_for('teacher_dashboard.dashboard'))

@synchronization_bp.route('/api/teacher/realtime-stats')
@login_required
@teacher_required
def get_realtime_stats():
    """リアルタイム統計取得"""
    try:
        # リアルタイム接続統計（仮の実装）
        stats = {
            'connected_users': 0,  # WebSocket接続ユーザー数
            'active_syncs': 0,     # アクティブな同期数
            'completed_syncs_today': 0,  # 今日完了した同期数
            'sync_conflicts': 0    # 同期競合数
        }
        
        # 実際の統計データを取得する場合の実装例
        # if hasattr(current_app, 'socketio'):
        #     stats['connected_users'] = len(current_app.socketio.server.manager.rooms.get('/', {}).get('teacher_' + str(current_user.id), []))
        
        # 今日の同期ログ数を取得
        from app.models import SyncLog
        from datetime import date
        
        today_syncs = SyncLog.query.filter(
            SyncLog.created_at >= datetime.combine(date.today(), datetime.min.time())
        ).join(Curriculum).filter(
            Curriculum.teacher_id == current_user.id
        ).count()
        
        stats['completed_syncs_today'] = today_syncs
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'統計取得に失敗しました: {str(e)}'
        }), 500

@synchronization_bp.route('/api/teacher/sync-overview-stats')
@login_required
@teacher_required
def get_sync_overview_stats():
    """同期概要統計取得"""
    try:
        # 教師のカリキュラム統計
        total_curriculums = Curriculum.query.filter_by(
            teacher_id=current_user.id
        ).count()
        
        converted_curriculums = Curriculum.query.filter_by(
            teacher_id=current_user.id,
            is_converted_to_units=True
        ).count()
        
        total_units = CurriculumUnit.query.filter_by(
            created_by=current_user.id,
            is_active=True
        ).count()
        
        # 最近の同期活動
        from app.models import SyncLog
        recent_syncs = SyncLog.query.join(Curriculum).filter(
            Curriculum.teacher_id == current_user.id
        ).order_by(SyncLog.created_at.desc()).limit(5).all()
        
        recent_activity = []
        for sync_log in recent_syncs:
            recent_activity.append({
                'curriculum_title': sync_log.curriculum.title,
                'status': sync_log.status,
                'trigger_type': sync_log.trigger_type,
                'created_at': sync_log.created_at.strftime('%Y-%m-%d %H:%M'),
                'message': sync_log.message
            })
        
        stats = {
            'total_curriculums': total_curriculums,
            'converted_curriculums': converted_curriculums,
            'total_units': total_units,
            'conversion_rate': round((converted_curriculums / total_curriculums) * 100, 1) if total_curriculums > 0 else 0,
            'recent_activity': recent_activity
        }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'概要統計取得に失敗しました: {str(e)}'
        }), 500

@synchronization_bp.route('/curriculum/<int:curriculum_id>/auto-sync-settings', methods=['GET', 'POST'])
@login_required
@teacher_required
def auto_sync_settings(curriculum_id):
    """自動同期設定管理"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash('この設定を変更する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    from app.models import AutoSyncSettings
    
    # 現在の設定を取得
    settings = AutoSyncSettings.query.filter_by(curriculum_id=curriculum_id).first()
    
    if request.method == 'POST':
        try:
            if not settings:
                settings = AutoSyncSettings(curriculum_id=curriculum_id)
                db.session.add(settings)
            
            # 設定更新
            settings.auto_sync_enabled = request.form.get('auto_sync_enabled') == 'on'
            settings.sync_on_curriculum_update = request.form.get('sync_on_curriculum_update') == 'on'
            settings.sync_on_item_change = request.form.get('sync_on_item_change') == 'on'
            
            # 競合解決戦略
            conflict_resolution = request.form.get('conflict_resolution_strategy', 'manual')
            if conflict_resolution in ['manual', 'auto_curriculum', 'auto_items']:
                settings.conflict_resolution_strategy = conflict_resolution
            
            # 同期遅延設定
            sync_delay = request.form.get('sync_delay_minutes', 5, type=int)
            if 0 <= sync_delay <= 60:
                settings.sync_delay_minutes = sync_delay
            
            db.session.commit()
            flash('自動同期設定が更新されました。', 'success')
            
            return redirect(url_for('teacher_curriculum_management.view_curriculum', curriculum_id=curriculum_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Auto sync settings update error: {str(e)}")
            flash('設定の更新に失敗しました。', 'error')
    
    return render_template('auto_sync_settings.html', 
                         curriculum=curriculum,
                         settings=settings)

@synchronization_bp.route('/api/curriculum/<int:curriculum_id>/problems')
@login_required
@teacher_required  
def get_curriculum_problems(curriculum_id):
    """カリキュラム関連問題取得"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        # カリキュラムに関連する問題を取得
        # 教科と難易度に基づいて関連問題を検索
        problems = BasicKnowledgeItem.query.filter_by(
            subject_id=curriculum.subject_id
        ).limit(50).all()
        
        problem_data = []
        for problem in problems:
            problem_data.append({
                'id': problem.id,
                'question': problem.question,
                'difficulty_level': problem.difficulty_level,
                'category': problem.category.name if problem.category else 'なし'
            })
        
        return jsonify({
            'success': True,
            'problems': problem_data,
            'total_count': len(problem_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'問題取得に失敗しました: {str(e)}'
        }), 500