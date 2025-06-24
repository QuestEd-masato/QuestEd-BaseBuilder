"""
リアルタイム同期システム

WebSocketを使用してカリキュラム・単元の同期状況をリアルタイムで通知
"""
from flask import Blueprint
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_login import current_user, login_required
import logging
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# SocketIOインスタンス（app/__init__.pyで初期化される）
socketio = None

realtime_bp = Blueprint('realtime', __name__)

# 接続されているユーザーの管理
connected_users = {}  # user_id -> {'sid': session_id, 'rooms': [room_list]}


def init_socketio(app):
    """SocketIOの初期化"""
    global socketio
    from flask_socketio import SocketIO
    
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='threading',
        logger=True,
        engineio_logger=True
    )
    
    # イベントハンドラーの登録
    register_socketio_events()
    
    logger.info("SocketIO initialized for real-time sync system")
    return socketio


def register_socketio_events():
    """SocketIOイベントハンドラーの登録"""
    
    @socketio.on('connect')
    def handle_connect():
        """クライアント接続時の処理"""
        if current_user.is_authenticated:
            user_id = current_user.id
            from flask import request
            session_id = request.sid
            
            connected_users[user_id] = {
                'sid': session_id,
                'rooms': [],
                'user_type': current_user.role,
                'connected_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"User {user_id} ({current_user.role}) connected: {session_id}")
            
            # ユーザータイプに応じたルームに参加
            if current_user.role == 'teacher':
                join_room(f"teacher_{user_id}")
                connected_users[user_id]['rooms'].append(f"teacher_{user_id}")
            elif current_user.role == 'student':
                join_room(f"student_{user_id}")
                connected_users[user_id]['rooms'].append(f"student_{user_id}")
                
                # 学生の場合、所属クラスのルームにも参加
                from app.models import ClassEnrollment
                enrollments = ClassEnrollment.query.filter_by(student_id=user_id).all()
                for enrollment in enrollments:
                    class_room = f"class_{enrollment.class_id}"
                    join_room(class_room)
                    connected_users[user_id]['rooms'].append(class_room)
            
            # 接続確認を送信
            emit('sync_status', {
                'type': 'connection_established',
                'message': 'リアルタイム同期に接続しました',
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            logger.warning("Unauthenticated user attempted to connect")
            disconnect()
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """クライアント切断時の処理"""
        if current_user.is_authenticated:
            user_id = current_user.id
            if user_id in connected_users:
                session_id = connected_users[user_id]['sid']
                rooms = connected_users[user_id]['rooms']
                
                # 全ルームから退出
                for room in rooms:
                    leave_room(room)
                
                del connected_users[user_id]
                logger.info(f"User {user_id} disconnected: {session_id}")
    
    @socketio.on('join_curriculum_sync')
    def handle_join_curriculum_sync(data):
        """特定のカリキュラム同期ルームに参加"""
        if not current_user.is_authenticated:
            return
            
        curriculum_id = data.get('curriculum_id')
        if not curriculum_id:
            return
            
        # 権限チェック
        from app.models import Curriculum, ClassEnrollment
        
        if current_user.role == 'teacher':
            # 教師は自分のカリキュラムのみ
            curriculum = Curriculum.query.filter_by(
                id=curriculum_id, 
                teacher_id=current_user.id
            ).first()
        else:
            # 学生は所属クラスのカリキュラムのみ
            curriculum = Curriculum.query.join(ClassEnrollment).filter(
                Curriculum.id == curriculum_id,
                ClassEnrollment.student_id == current_user.id
            ).first()
        
        if curriculum:
            room_name = f"curriculum_sync_{curriculum_id}"
            join_room(room_name)
            
            if current_user.id in connected_users:
                connected_users[current_user.id]['rooms'].append(room_name)
            
            emit('sync_status', {
                'type': 'joined_curriculum_sync',
                'curriculum_id': curriculum_id,
                'message': f'カリキュラム「{curriculum.title}」の同期ルームに参加しました'
            })
            
            logger.info(f"User {current_user.id} joined curriculum sync room: {curriculum_id}")
    
    @socketio.on('leave_curriculum_sync')
    def handle_leave_curriculum_sync(data):
        """カリキュラム同期ルームから退出"""
        if not current_user.is_authenticated:
            return
            
        curriculum_id = data.get('curriculum_id')
        if not curriculum_id:
            return
            
        room_name = f"curriculum_sync_{curriculum_id}"
        leave_room(room_name)
        
        if current_user.id in connected_users:
            rooms = connected_users[current_user.id]['rooms']
            if room_name in rooms:
                rooms.remove(room_name)
        
        emit('sync_status', {
            'type': 'left_curriculum_sync',
            'curriculum_id': curriculum_id,
            'message': 'カリキュラム同期ルームから退出しました'
        })
        
        logger.info(f"User {current_user.id} left curriculum sync room: {curriculum_id}")


class RealtimeSyncNotifier:
    """リアルタイム同期通知クラス"""
    
    @classmethod
    def notify_sync_started(cls, curriculum_id: int, teacher_id: int, sync_info: Dict[str, Any]):
        """同期開始通知"""
        if not socketio:
            logger.warning("SocketIO not initialized, cannot send sync_started notification")
            return
            
        notification = {
            'type': 'sync_started',
            'curriculum_id': curriculum_id,
            'teacher_id': teacher_id,
            'message': 'カリキュラムの同期を開始しました',
            'sync_info': sync_info,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 教師に通知
        socketio.emit('sync_notification', notification, room=f"teacher_{teacher_id}")
        
        # カリキュラム同期ルームに通知
        socketio.emit('sync_notification', notification, room=f"curriculum_sync_{curriculum_id}")
        
        logger.info(f"Sync started notification sent for curriculum {curriculum_id}")
    
    @classmethod
    def notify_sync_progress(cls, curriculum_id: int, teacher_id: int, progress_info: Dict[str, Any]):
        """同期進捗通知"""
        if not socketio:
            logger.warning("SocketIO not initialized, cannot send sync_progress notification")
            return
            
        notification = {
            'type': 'sync_progress',
            'curriculum_id': curriculum_id,
            'teacher_id': teacher_id,
            'progress': progress_info,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 教師に通知
        socketio.emit('sync_notification', notification, room=f"teacher_{teacher_id}")
        
        # カリキュラム同期ルームに通知
        socketio.emit('sync_notification', notification, room=f"curriculum_sync_{curriculum_id}")
        
        logger.debug(f"Sync progress notification sent for curriculum {curriculum_id}: {progress_info}")
    
    @classmethod
    def notify_sync_completed(cls, curriculum_id: int, teacher_id: int, result: Dict[str, Any]):
        """同期完了通知"""
        if not socketio:
            logger.warning("SocketIO not initialized, cannot send sync_completed notification")
            return
            
        notification = {
            'type': 'sync_completed',
            'curriculum_id': curriculum_id,
            'teacher_id': teacher_id,
            'result': result,
            'message': '同期が完了しました' if result.get('success') else '同期中にエラーが発生しました',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 教師に通知
        socketio.emit('sync_notification', notification, room=f"teacher_{teacher_id}")
        
        # カリキュラム同期ルームに通知
        socketio.emit('sync_notification', notification, room=f"curriculum_sync_{curriculum_id}")
        
        # 成功時は関連学生にも通知
        if result.get('success') and result.get('units_updated', 0) > 0:
            cls._notify_students_unit_updated(curriculum_id, result)
        
        logger.info(f"Sync completed notification sent for curriculum {curriculum_id}: {result.get('message', 'No message')}")
    
    @classmethod
    def notify_sync_conflict(cls, curriculum_id: int, teacher_id: int, conflict_info: Dict[str, Any]):
        """同期競合通知"""
        if not socketio:
            logger.warning("SocketIO not initialized, cannot send sync_conflict notification")
            return
            
        notification = {
            'type': 'sync_conflict',
            'curriculum_id': curriculum_id,
            'teacher_id': teacher_id,
            'conflict_info': conflict_info,
            'message': '同期中に競合が検出されました。確認が必要です。',
            'requires_action': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 教師に通知（優先度高）
        socketio.emit('sync_notification', notification, room=f"teacher_{teacher_id}")
        
        logger.warning(f"Sync conflict notification sent for curriculum {curriculum_id}: {conflict_info}")
    
    @classmethod
    def _notify_students_unit_updated(cls, curriculum_id: int, sync_result: Dict[str, Any]):
        """学生への単元更新通知"""
        try:
            from app.models import Curriculum, ClassEnrollment, CurriculumUnit
            
            # カリキュラムから関連クラスを取得
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return
            
            # 関連単元の情報を取得
            updated_units = CurriculumUnit.query.filter_by(
                legacy_curriculum_id=curriculum_id,
                is_active=True
            ).all()
            
            if not updated_units:
                return
            
            student_notification = {
                'type': 'units_updated',
                'curriculum_id': curriculum_id,
                'curriculum_title': curriculum.title,
                'units_count': len(updated_units),
                'units_info': [
                    {
                        'id': unit.id,
                        'title': unit.title,
                        'difficulty_level': unit.difficulty_level,
                        'estimated_minutes': unit.estimated_minutes
                    } for unit in updated_units[:5]  # 最初の5つのみ
                ],
                'message': f'「{curriculum.title}」の学習単元が更新されました',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # クラスの学生に通知
            socketio.emit('unit_update_notification', student_notification, room=f"class_{curriculum.class_id}")
            
            logger.info(f"Unit update notification sent to class {curriculum.class_id} for curriculum {curriculum_id}")
            
        except Exception as e:
            logger.error(f"Error sending student unit update notification: {str(e)}", exc_info=True)
    
    @classmethod
    def get_connected_users_count(cls) -> int:
        """接続中のユーザー数を取得"""
        return len(connected_users)
    
    @classmethod
    def get_connected_users_info(cls) -> Dict[str, Any]:
        """接続中のユーザー情報を取得"""
        return {
            'total_connected': len(connected_users),
            'users': {
                user_id: {
                    'user_type': info['user_type'],
                    'connected_at': info['connected_at'],
                    'rooms_count': len(info['rooms'])
                } for user_id, info in connected_users.items()
            }
        }