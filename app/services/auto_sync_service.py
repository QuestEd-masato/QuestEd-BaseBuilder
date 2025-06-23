"""
自動同期サービス

カリキュラム更新時の自動同期、変更検知、競合解決機能を提供します。
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy import and_, or_, func, text
from flask import current_app
import json
import logging
import hashlib
from enum import Enum

from extensions import db
from app.models import (
    Curriculum, CurriculumUnit, User, Class,
    StudentUnitSelection
)
from app.services.curriculum_bridge_service import CurriculumBridgeService

logger = logging.getLogger(__name__)


class SyncTriggerType(Enum):
    """同期トリガーの種類"""
    MANUAL = "manual"           # 手動同期
    AUTO_UPDATE = "auto_update" # 自動更新
    SCHEDULED = "scheduled"     # スケジュール同期
    CONFLICT_RESOLUTION = "conflict_resolution"  # 競合解決


class SyncStatus(Enum):
    """同期ステータス"""
    PENDING = "pending"         # 待機中
    IN_PROGRESS = "in_progress" # 実行中
    COMPLETED = "completed"     # 完了
    FAILED = "failed"          # 失敗
    CONFLICT = "conflict"      # 競合


class ChangeType(Enum):
    """変更タイプ"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"


class AutoSyncService:
    """自動同期サービス"""
    
    # 自動同期設定のデフォルト値
    DEFAULT_SYNC_SETTINGS = {
        'auto_sync_enabled': True,
        'sync_on_curriculum_update': True,
        'sync_on_item_change': True,
        'conflict_resolution_strategy': 'prompt',  # 'auto', 'prompt', 'manual'
        'sync_delay_minutes': 5,  # 変更から同期までの遅延
        'batch_sync_window': 30,  # バッチ同期のウィンドウ（分）
    }
    
    @classmethod
    def enable_auto_sync_for_curriculum(cls, curriculum_id: int, user_id: int) -> Dict[str, Any]:
        """カリキュラムの自動同期を有効化"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {'success': False, 'message': 'カリキュラムが見つかりません'}
            
            # 権限チェック
            if curriculum.teacher_id != user_id:
                return {'success': False, 'message': '権限がありません'}
            
            # 自動同期設定を追加/更新
            sync_settings = cls.DEFAULT_SYNC_SETTINGS.copy()
            sync_settings['enabled_by'] = user_id
            sync_settings['enabled_at'] = datetime.utcnow().isoformat()
            
            # curriculum_dataに同期設定を保存
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            curriculum_data['auto_sync_settings'] = sync_settings
            curriculum.curriculum_data = json.dumps(curriculum_data, ensure_ascii=False)
            
            db.session.commit()
            
            logger.info(f"Auto sync enabled for curriculum {curriculum_id} by user {user_id}")
            return {
                'success': True,
                'message': '自動同期が有効になりました',
                'settings': sync_settings
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Enable auto sync error: {str(e)}", exc_info=True)
            return {'success': False, 'message': f'自動同期の有効化に失敗しました: {str(e)}'}
    
    @classmethod
    def detect_curriculum_changes(cls, curriculum_id: int) -> Dict[str, Any]:
        """カリキュラムの変更を検知"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {'has_changes': False, 'error': 'カリキュラムが見つかりません'}
            
            # 現在のカリキュラムデータのハッシュ計算
            current_data = curriculum.curriculum_data or ''
            current_hash = hashlib.md5(current_data.encode('utf-8')).hexdigest()
            
            # 最後の同期時のハッシュと比較
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            last_sync_hash = curriculum_data.get('last_sync_hash', '')
            
            changes_detected = current_hash != last_sync_hash
            
            # 変更詳細の分析
            change_details = []
            if changes_detected:
                change_details = cls._analyze_curriculum_changes(curriculum_id, curriculum_data)
            
            return {
                'has_changes': changes_detected,
                'current_hash': current_hash,
                'last_sync_hash': last_sync_hash,
                'changes': change_details,
                'last_sync_date': curriculum_data.get('last_sync_date'),
                'auto_sync_enabled': curriculum_data.get('auto_sync_settings', {}).get('auto_sync_enabled', False)
            }
            
        except Exception as e:
            logger.error(f"Change detection error: {str(e)}", exc_info=True)
            return {'has_changes': False, 'error': str(e)}
    
    @classmethod
    def _analyze_curriculum_changes(cls, curriculum_id: int, curriculum_data: Dict) -> List[Dict]:
        """カリキュラム変更の詳細分析"""
        changes = []
        
        try:
            # 現在のアイテム
            current_items = curriculum_data.get('items', [])
            
            # 前回のアイテム（同期ログから取得）
            last_items = curriculum_data.get('last_sync_items', [])
            
            # アイテムの比較
            current_titles = {item.get('activity', ''): idx for idx, item in enumerate(current_items)}
            last_titles = {item.get('activity', ''): idx for idx, item in enumerate(last_items)}
            
            # 新規追加の検出
            for title, idx in current_titles.items():
                if title and title not in last_titles:
                    changes.append({
                        'type': ChangeType.CREATE.value,
                        'description': f'新しい項目が追加されました: {title[:50]}',
                        'index': idx,
                        'affected_units': 0  # 計算必要
                    })
            
            # 削除の検出
            for title, idx in last_titles.items():
                if title and title not in current_titles:
                    changes.append({
                        'type': ChangeType.DELETE.value,
                        'description': f'項目が削除されました: {title[:50]}',
                        'index': idx,
                        'affected_units': 1
                    })
            
            # 更新の検出
            for title in current_titles:
                if title in last_titles:
                    current_idx = current_titles[title]
                    last_idx = last_titles[title]
                    
                    current_item = current_items[current_idx] if current_idx < len(current_items) else {}
                    last_item = last_items[last_idx] if last_idx < len(last_items) else {}
                    
                    # 内容の比較
                    if json.dumps(current_item, sort_keys=True) != json.dumps(last_item, sort_keys=True):
                        changes.append({
                            'type': ChangeType.UPDATE.value,
                            'description': f'項目が更新されました: {title[:50]}',
                            'index': current_idx,
                            'affected_units': 1
                        })
                    
                    # 位置の変更
                    if current_idx != last_idx:
                        changes.append({
                            'type': ChangeType.MOVE.value,
                            'description': f'項目の順序が変更されました: {title[:50]}',
                            'from_index': last_idx,
                            'to_index': current_idx,
                            'affected_units': 1
                        })
            
        except Exception as e:
            logger.error(f"Change analysis error: {str(e)}", exc_info=True)
            changes.append({
                'type': 'error',
                'description': f'変更分析中にエラーが発生しました: {str(e)}',
                'affected_units': 0
            })
        
        return changes
    
    @classmethod
    def should_auto_sync(cls, curriculum_id: int) -> Tuple[bool, Dict[str, Any]]:
        """自動同期すべきかどうかを判定"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return False, {'reason': 'カリキュラムが見つかりません'}
            
            # 自動同期設定を取得
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            sync_settings = curriculum_data.get('auto_sync_settings', {})
            
            if not sync_settings.get('auto_sync_enabled', False):
                return False, {'reason': '自動同期が無効です'}
            
            # 変更検知
            change_result = cls.detect_curriculum_changes(curriculum_id)
            if not change_result.get('has_changes', False):
                return False, {'reason': '変更がありません'}
            
            # 遅延チェック
            last_update = curriculum.updated_at
            sync_delay = sync_settings.get('sync_delay_minutes', 5)
            delay_threshold = datetime.utcnow() - timedelta(minutes=sync_delay)
            
            if last_update > delay_threshold:
                return False, {
                    'reason': f'遅延期間中です（{sync_delay}分）',
                    'retry_after': (last_update + timedelta(minutes=sync_delay)).isoformat()
                }
            
            # 既存の同期中プロセスチェック
            if cls._is_sync_in_progress(curriculum_id):
                return False, {'reason': '同期処理が実行中です'}
            
            return True, {
                'reason': '自動同期の条件を満たしています',
                'changes': change_result.get('changes', []),
                'sync_settings': sync_settings
            }
            
        except Exception as e:
            logger.error(f"Auto sync check error: {str(e)}", exc_info=True)
            return False, {'reason': f'チェック中にエラーが発生しました: {str(e)}'}
    
    @classmethod
    def execute_auto_sync(cls, curriculum_id: int, trigger_type: SyncTriggerType = SyncTriggerType.AUTO_UPDATE) -> Dict[str, Any]:
        """自動同期の実行"""
        sync_log_id = None
        try:
            # 同期ログの開始
            sync_log_id = cls._create_sync_log(curriculum_id, trigger_type)
            
            # 同期前の状態保存
            pre_sync_state = cls._capture_curriculum_state(curriculum_id)
            
            # 競合チェック
            conflict_result = cls._check_for_conflicts(curriculum_id)
            if conflict_result['has_conflicts']:
                return cls._handle_conflicts(curriculum_id, conflict_result, sync_log_id)
            
            # 実際の同期実行
            curriculum = Curriculum.query.get(curriculum_id)
            sync_result = CurriculumBridgeService.convert_curriculum_to_units(
                curriculum_id, curriculum.teacher_id
            )
            
            if sync_result['success']:
                # 同期成功時の処理
                cls._update_sync_metadata(curriculum_id, sync_result)
                cls._complete_sync_log(sync_log_id, SyncStatus.COMPLETED, sync_result)
                
                # リアルタイム通知
                cls._send_sync_notification(curriculum_id, 'success', sync_result)
                
                logger.info(f"Auto sync completed for curriculum {curriculum_id}")
                return {
                    'success': True,
                    'message': '自動同期が完了しました',
                    'sync_result': sync_result,
                    'sync_log_id': sync_log_id
                }
            else:
                # 同期失敗時の処理
                cls._complete_sync_log(sync_log_id, SyncStatus.FAILED, sync_result)
                return {
                    'success': False,
                    'message': f'自動同期に失敗しました: {sync_result.get("message", "不明なエラー")}',
                    'sync_log_id': sync_log_id
                }
                
        except Exception as e:
            # エラー時の処理
            if sync_log_id:
                cls._complete_sync_log(sync_log_id, SyncStatus.FAILED, {'error': str(e)})
            
            logger.error(f"Auto sync execution error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'自動同期の実行中にエラーが発生しました: {str(e)}',
                'sync_log_id': sync_log_id
            }
    
    @classmethod
    def _check_for_conflicts(cls, curriculum_id: int) -> Dict[str, Any]:
        """競合チェック"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            
            # 同時編集チェック
            recent_updates = db.session.query(Curriculum).filter(
                and_(
                    Curriculum.id == curriculum_id,
                    Curriculum.updated_at > datetime.utcnow() - timedelta(minutes=5)
                )
            ).count()
            
            # 関連単元の学習中学生チェック
            active_learning = db.session.query(StudentUnitSelection).join(CurriculumUnit).filter(
                and_(
                    CurriculumUnit.legacy_curriculum_id == curriculum_id,
                    StudentUnitSelection.status == 'in_progress'
                )
            ).count()
            
            conflicts = []
            
            if recent_updates > 1:
                conflicts.append({
                    'type': 'concurrent_edit',
                    'description': '複数の同時編集が検出されました',
                    'severity': 'medium'
                })
            
            if active_learning > 0:
                conflicts.append({
                    'type': 'active_learning',
                    'description': f'{active_learning}名の学生が関連単元を学習中です',
                    'severity': 'low',
                    'affected_students': active_learning
                })
            
            return {
                'has_conflicts': len(conflicts) > 0,
                'conflicts': conflicts,
                'conflict_count': len(conflicts)
            }
            
        except Exception as e:
            logger.error(f"Conflict check error: {str(e)}", exc_info=True)
            return {
                'has_conflicts': True,
                'conflicts': [{'type': 'error', 'description': str(e), 'severity': 'high'}],
                'error': str(e)
            }
    
    @classmethod
    def _handle_conflicts(cls, curriculum_id: int, conflict_result: Dict, sync_log_id: str) -> Dict[str, Any]:
        """競合の処理"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            sync_settings = curriculum_data.get('auto_sync_settings', {})
            
            resolution_strategy = sync_settings.get('conflict_resolution_strategy', 'prompt')
            
            if resolution_strategy == 'auto':
                # 自動解決
                return cls._auto_resolve_conflicts(curriculum_id, conflict_result, sync_log_id)
            elif resolution_strategy == 'prompt':
                # ユーザーに確認を要求
                cls._complete_sync_log(sync_log_id, SyncStatus.CONFLICT, conflict_result)
                return {
                    'success': False,
                    'requires_user_action': True,
                    'message': '競合が検出されました。手動で解決してください。',
                    'conflicts': conflict_result['conflicts'],
                    'sync_log_id': sync_log_id
                }
            else:
                # 手動解決待ち
                cls._complete_sync_log(sync_log_id, SyncStatus.CONFLICT, conflict_result)
                return {
                    'success': False,
                    'message': '競合が検出されたため、同期を一時停止しました。',
                    'conflicts': conflict_result['conflicts'],
                    'sync_log_id': sync_log_id
                }
                
        except Exception as e:
            logger.error(f"Conflict handling error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'競合処理中にエラーが発生しました: {str(e)}'
            }
    
    @classmethod
    def _auto_resolve_conflicts(cls, curriculum_id: int, conflict_result: Dict, sync_log_id: str) -> Dict[str, Any]:
        """競合の自動解決"""
        try:
            resolved_conflicts = []
            
            for conflict in conflict_result['conflicts']:
                if conflict['type'] == 'active_learning':
                    # 学習中の学生がいる場合は同期を延期
                    if conflict['severity'] == 'low' and conflict.get('affected_students', 0) < 5:
                        # 少数の学生の場合は続行
                        resolved_conflicts.append({
                            'conflict': conflict,
                            'resolution': 'continue',
                            'reason': '影響が軽微なため続行'
                        })
                    else:
                        # 多数の学生の場合は延期
                        return {
                            'success': False,
                            'message': '多数の学生が学習中のため、同期を延期しました。',
                            'auto_retry_after': (datetime.utcnow() + timedelta(hours=1)).isoformat()
                        }
                
                elif conflict['type'] == 'concurrent_edit':
                    # 同時編集の場合は最新を優先
                    resolved_conflicts.append({
                        'conflict': conflict,
                        'resolution': 'latest_wins',
                        'reason': '最新の編集を優先'
                    })
            
            # 解決された競合をログに記録
            resolution_result = {
                'resolved_conflicts': resolved_conflicts,
                'resolution_strategy': 'auto',
                'resolved_at': datetime.utcnow().isoformat()
            }
            
            # 同期続行
            curriculum = Curriculum.query.get(curriculum_id)
            sync_result = CurriculumBridgeService.convert_curriculum_to_units(
                curriculum_id, curriculum.teacher_id
            )
            
            sync_result['conflict_resolution'] = resolution_result
            cls._complete_sync_log(sync_log_id, SyncStatus.COMPLETED, sync_result)
            
            return {
                'success': True,
                'message': '競合を自動解決して同期を完了しました',
                'sync_result': sync_result,
                'conflict_resolution': resolution_result
            }
            
        except Exception as e:
            logger.error(f"Auto conflict resolution error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'自動競合解決中にエラーが発生しました: {str(e)}'
            }
    
    @classmethod
    def _create_sync_log(cls, curriculum_id: int, trigger_type: SyncTriggerType) -> str:
        """同期ログの作成"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            
            sync_log = {
                'id': f"sync_{curriculum_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'curriculum_id': curriculum_id,
                'trigger_type': trigger_type.value,
                'status': SyncStatus.IN_PROGRESS.value,
                'started_at': datetime.utcnow().isoformat(),
                'curriculum_version': curriculum.updated_at.isoformat() if curriculum.updated_at else None
            }
            
            # 同期ログを保存
            sync_logs = curriculum_data.get('sync_logs', [])
            sync_logs.append(sync_log)
            
            # 古いログを削除（最新50件まで保持）
            if len(sync_logs) > 50:
                sync_logs = sync_logs[-50:]
            
            curriculum_data['sync_logs'] = sync_logs
            curriculum.curriculum_data = json.dumps(curriculum_data, ensure_ascii=False)
            db.session.commit()
            
            return sync_log['id']
            
        except Exception as e:
            logger.error(f"Sync log creation error: {str(e)}", exc_info=True)
            return f"error_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    @classmethod
    def _complete_sync_log(cls, sync_log_id: str, status: SyncStatus, result: Dict) -> None:
        """同期ログの完了"""
        try:
            # sync_log_idからcurriculum_idを抽出
            curriculum_id = int(sync_log_id.split('_')[1])
            
            curriculum = Curriculum.query.get(curriculum_id)
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            
            sync_logs = curriculum_data.get('sync_logs', [])
            
            # 該当ログを更新
            for log in sync_logs:
                if log['id'] == sync_log_id:
                    log['status'] = status.value
                    log['completed_at'] = datetime.utcnow().isoformat()
                    log['result'] = result
                    break
            
            curriculum_data['sync_logs'] = sync_logs
            curriculum.curriculum_data = json.dumps(curriculum_data, ensure_ascii=False)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Sync log completion error: {str(e)}", exc_info=True)
    
    @classmethod
    def _update_sync_metadata(cls, curriculum_id: int, sync_result: Dict) -> None:
        """同期メタデータの更新"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            
            # 同期成功時のメタデータ更新
            current_data = curriculum.curriculum_data or ''
            current_hash = hashlib.md5(current_data.encode('utf-8')).hexdigest()
            
            curriculum_data['last_sync_hash'] = current_hash
            curriculum_data['last_sync_date'] = datetime.utcnow().isoformat()
            curriculum_data['last_sync_items'] = curriculum_data.get('items', []).copy()
            curriculum_data['last_sync_result'] = sync_result
            
            curriculum.curriculum_data = json.dumps(curriculum_data, ensure_ascii=False)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Sync metadata update error: {str(e)}", exc_info=True)
    
    @classmethod
    def _is_sync_in_progress(cls, curriculum_id: int) -> bool:
        """同期中かどうかをチェック"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            
            sync_logs = curriculum_data.get('sync_logs', [])
            
            # 最新の同期ログをチェック
            for log in reversed(sync_logs):
                if log.get('status') == SyncStatus.IN_PROGRESS.value:
                    # 開始から30分以上経過している場合は異常終了とみなす
                    started_at = datetime.fromisoformat(log['started_at'])
                    if datetime.utcnow() - started_at > timedelta(minutes=30):
                        # 異常終了として処理
                        log['status'] = SyncStatus.FAILED.value
                        log['completed_at'] = datetime.utcnow().isoformat()
                        log['result'] = {'error': 'タイムアウト'}
                        
                        curriculum.curriculum_data = json.dumps(curriculum_data, ensure_ascii=False)
                        db.session.commit()
                        return False
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Sync progress check error: {str(e)}", exc_info=True)
            return False
    
    @classmethod
    def _capture_curriculum_state(cls, curriculum_id: int) -> Dict[str, Any]:
        """カリキュラムの現在状態をキャプチャ"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            units = CurriculumUnit.query.filter_by(
                legacy_curriculum_id=curriculum_id,
                is_active=True
            ).all()
            
            return {
                'curriculum_updated_at': curriculum.updated_at.isoformat() if curriculum.updated_at else None,
                'curriculum_data_hash': hashlib.md5((curriculum.curriculum_data or '').encode('utf-8')).hexdigest(),
                'units_count': len(units),
                'units_data': [
                    {
                        'id': unit.id,
                        'title': unit.title,
                        'updated_at': unit.updated_at.isoformat() if unit.updated_at else None
                    }
                    for unit in units
                ]
            }
            
        except Exception as e:
            logger.error(f"State capture error: {str(e)}", exc_info=True)
            return {'error': str(e)}
    
    @classmethod
    def _send_sync_notification(cls, curriculum_id: int, status: str, result: Dict) -> None:
        """同期通知の送信（将来のWebSocket実装用）"""
        try:
            # 現在はログ出力のみ（将来WebSocketで実装）
            logger.info(f"Sync notification: curriculum_id={curriculum_id}, status={status}")
            
            # 将来の実装：
            # - WebSocketでリアルタイム通知
            # - メール通知
            # - システム内通知
            
        except Exception as e:
            logger.error(f"Sync notification error: {str(e)}", exc_info=True)
    
    @classmethod
    def get_sync_history(cls, curriculum_id: int, limit: int = 20) -> List[Dict]:
        """同期履歴の取得"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return []
            
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            sync_logs = curriculum_data.get('sync_logs', [])
            
            # 最新のものから返す
            return list(reversed(sync_logs))[:limit]
            
        except Exception as e:
            logger.error(f"Sync history retrieval error: {str(e)}", exc_info=True)
            return []
    
    @classmethod
    def get_sync_settings(cls, curriculum_id: int) -> Dict[str, Any]:
        """同期設定の取得"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return cls.DEFAULT_SYNC_SETTINGS.copy()
            
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            sync_settings = curriculum_data.get('auto_sync_settings', {})
            
            # デフォルト設定とマージ
            result = cls.DEFAULT_SYNC_SETTINGS.copy()
            result.update(sync_settings)
            
            return result
            
        except Exception as e:
            logger.error(f"Sync settings retrieval error: {str(e)}", exc_info=True)
            return cls.DEFAULT_SYNC_SETTINGS.copy()
    
    @classmethod
    def update_sync_settings(cls, curriculum_id: int, settings: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """同期設定の更新"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {'success': False, 'message': 'カリキュラムが見つかりません'}
            
            # 権限チェック
            if curriculum.teacher_id != user_id:
                return {'success': False, 'message': '権限がありません'}
            
            curriculum_data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            current_settings = curriculum_data.get('auto_sync_settings', {})
            
            # 設定を更新
            current_settings.update(settings)
            current_settings['updated_by'] = user_id
            current_settings['updated_at'] = datetime.utcnow().isoformat()
            
            curriculum_data['auto_sync_settings'] = current_settings
            curriculum.curriculum_data = json.dumps(curriculum_data, ensure_ascii=False)
            
            db.session.commit()
            
            logger.info(f"Sync settings updated for curriculum {curriculum_id} by user {user_id}")
            return {
                'success': True,
                'message': '同期設定が更新されました',
                'settings': current_settings
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Sync settings update error: {str(e)}", exc_info=True)
            return {'success': False, 'message': f'設定更新に失敗しました: {str(e)}'}