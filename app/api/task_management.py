# -*- coding: utf-8 -*-
"""
Task Management API (Phase7-5: リファクタリング版)

Phase7-5で3つの専門サービスに分割:
- TaskCRUDService: 課題のCRUD操作専門
- TaskProgressService: 学生進捗管理専門  
- TaskValidationService: 入力検証専門

このファイルは後方互換性を維持するためのAPIレイヤーです。
"""
import logging
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app.models import (
    CurriculumTask, StudentTaskProgress, TaskFileAttachment,
    TaskType, TaskStatus, DueDateType, db
)
from app.services.task import (
    TaskCRUDService,
    TaskProgressService,
    TaskValidationService
)
from app.utils.rate_limiting import api_limit

task_management_bp = Blueprint("task_management", __name__)
logger = logging.getLogger(__name__)

# サービスインスタンス
crud_service = TaskCRUDService()
progress_service = TaskProgressService()
validation_service = TaskValidationService()

# ==========================================
# 課題管理API (教師用)
# ==========================================

@task_management_bp.route('/curriculum/<int:curriculum_id>/tasks', methods=['GET'])
@login_required
@api_limit()
def get_curriculum_tasks(curriculum_id):
    """カリキュラムの課題一覧取得"""
    try:
        # 権限チェック
        permission_check = validation_service.validate_user_permissions(
            'read', {'curriculum_id': curriculum_id}
        )
        if not permission_check['valid']:
            return jsonify({"status": "error", "message": permission_check['message']}), 403

        # 課題一覧を取得
        result = crud_service.get_curriculum_tasks(curriculum_id)
        
        return jsonify(result), 200 if result['status'] == 'success' else 400

    except Exception as e:
        logger.error(f"Error in get_curriculum_tasks: {str(e)}")
        return jsonify({"status": "error", "message": "課題一覧の取得に失敗しました"}), 500

@task_management_bp.route('/task', methods=['POST'])
@login_required
@api_limit()
def create_task():
    """課題作成"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "リクエストデータが不正です"}), 400

        # 入力データをサニタイズ
        sanitized_data = validation_service.sanitize_input_data(data)

        # 権限チェック
        permission_check = validation_service.validate_user_permissions(
            'create', {'curriculum_id': sanitized_data.get('curriculum_id')}
        )
        if not permission_check['valid']:
            return jsonify({"status": "error", "message": permission_check['message']}), 403

        # データ検証
        validation_result = validation_service.validate_task_data(sanitized_data, 'create')
        if not validation_result['valid']:
            return jsonify({
                "status": "error", 
                "message": "入力データが不正です",
                "errors": validation_result['errors']
            }), 400

        # 依存関係チェック
        dependency_check = validation_service.check_task_dependencies(sanitized_data)
        if dependency_check['warnings']:
            logger.warning(f"Task dependency warnings: {dependency_check['warnings']}")

        # 課題を作成
        result = crud_service.create_task(sanitized_data)
        
        return jsonify(result), 201 if result['status'] == 'success' else 400

    except Exception as e:
        logger.error(f"Error in create_task: {str(e)}")
        return jsonify({"status": "error", "message": "課題の作成に失敗しました"}), 500

@task_management_bp.route('/task/<int:task_id>', methods=['PUT'])
@login_required
@api_limit()
def update_task(task_id):
    """課題更新"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "リクエストデータが不正です"}), 400

        # 課題の存在確認
        task = crud_service.get_task_by_id(task_id)
        if not task:
            return jsonify({"status": "error", "message": "課題が見つかりません"}), 404

        # 入力データをサニタイズ  
        sanitized_data = validation_service.sanitize_input_data(data)

        # 権限チェック
        permission_check = validation_service.validate_user_permissions(
            'update', {'curriculum_id': task['curriculum_id']}
        )
        if not permission_check['valid']:
            return jsonify({"status": "error", "message": permission_check['message']}), 403

        # データ検証
        validation_result = validation_service.validate_task_data(sanitized_data, 'update')
        if not validation_result['valid']:
            return jsonify({
                "status": "error",
                "message": "入力データが不正です",
                "errors": validation_result['errors']
            }), 400

        # 課題を更新
        result = crud_service.update_task(task_id, sanitized_data)
        
        return jsonify(result), 200 if result['status'] == 'success' else 400

    except Exception as e:
        logger.error(f"Error in update_task: {str(e)}")
        return jsonify({"status": "error", "message": "課題の更新に失敗しました"}), 500

