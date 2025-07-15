"""
Task Management API
===================
Week 1: 基盤整備

新タスクシステムのためのAPI エンドポイント
- 課題CRUD操作
- 学生進捗管理
- 教師承認機能
"""

import logging
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app.models import (
    CurriculumTask, StudentTaskProgress, TaskFileAttachment,
    TaskType, TaskStatus, DueDateType, db
)
from app.utils.rate_limiting import api_limit

task_management_bp = Blueprint("task_management", __name__)

# ==========================================
# 課題管理API (教師用)
# ==========================================

@task_management_bp.route('/curriculum/<int:curriculum_id>/tasks', methods=['GET'])
@login_required
@api_limit()
def get_curriculum_tasks(curriculum_id):
    """カリキュラムの課題一覧取得"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        # 週番号でソート
        tasks = CurriculumTask.query.filter_by(curriculum_id=curriculum_id) \
                                   .order_by(CurriculumTask.week_number, CurriculumTask.order_in_week) \
                                   .all()

        # 週ごとにグループ化
        weeks_data = {}
        for task in tasks:
            week_num = task.week_number
            if week_num not in weeks_data:
                weeks_data[week_num] = {
                    'week_number': week_num,
                    'tasks': []
                }
            weeks_data[week_num]['tasks'].append(task.to_dict())

        weeks_list = list(weeks_data.values())
        weeks_list.sort(key=lambda x: x['week_number'])

        return jsonify({
            "status": "success",
            "curriculum_id": curriculum_id,
            "weeks": weeks_list,
            "total_tasks": len(tasks)
        })

    except Exception as e:
        logging.error(f"Get curriculum tasks error: {str(e)}")
        return jsonify({"status": "error", "message": "課題取得中にエラーが発生しました"}), 500


@task_management_bp.route('/task', methods=['POST'])
@login_required
@api_limit()
def create_task():
    """新規課題作成"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "JSONデータが必要です"}), 400

        # 必須フィールドの検証
        required_fields = ['curriculum_id', 'week_number', 'title', 'task_type']
        for field in required_fields:
            if field not in data:
                return jsonify({"status": "error", "message": f"{field}は必須項目です"}), 400

        # 課題タイプの検証
        try:
            task_type = TaskType(data['task_type'])
        except ValueError:
            valid_types = [t.value for t in TaskType]
            return jsonify({
                "status": "error", 
                "message": f"無効な課題タイプです。有効な値: {valid_types}"
            }), 400

        # 期限タイプの検証
        due_date_type = DueDateType.RELATIVE_TO_WEEK_START
        if 'due_date_type' in data:
            try:
                due_date_type = DueDateType(data['due_date_type'])
            except ValueError:
                valid_types = [t.value for t in DueDateType]
                return jsonify({
                    "status": "error", 
                    "message": f"無効な期限タイプです。有効な値: {valid_types}"
                }), 400

        # 新しい課題の順序決定
        order_in_week = data.get('order_in_week')
        if not order_in_week:
            max_order = db.session.query(db.func.max(CurriculumTask.order_in_week)) \
                                  .filter_by(curriculum_id=data['curriculum_id'], 
                                           week_number=data['week_number']) \
                                  .scalar()
            order_in_week = (max_order or 0) + 1

        # 課題作成
        task = CurriculumTask(
            curriculum_id=data['curriculum_id'],
            week_number=data['week_number'],
            order_in_week=order_in_week,
            title=data['title'],
            description=data.get('description', ''),
            task_type=task_type,
            estimated_minutes=data.get('estimated_minutes', 50),
            difficulty_level=data.get('difficulty_level', 2),
            is_required=data.get('is_required', True),
            submission_requirements=data.get('submission_requirements'),
            evaluation_criteria=data.get('evaluation_criteria'),
            due_date_type=due_date_type,
            due_date_offset_days=data.get('due_date_offset_days', 7),
            fixed_due_date=datetime.strptime(data['fixed_due_date'], '%Y-%m-%d').date() 
                          if data.get('fixed_due_date') else None,
            resources=data.get('resources'),
            teacher_notes=data.get('teacher_notes'),
            auto_approval_enabled=data.get('auto_approval_enabled', False),
            auto_approval_threshold=data.get('auto_approval_threshold', 80),
            created_by=current_user.id
        )

        db.session.add(task)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "課題が作成されました",
            "task_id": task.id,
            "task": task.to_dict()
        }), 201

    except Exception as e:
        logging.error(f"Create task error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "課題作成中にエラーが発生しました"}), 500


@task_management_bp.route('/task/<int:task_id>', methods=['PUT'])
@login_required
@api_limit()
def update_task(task_id):
    """課題更新"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        task = CurriculumTask.query.get(task_id)
        if not task:
            return jsonify({"status": "error", "message": "課題が見つかりません"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "JSONデータが必要です"}), 400

        # 更新可能フィールドの更新
        updatable_fields = [
            'title', 'description', 'estimated_minutes', 'difficulty_level',
            'is_required', 'submission_requirements', 'evaluation_criteria',
            'due_date_offset_days', 'resources', 'teacher_notes',
            'auto_approval_enabled', 'auto_approval_threshold'
        ]

        for field in updatable_fields:
            if field in data:
                setattr(task, field, data[field])

        # 課題タイプの更新
        if 'task_type' in data:
            try:
                task.task_type = TaskType(data['task_type'])
            except ValueError:
                valid_types = [t.value for t in TaskType]
                return jsonify({
                    "status": "error", 
                    "message": f"無効な課題タイプです。有効な値: {valid_types}"
                }), 400

        # 期限タイプの更新
        if 'due_date_type' in data:
            try:
                task.due_date_type = DueDateType(data['due_date_type'])
            except ValueError:
                valid_types = [t.value for t in DueDateType]
                return jsonify({
                    "status": "error", 
                    "message": f"無効な期限タイプです。有効な値: {valid_types}"
                }), 400

        # 固定期限の更新
        if 'fixed_due_date' in data:
            if data['fixed_due_date']:
                task.fixed_due_date = datetime.strptime(data['fixed_due_date'], '%Y-%m-%d').date()
            else:
                task.fixed_due_date = None

        task.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "課題が更新されました",
            "task": task.to_dict()
        })

    except Exception as e:
        logging.error(f"Update task error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "課題更新中にエラーが発生しました"}), 500


@task_management_bp.route('/task/<int:task_id>', methods=['DELETE'])
@login_required
@api_limit()
def delete_task(task_id):
    """課題削除"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        task = CurriculumTask.query.get(task_id)
        if not task:
            return jsonify({"status": "error", "message": "課題が見つかりません"}), 404

        # 進捗データが存在する場合の確認
        progress_count = StudentTaskProgress.query.filter_by(task_id=task_id).count()
        if progress_count > 0:
            force = request.args.get('force', 'false').lower() == 'true'
            if not force:
                return jsonify({
                    "status": "warning",
                    "message": f"この課題には{progress_count}件の学生進捗データが存在します。削除すると進捗データも失われます。",
                    "progress_count": progress_count
                }), 200

        # 課題削除（カスケードで進捗データも削除）
        db.session.delete(task)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "課題が削除されました",
            "task_id": task_id
        })

    except Exception as e:
        logging.error(f"Delete task error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "課題削除中にエラーが発生しました"}), 500


# ==========================================
# 学生課題API
# ==========================================

@task_management_bp.route('/student/tasks/<int:curriculum_id>', methods=['GET'])
@login_required
@api_limit()
def get_student_tasks(curriculum_id):
    """学生用課題一覧取得（進捗含む）"""
    try:
        # 学生のみアクセス可能
        if current_user.role != 'student':
            return jsonify({"status": "error", "message": "この機能は学生のみ利用可能です"}), 403

        # 課題取得
        tasks = CurriculumTask.query.filter_by(curriculum_id=curriculum_id) \
                                   .order_by(CurriculumTask.week_number, CurriculumTask.order_in_week) \
                                   .all()

        # 学生の進捗データ取得
        progress_dict = {}
        progress_records = StudentTaskProgress.query.filter_by(student_id=current_user.id) \
                                                   .filter(StudentTaskProgress.task_id.in_([t.id for t in tasks])) \
                                                   .all()
        
        for progress in progress_records:
            progress_dict[progress.task_id] = progress

        # 週ごとにグループ化して進捗情報を追加
        weeks_data = {}
        for task in tasks:
            week_num = task.week_number
            if week_num not in weeks_data:
                weeks_data[week_num] = {
                    'week_number': week_num,
                    'tasks': [],
                    'completed_tasks': 0,
                    'total_tasks': 0,
                    'progress_percentage': 0
                }

            task_data = task.to_dict()
            progress = progress_dict.get(task.id)
            
            if progress:
                task_data['progress'] = progress.to_dict()
            else:
                task_data['progress'] = {
                    'status': 'not_started',
                    'progress_percentage': 0
                }

            weeks_data[week_num]['tasks'].append(task_data)
            weeks_data[week_num]['total_tasks'] += 1
            
            if progress and progress.status == TaskStatus.COMPLETED:
                weeks_data[week_num]['completed_tasks'] += 1

        # 週別進捗率計算
        for week_data in weeks_data.values():
            if week_data['total_tasks'] > 0:
                week_data['progress_percentage'] = round(
                    (week_data['completed_tasks'] / week_data['total_tasks']) * 100, 1
                )

        weeks_list = list(weeks_data.values())
        weeks_list.sort(key=lambda x: x['week_number'])

        return jsonify({
            "status": "success",
            "curriculum_id": curriculum_id,
            "student_id": current_user.id,
            "weeks": weeks_list,
            "total_tasks": len(tasks),
            "total_completed": sum(w['completed_tasks'] for w in weeks_data.values())
        })

    except Exception as e:
        logging.error(f"Get student tasks error: {str(e)}")
        return jsonify({"status": "error", "message": "課題取得中にエラーが発生しました"}), 500


@task_management_bp.route('/student/task/<int:task_id>/start', methods=['POST'])
@login_required
@api_limit()
def start_task(task_id):
    """課題開始"""
    try:
        # 学生のみアクセス可能
        if current_user.role != 'student':
            return jsonify({"status": "error", "message": "この機能は学生のみ利用可能です"}), 403

        # 課題存在確認
        task = CurriculumTask.query.get(task_id)
        if not task:
            return jsonify({"status": "error", "message": "課題が見つかりません"}), 404

        # 既存進捗確認
        progress = StudentTaskProgress.query.filter_by(student_id=current_user.id, task_id=task_id).first()
        
        if progress:
            if progress.status != TaskStatus.NOT_STARTED:
                return jsonify({
                    "status": "info", 
                    "message": "課題は既に開始されています",
                    "progress": progress.to_dict()
                })
        else:
            # 新規進捗レコード作成
            progress = StudentTaskProgress(
                student_id=current_user.id,
                task_id=task_id,
                status=TaskStatus.NOT_STARTED
            )
            db.session.add(progress)

        # 課題開始処理
        success = progress.start_task()
        if success:
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "課題を開始しました",
                "progress": progress.to_dict()
            })
        else:
            return jsonify({"status": "error", "message": "課題開始に失敗しました"}), 400

    except Exception as e:
        logging.error(f"Start task error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "課題開始中にエラーが発生しました"}), 500


@task_management_bp.route('/student/task/<int:task_id>/progress', methods=['PUT'])
@login_required
@api_limit()
def update_task_progress(task_id):
    """課題進捗更新"""
    try:
        # 学生のみアクセス可能
        if current_user.role != 'student':
            return jsonify({"status": "error", "message": "この機能は学生のみ利用可能です"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "JSONデータが必要です"}), 400

        # 進捗レコード取得
        progress = StudentTaskProgress.query.filter_by(student_id=current_user.id, task_id=task_id).first()
        if not progress:
            return jsonify({"status": "error", "message": "進捗レコードが見つかりません"}), 404

        # 進捗更新
        progress_percentage = data.get('progress_percentage', 0)
        time_spent = data.get('time_spent_minutes', 0)
        
        progress.update_progress(progress_percentage, time_spent)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "進捗が更新されました",
            "progress": progress.to_dict()
        })

    except Exception as e:
        logging.error(f"Update task progress error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "進捗更新中にエラーが発生しました"}), 500


@task_management_bp.route('/student/task/<int:task_id>/submit', methods=['POST'])
@login_required
@api_limit()
def submit_task(task_id):
    """課題提出"""
    try:
        # 学生のみアクセス可能
        if current_user.role != 'student':
            return jsonify({"status": "error", "message": "この機能は学生のみ利用可能です"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "JSONデータが必要です"}), 400

        # 進捗レコード取得
        progress = StudentTaskProgress.query.filter_by(student_id=current_user.id, task_id=task_id).first()
        if not progress:
            return jsonify({"status": "error", "message": "進捗レコードが見つかりません"}), 404

        # 提出データ
        submission_data = data.get('submission_data')
        self_evaluation = data.get('self_evaluation')

        if not submission_data:
            return jsonify({"status": "error", "message": "提出データが必要です"}), 400

        # 課題提出処理
        success = progress.submit_task(submission_data, self_evaluation)
        if success:
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "課題を提出しました",
                "progress": progress.to_dict()
            })
        else:
            return jsonify({"status": "error", "message": "課題提出に失敗しました"}), 400

    except Exception as e:
        logging.error(f"Submit task error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "課題提出中にエラーが発生しました"}), 500


# ==========================================
# 教師承認API
# ==========================================

@task_management_bp.route('/teacher/pending-submissions', methods=['GET'])
@login_required
@api_limit()
def get_pending_submissions():
    """承認待ち課題一覧取得"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        # 承認待ち課題取得
        pending_submissions = db.session.query(StudentTaskProgress, CurriculumTask) \
                                       .join(CurriculumTask) \
                                       .filter(StudentTaskProgress.status == TaskStatus.SUBMITTED) \
                                       .order_by(StudentTaskProgress.submitted_at) \
                                       .all()

        submissions_data = []
        for progress, task in pending_submissions:
            submission_info = progress.to_dict()
            submission_info['task'] = task.to_dict()
            submission_info['student'] = {
                'id': progress.student.id,
                'name': progress.student.full_name or progress.student.username
            }
            submissions_data.append(submission_info)

        return jsonify({
            "status": "success",
            "submissions": submissions_data,
            "total_count": len(submissions_data)
        })

    except Exception as e:
        logging.error(f"Get pending submissions error: {str(e)}")
        return jsonify({"status": "error", "message": "承認待ち取得中にエラーが発生しました"}), 500


@task_management_bp.route('/teacher/submission/<int:progress_id>/approve', methods=['POST'])
@login_required
@api_limit()
def approve_submission(progress_id):
    """課題承認"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        data = request.get_json() or {}
        
        # 進捗レコード取得
        progress = StudentTaskProgress.query.get(progress_id)
        if not progress:
            return jsonify({"status": "error", "message": "提出レコードが見つかりません"}), 404

        # 承認処理
        teacher_evaluation = data.get('teacher_evaluation')
        feedback = data.get('feedback')
        
        success = progress.approve_task(current_user.id, teacher_evaluation, feedback)
        if success:
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "課題を承認しました",
                "progress": progress.to_dict()
            })
        else:
            return jsonify({"status": "error", "message": "承認処理に失敗しました"}), 400

    except Exception as e:
        logging.error(f"Approve submission error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "承認処理中にエラーが発生しました"}), 500


@task_management_bp.route('/teacher/submission/<int:progress_id>/request-revision', methods=['POST'])
@login_required
@api_limit()
def request_revision(progress_id):
    """修正依頼"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({"status": "error", "message": "権限がありません"}), 403

        data = request.get_json()
        if not data or 'feedback' not in data:
            return jsonify({"status": "error", "message": "フィードバックが必要です"}), 400

        # 進捗レコード取得
        progress = StudentTaskProgress.query.get(progress_id)
        if not progress:
            return jsonify({"status": "error", "message": "提出レコードが見つかりません"}), 404

        # 修正依頼処理
        success = progress.request_revision(data['feedback'])
        if success:
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "修正依頼を送信しました",
                "progress": progress.to_dict()
            })
        else:
            return jsonify({"status": "error", "message": "修正依頼に失敗しました"}), 400

    except Exception as e:
        logging.error(f"Request revision error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "修正依頼中にエラーが発生しました"}), 500


# ==========================================
# ユーティリティAPI
# ==========================================

@task_management_bp.route('/task-types', methods=['GET'])
@login_required
def get_task_types():
    """課題タイプ一覧取得"""
    task_types = []
    for task_type in TaskType:
        task_types.append({
            'value': task_type.value,
            'display': CurriculumTask(task_type=task_type).get_type_display()
        })
    
    return jsonify({
        "status": "success",
        "task_types": task_types
    })


@task_management_bp.route('/task-statuses', methods=['GET'])
@login_required  
def get_task_statuses():
    """課題ステータス一覧取得"""
    statuses = []
    for status in TaskStatus:
        statuses.append({
            'value': status.value,
            'display': StudentTaskProgress(status=status).get_status_display()
        })
    
    return jsonify({
        "status": "success",
        "task_statuses": statuses
    })


# Health check
@task_management_bp.route('/health', methods=['GET'])
def health_check():
    """タスクAPIヘルスチェック"""
    return jsonify({
        "status": "success",
        "service": "task_management",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "conversion_disabled": current_app.config.get('CONVERSION_DISABLED', False),
        "task_system_enabled": current_app.config.get('TASK_SYSTEM_ENABLED', False)
    })