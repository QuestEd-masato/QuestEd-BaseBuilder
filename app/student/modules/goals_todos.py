# app/student/modules/goals_todos_secure.py
"""
学生目標・TODO管理機能（セキュリティ強化版）

セキュリティ機能:
- リソース所有権チェック
- 監査ログ記録
- レート制限
- 入力検証強化
"""

import logging
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.models import Goal, Todo, db
from app.utils.model_helpers import mysql_nulls_last
from app.utils.enhanced_decorators import (
    secure_student_access,
    secure_data_modification,
    audit_log_access,
    rate_limited_access,
)
from app.utils.input_validator import InputValidator, ValidationError
from app.utils.resource_ownership import (
    can_access_user_data,
    can_modify_user_data,
    filter_accessible_resources,
)

from ..utils import student_required

goals_todos_secure_bp = Blueprint("student_goals_todos_secure", __name__)
logger = logging.getLogger(__name__)


@goals_todos_secure_bp.route("/todos")
@login_required
@student_required
@audit_log_access('todo', 'list_view')
@rate_limited_access("30 per minute")
def todos():
    """To Do一覧（セキュリティ強化版）"""
    try:
        # 自分のTODOのみ取得（所有権チェック）
        todos = (
            Todo.query.filter_by(student_id=current_user.id)
            .order_by(*mysql_nulls_last(Todo.due_date, "asc"))
            .all()
        )
        
        # 念のため所有権でフィルタリング
        accessible_todos = filter_accessible_resources('todo', todos, current_user.id)
        
        logger.info(f"User {current_user.id} accessed {len(accessible_todos)} todos")
        
        return render_template("todos.html", todos=accessible_todos)

    except Exception as e:
        logger.error(f"Todos list error for user {current_user.id}: {str(e)}")
        flash("TODO一覧の読み込み中にエラーが発生しました。")
        return redirect(url_for("student_dashboard.dashboard"))


@goals_todos_secure_bp.route("/todo/<int:todo_id>")
@secure_student_access('todo', 'todo_id')
@rate_limited_access("60 per minute")
def view_todo(todo_id):
    """TODO詳細表示（セキュリティ強化版）"""
    try:
        todo = Todo.query.get_or_404(todo_id)
        
        # 念のため再度所有権チェック
        if todo.student_id != current_user.id:
            logger.warning(f"Unauthorized todo access attempt: User {current_user.id} tried to access todo {todo_id}")
            flash("アクセス権限がありません。")
            return redirect(url_for("student_goals_todos_secure.todos"))
        
        return render_template("todo_detail.html", todo=todo)

    except Exception as e:
        logger.error(f"Todo view error for user {current_user.id}, todo {todo_id}: {str(e)}")
        flash("TODOの詳細表示中にエラーが発生しました。")
        return redirect(url_for("student_goals_todos_secure.todos"))


@goals_todos_secure_bp.route("/new_todo", methods=["GET", "POST"])
@login_required
@student_required
@audit_log_access('todo', 'create')
@rate_limited_access("10 per minute")
def new_todo():
    """新規To Do作成（セキュリティ強化版）"""
    if request.method == "GET":
        return render_template("new_todo.html")
    
    try:
        # 入力検証ルール
        validation_rules = {
            'title': {
                'type': 'safe_text',
                'required': True,
                'max_length': 200,
                'min_length': 1
            },
            'description': {
                'type': 'safe_text',
                'required': False,
                'max_length': 1000
            },
            'priority': {
                'type': 'text',
                'required': False,
            },
            'due_date': {
                'type': 'text',
                'required': False,
            }
        }
        
        # 入力データを検証・サニタイズ
        form_data = {
            'title': request.form.get('title', ''),
            'description': request.form.get('description', ''),
            'priority': request.form.get('priority', 'medium'),
            'due_date': request.form.get('due_date', '')
        }
        
        clean_data = InputValidator.validate_and_sanitize(form_data, validation_rules)
        
        # 優先度の検証
        if clean_data['priority'] not in ['high', 'medium', 'low']:
            clean_data['priority'] = 'medium'
        
        # 期限の処理
        due_date = None
        if clean_data['due_date']:
            try:
                due_date = datetime.strptime(clean_data['due_date'], '%Y-%m-%d').date()
            except ValueError:
                flash("無効な期限形式です。")
                return render_template("new_todo.html")
        
        # TODO作成
        todo = Todo(
            student_id=current_user.id,  # 必ず現在ユーザーに関連付け
            title=clean_data['title'],
            description=clean_data['description'],
            priority=clean_data['priority'],
            due_date=due_date,
            is_completed=False
        )
        
        db.session.add(todo)
        db.session.commit()
        
        logger.info(f"User {current_user.id} created new todo: {todo.id}")
        flash("TODOを作成しました。")
        return redirect(url_for("student_goals_todos_secure.todos"))

    except ValidationError as e:
        logger.warning(f"Todo creation validation error for user {current_user.id}: {str(e)}")
        flash(f"入力エラー: {str(e)}")
        return render_template("new_todo.html")
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Todo creation error for user {current_user.id}: {str(e)}")
        flash("TODO作成中にエラーが発生しました。")
        return render_template("new_todo.html")