@task_management_bp.route('/task/<int:task_id>', methods=['DELETE'])
@login_required
@api_limit()
def delete_task(task_id):
    """課題削除"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        # 課題の存在確認
        task = crud_service.get_task_by_id(task_id)
        if not task:
            return jsonify({"status": "error", "message": "課題が見つかりません"}), 404

        # 権限チェック
        permission_check = validation_service.validate_user_permissions(
            'delete', {'curriculum_id': task['curriculum_id']}
        )
        if not permission_check['valid']:
            return jsonify({"status": "error", "message": permission_check['message']}), 403

        # 課題を削除
        result = crud_service.delete_task(task_id)
        
        return jsonify(result), 200 if result['status'] == 'success' else 400

    except Exception as e:
        logger.error(f"Error in delete_task: {str(e)}")
        return jsonify({"status": "error", "message": "課題の削除に失敗しました"}), 500

# ==========================================
# 学生用API
# ==========================================

@task_management_bp.route('/student/tasks/<int:curriculum_id>', methods=['GET'])
@login_required
@api_limit()
def get_student_tasks(curriculum_id):
    """学生課題一覧取得"""
    try:
        # 学生のみアクセス可能
        if current_user.role != 'student':
            return jsonify({"status": "error", "message": "学生のみアクセス可能です"}), 403

        # アクセス権限チェック
        access_check = validation_service.validate_curriculum_access(curriculum_id, current_user.id)
        if not access_check['valid']:
            return jsonify({"status": "error", "message": access_check['message']}), 403

        # 学生用課題一覧を取得
        result = crud_service.get_student_tasks(curriculum_id, current_user.id)
        
        return jsonify(result), 200 if result['status'] == 'success' else 400

    except Exception as e:
        logger.error(f"Error in get_student_tasks: {str(e)}")
        return jsonify({"status": "error", "message": "学生課題一覧の取得に失敗しました"}), 500

@task_management_bp.route('/student/task/<int:task_id>/start', methods=['POST'])
@login_required
@api_limit()
def start_task(task_id):
    """課題開始"""
    try:
        # 学生のみアクセス可能
        if current_user.role != 'student':
            return jsonify({"status": "error", "message": "学生のみアクセス可能です"}), 403

        # 課題開始
        result = progress_service.start_task(task_id, current_user.id)
        
        return jsonify(result), 200 if result['status'] == 'success' else 400

    except Exception as e:
        logger.error(f"Error in start_task: {str(e)}")
        return jsonify({"status": "error", "message": "課題の開始に失敗しました"}), 500

@task_management_bp.route('/student/task/<int:task_id>/progress', methods=['PUT'])
@login_required
@api_limit()
def update_task_progress(task_id):
    """課題進捗更新"""
    try:
        # 学生のみアクセス可能
        if current_user.role != 'student':
            return jsonify({"status": "error", "message": "学生のみアクセス可能です"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "リクエストデータが不正です"}), 400

        # 入力データをサニタイズ
        sanitized_data = validation_service.sanitize_input_data(data)

        # データ検証
        validation_result = validation_service.validate_progress_data(sanitized_data)
        if not validation_result['valid']:
            return jsonify({
                "status": "error",
                "message": "入力データが不正です",
                "errors": validation_result['errors']
            }), 400

        # 進捗を更新
        result = progress_service.update_task_progress(task_id, current_user.id, sanitized_data)
        
        return jsonify(result), 200 if result['status'] == 'success' else 400

    except Exception as e:
        logger.error(f"Error in update_task_progress: {str(e)}")
        return jsonify({"status": "error", "message": "進捗の更新に失敗しました"}), 500

@task_management_bp.route('/student/task/<int:task_id>/submit', methods=['POST'])
@login_required
@api_limit()
def submit_task(task_id):
    """課題提出"""
    try:
        # 学生のみアクセス可能
        if current_user.role != 'student':
            return jsonify({"status": "error", "message": "学生のみアクセス可能です"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "リクエストデータが不正です"}), 400

        # 入力データをサニタイズ
        sanitized_data = validation_service.sanitize_input_data(data)

        # データ検証
        validation_result = validation_service.validate_progress_data(sanitized_data)
        if not validation_result['valid']:
            return jsonify({
                "status": "error",
                "message": "入力データが不正です", 
                "errors": validation_result['errors']
            }), 400

        # 課題を提出
        result = progress_service.submit_task(task_id, current_user.id, sanitized_data)
        
        return jsonify(result), 200 if result['status'] == 'success' else 400

    except Exception as e:
        logger.error(f"Error in submit_task: {str(e)}")
        return jsonify({"status": "error", "message": "課題の提出に失敗しました"}), 500

# ==========================================
# 教師評価API
# ==========================================

@task_management_bp.route('/teacher/pending-submissions', methods=['GET'])
@login_required
@api_limit()
def get_pending_submissions():
    """承認待ち提出物取得"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        # 承認待ち提出物を取得
        result = progress_service.get_pending_submissions(current_user.id)
        
        return jsonify(result), 200 if result['status'] == 'success' else 400

    except Exception as e:
        logger.error(f"Error in get_pending_submissions: {str(e)}")
        return jsonify({"status": "error", "message": "承認待ち提出物の取得に失敗しました"}), 500