@goals_todos_secure_bp.route("/todo/<int:todo_id>/edit", methods=["GET", "POST"])
@secure_data_modification('todo', 'todo_id', mfa_required_flag=False)
@rate_limited_access("10 per minute")
def edit_todo(todo_id):
    """TODO編集（セキュリティ強化版）"""
    try:
        todo = Todo.query.get_or_404(todo_id)
        
        # 所有権の追加チェック
        if not can_modify_user_data(todo.student_id):
            logger.warning(f"Unauthorized todo edit attempt: User {current_user.id} tried to edit todo {todo_id}")
            flash("編集権限がありません。")
            return redirect(url_for("student_goals_todos_secure.todos"))
        
        if request.method == "GET":
            return render_template("edit_todo.html", todo=todo)
        
        # 入力検証（新規作成と同じルール）
        validation_rules = {
            'title': {
                'type': 'safe_text',
                'required': True,
                'max_length': 200,
                'min_length': 1
            },
            'description': {
                'type': 'safe_text',
                'required': False,
                'max_length': 1000
            },
            'priority': {
                'type': 'text',
                'required': False,
            },
            'due_date': {
                'type': 'text',
                'required': False,
            },
            'is_completed': {
                'type': 'text',
                'required': False,
            }
        }
        
        form_data = {
            'title': request.form.get('title', ''),
            'description': request.form.get('description', ''),
            'priority': request.form.get('priority', 'medium'),
            'due_date': request.form.get('due_date', ''),
            'is_completed': request.form.get('is_completed', 'off')
        }
        
        clean_data = InputValidator.validate_and_sanitize(form_data, validation_rules)
        
        # データ更新
        todo.title = clean_data['title']
        todo.description = clean_data['description']
        todo.priority = clean_data['priority'] if clean_data['priority'] in ['high', 'medium', 'low'] else 'medium'
        todo.is_completed = clean_data['is_completed'] == 'on'
        
        # 期限の処理
        if clean_data['due_date']:
            try:
                todo.due_date = datetime.strptime(clean_data['due_date'], '%Y-%m-%d').date()
            except ValueError:
                flash("無効な期限形式です。")
                return render_template("edit_todo.html", todo=todo)
        else:
            todo.due_date = None
        
        db.session.commit()
        
        logger.info(f"User {current_user.id} updated todo: {todo.id}")
        flash("TODOを更新しました。")
        return redirect(url_for("student_goals_todos_secure.view_todo", todo_id=todo.id))

    except ValidationError as e:
        logger.warning(f"Todo edit validation error for user {current_user.id}, todo {todo_id}: {str(e)}")
        flash(f"入力エラー: {str(e)}")
        return render_template("edit_todo.html", todo=todo)
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Todo edit error for user {current_user.id}, todo {todo_id}: {str(e)}")
        flash("TODO更新中にエラーが発生しました。")
        return redirect(url_for("student_goals_todos_secure.todos"))


@goals_todos_secure_bp.route("/todo/<int:todo_id>/delete", methods=["POST"])
@secure_data_modification('todo', 'todo_id', mfa_required_flag=True)
@rate_limited_access("5 per minute")
def delete_todo(todo_id):
    """TODO削除（セキュリティ強化版）"""
    try:
        todo = Todo.query.get_or_404(todo_id)
        
        # 最終所有権チェック
        if not can_modify_user_data(todo.student_id):
            logger.warning(f"Unauthorized todo delete attempt: User {current_user.id} tried to delete todo {todo_id}")
            return jsonify({'success': False, 'error': 'アクセス権限がありません。'}), 403
        
        # TODO削除
        db.session.delete(todo)
        db.session.commit()
        
        logger.info(f"User {current_user.id} deleted todo: {todo_id}")
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'TODOを削除しました。'})
        else:
            flash("TODOを削除しました。")
            return redirect(url_for("student_goals_todos_secure.todos"))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Todo deletion error for user {current_user.id}, todo {todo_id}: {str(e)}")
        
        if request.is_json:
            return jsonify({'success': False, 'error': 'TODO削除中にエラーが発生しました。'}), 500
        else:
            flash("TODO削除中にエラーが発生しました。")
            return redirect(url_for("student_goals_todos_secure.todos"))


@goals_todos_secure_bp.route("/todo/<int:todo_id>/toggle", methods=["POST"])
@secure_data_modification('todo', 'todo_id', mfa_required_flag=False)
@rate_limited_access("20 per minute")
def toggle_todo_completion(todo_id):
    """TODO完了状態切り替え（セキュリティ強化版）"""
    try:
        todo = Todo.query.get_or_404(todo_id)
        
        # 所有権チェック
        if not can_modify_user_data(todo.student_id):
            logger.warning(f"Unauthorized todo toggle attempt: User {current_user.id} tried to toggle todo {todo_id}")
            return jsonify({'success': False, 'error': 'アクセス権限がありません。'}), 403
        
        # 完了状態を切り替え
        todo.is_completed = not todo.is_completed
        db.session.commit()
        
        logger.info(f"User {current_user.id} toggled todo completion: {todo_id} -> {todo.is_completed}")
        
        return jsonify({
            'success': True,
            'is_completed': todo.is_completed,
            'message': 'TODOの状態を更新しました。'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Todo toggle error for user {current_user.id}, todo {todo_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'TODO状態更新中にエラーが発生しました。'}), 500


# 目標関連の機能も同様にセキュリティ強化

@goals_todos_secure_bp.route("/goals")
@login_required
@student_required
@audit_log_access('goal', 'list_view')
@rate_limited_access("30 per minute")
def goals():
    """目標一覧（セキュリティ強化版）"""
    try:
        goals = (
            Goal.query.filter_by(student_id=current_user.id)
            .order_by(Goal.created_at.desc())
            .all()
        )
        
        # 所有権でフィルタリング
        accessible_goals = filter_accessible_resources('goal', goals, current_user.id)
        
        logger.info(f"User {current_user.id} accessed {len(accessible_goals)} goals")
        
        return render_template("goals.html", goals=accessible_goals)

    except Exception as e:
        logger.error(f"Goals list error for user {current_user.id}: {str(e)}")
        flash("目標一覧の読み込み中にエラーが発生しました。")
        return redirect(url_for("student_dashboard.dashboard"))


@goals_todos_secure_bp.route("/goal/<int:goal_id>")
@secure_student_access('goal', 'goal_id')
@rate_limited_access("60 per minute")
def view_goal(goal_id):
    """目標詳細表示（セキュリティ強化版）"""
    try:
        goal = Goal.query.get_or_404(goal_id)
        
        # 所有権チェック
        if goal.student_id != current_user.id:
            logger.warning(f"Unauthorized goal access attempt: User {current_user.id} tried to access goal {goal_id}")
            flash("アクセス権限がありません。")
            return redirect(url_for("student_goals_todos_secure.goals"))
        
        return render_template("goal_detail.html", goal=goal)

    except Exception as e:
        logger.error(f"Goal view error for user {current_user.id}, goal {goal_id}: {str(e)}")
        flash("目標の詳細表示中にエラーが発生しました。")
        return redirect(url_for("student_goals_todos_secure.goals"))


# セキュリティ設定用の初期化関数
def init_secure_goals_todos(app):
    """セキュリティ強化版目標・TODO機能の初期化"""
    app.register_blueprint(goals_todos_secure_bp, url_prefix='/student')
    logger.info("Secure goals/todos module initialized")