@task_management_bp.route('/teacher/submission/<int:progress_id>/approve', methods=['POST'])
@login_required
@api_limit()
def approve_submission(progress_id):
    """提出物承認"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "リクエストデータが不正です"}), 400

        # 入力データをサニタイズ
        sanitized_data = validation_service.sanitize_input_data(data)

        # データ検証
        validation_result = validation_service.validate_progress_data(sanitized_data)
        if not validation_result['valid']:
            return jsonify({
                "status": "error",
                "message": "入力データが不正です",
                "errors": validation_result['errors']
            }), 400

        # 提出物を承認
        result = progress_service.approve_submission(progress_id, current_user.id, sanitized_data)
        
        return jsonify(result), 200 if result['status'] == 'success' else 400

    except Exception as e:
        logger.error(f"Error in approve_submission: {str(e)}")
        return jsonify({"status": "error", "message": "提出物の承認に失敗しました"}), 500

@task_management_bp.route('/teacher/submission/<int:progress_id>/request-revision', methods=['POST'])
@login_required
@api_limit()
def request_revision(progress_id):
    """修正要求"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "リクエストデータが不正です"}), 400

        # 入力データをサニタイズ
        sanitized_data = validation_service.sanitize_input_data(data)

        # データ検証
        validation_result = validation_service.validate_progress_data(sanitized_data)
        if not validation_result['valid']:
            return jsonify({
                "status": "error",
                "message": "入力データが不正です",
                "errors": validation_result['errors']
            }), 400

        # 修正を要求
        result = progress_service.request_revision(progress_id, current_user.id, sanitized_data)
        
        return jsonify(result), 200 if result['status'] == 'success' else 400

    except Exception as e:
        logger.error(f"Error in request_revision: {str(e)}")
        return jsonify({"status": "error", "message": "修正要求に失敗しました"}), 500

# ==========================================
# 設定・ユーティリティAPI
# ==========================================

@task_management_bp.route('/task-types', methods=['GET'])
@login_required
@api_limit()
def get_task_types():
    """課題タイプ一覧取得"""
    try:
        task_types = crud_service.get_task_types()
        return jsonify({
            "status": "success",
            "task_types": task_types
        }), 200

    except Exception as e:
        logger.error(f"Error in get_task_types: {str(e)}")
        return jsonify({"status": "error", "message": "課題タイプの取得に失敗しました"}), 500

@task_management_bp.route('/task-statuses', methods=['GET'])
@login_required
@api_limit()
def get_task_statuses():
    """課題ステータス一覧取得"""
    try:
        task_statuses = crud_service.get_task_statuses()
        return jsonify({
            "status": "success", 
            "task_statuses": task_statuses
        }), 200

    except Exception as e:
        logger.error(f"Error in get_task_statuses: {str(e)}")
        return jsonify({"status": "error", "message": "課題ステータスの取得に失敗しました"}), 500

@task_management_bp.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        "status": "success",
        "message": "Task Management API is healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "crud_service": "active",
            "progress_service": "active", 
            "validation_service": "active"
        }
    }), 200