# app/student/modules/goals_todos.py
"""学生目標・TODO管理機能"""

import logging
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.models import Class, ClassEnrollment, Goal, InquiryTheme, Todo, db
from app.utils.model_helpers import mysql_nulls_last

from ..utils import check_class_access, student_required

goals_todos_bp = Blueprint("student_goals_todos", __name__)


@goals_todos_bp.route("/todos")
@login_required
@student_required
def todos():
    """To Do一覧"""
    try:
        todos = (
            Todo.query.filter_by(student_id=current_user.id)
            .order_by(*mysql_nulls_last(Todo.due_date, "asc"))
            .all()
        )

        return render_template("todos.html", todos=todos)

    except Exception as e:
        current_app.logger.error(f"Todos list error: {str(e)}")
        flash("TODO一覧の読み込み中にエラーが発生しました。")
        return redirect(url_for("student_dashboard.dashboard"))


@goals_todos_bp.route("/new_todo", methods=["GET", "POST"])
@login_required
@student_required
def new_todo():
    """新規To Do作成"""
    try:
        if request.method == "POST":
            content = request.form.get("content", "").strip()
            due_date_str = request.form.get("due_date", "").strip()
            priority = request.form.get("priority", "medium")

            # 入力値検証
            if not content:
                flash("TODO内容を入力してください。", "error")
                return render_template("new_todo.html")

            # 期限日の処理
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                except ValueError:
                    flash("正しい日付形式で入力してください。", "error")
                    return render_template("new_todo.html")

            # 新しいTODOを作成
            new_todo = Todo(
                student_id=current_user.id,
                title=content,
                due_date=due_date,
                priority=priority,
            )

            try:
                db.session.add(new_todo)
                db.session.commit()
                flash("TODOを作成しました。", "success")
                return redirect(url_for("student_goals_todos.todos"))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"TODO creation error: {str(e)}")
                flash("TODOの作成に失敗しました。", "error")

        return render_template("new_todo.html")

    except Exception as e:
        current_app.logger.error(f"New todo error: {str(e)}")
        flash("TODO作成画面の読み込み中にエラーが発生しました。")
        return redirect(url_for("student_goals_todos.todos"))


@goals_todos_bp.route("/edit_todo/<int:todo_id>", methods=["GET", "POST"])
@login_required
@student_required
def edit_todo(todo_id):
    """To Do編集"""
    try:
        todo = Todo.query.get_or_404(todo_id)

        # 権限チェック
        if todo.student_id != current_user.id:
            flash("このTODOを編集する権限がありません。")
            return redirect(url_for("student_goals_todos.todos"))

        if request.method == "POST":
            content = request.form.get("content", "").strip()
            due_date_str = request.form.get("due_date", "").strip()
            priority = request.form.get("priority", "medium")
            completed = request.form.get("completed") == "on"

            # 入力値検証
            if not content:
                flash("TODO内容を入力してください。", "error")
                return render_template("edit_todo.html", todo=todo)

            # 期限日の処理
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                except ValueError:
                    flash("正しい日付形式で入力してください。", "error")
                    return render_template("edit_todo.html", todo=todo)

            # TODOを更新
            todo.title = content
            todo.due_date = due_date
            todo.priority = priority
            todo.is_completed = completed

            try:
                db.session.commit()
                flash("TODOを更新しました。", "success")
                return redirect(url_for("student_goals_todos.todos"))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"TODO update error: {str(e)}")
                flash("TODOの更新に失敗しました。", "error")

        return render_template("edit_todo.html", todo=todo)

    except Exception as e:
        current_app.logger.error(f"Edit todo error: {str(e)}")
        flash("TODO編集画面の読み込み中にエラーが発生しました。")
        return redirect(url_for("student_goals_todos.todos"))


@goals_todos_bp.route("/delete_todo/<int:todo_id>")
@login_required
@student_required
def delete_todo(todo_id):
    """To Do削除"""
    try:
        todo = Todo.query.get_or_404(todo_id)

        # 権限チェック
        if todo.student_id != current_user.id:
            flash("このTODOを削除する権限がありません。")
            return redirect(url_for("student_goals_todos.todos"))

        try:
            db.session.delete(todo)
            db.session.commit()
            flash("TODOを削除しました。", "success")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"TODO deletion error: {str(e)}")
            flash("TODOの削除に失敗しました。", "error")

        return redirect(url_for("student_goals_todos.todos"))

    except Exception as e:
        current_app.logger.error(f"Delete todo error: {str(e)}")
        flash("TODO削除中にエラーが発生しました。")
        return redirect(url_for("student_goals_todos.todos"))


@goals_todos_bp.route("/toggle_todo/<int:todo_id>")
@login_required
@student_required
def toggle_todo(todo_id):
    """To Do完了状態切り替え"""
    try:
        todo = Todo.query.get_or_404(todo_id)

        # 権限チェック
        if todo.student_id != current_user.id:
            flash("このTODOを変更する権限がありません。")
            return redirect(url_for("student_goals_todos.todos"))

        # 完了状態を切り替え
        todo.is_completed = not todo.is_completed

        try:
            db.session.commit()
            status = "完了" if todo.is_completed else "未完了"
            flash(f"TODOを{status}にしました。", "success")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"TODO toggle error: {str(e)}")
            flash("TODOの状態変更に失敗しました。", "error")

        return redirect(url_for("student_goals_todos.todos"))

    except Exception as e:
        current_app.logger.error(f"Toggle todo error: {str(e)}")
        flash("TODO状態変更中にエラーが発生しました。")
        return redirect(url_for("student_goals_todos.todos"))


@goals_todos_bp.route("/goals")
@login_required
@student_required
def goals():
    """目標一覧"""
    try:
        goals = (
            Goal.query.filter_by(student_id=current_user.id)
            .order_by(Goal.created_at.desc())
            .all()
        )

        return render_template("goals.html", goals=goals)

    except Exception as e:
        current_app.logger.error(f"Goals list error: {str(e)}")
        flash("目標一覧の読み込み中にエラーが発生しました。")
        return redirect(url_for("student_dashboard.dashboard"))


@goals_todos_bp.route("/new_goal", methods=["GET", "POST"])
@login_required
@student_required
def new_goal():
    """新規目標作成"""
    try:
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            target_date_str = request.form.get("target_date", "").strip()

            # 入力値検証
            if not title:
                flash("目標タイトルを入力してください。", "error")
                return render_template("new_goal.html")

            # 目標期限の処理
            target_date = None
            if target_date_str:
                try:
                    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                except ValueError:
                    flash("正しい日付形式で入力してください。", "error")
                    return render_template("new_goal.html")

            # 新しい目標を作成
            new_goal = Goal(
                student_id=current_user.id,
                title=title,
                description=description,
                target_date=target_date,
                status="not_started",
            )

            try:
                db.session.add(new_goal)
                db.session.commit()
                flash("目標を作成しました。", "success")
                return redirect(url_for("student_goals_todos.goals"))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Goal creation error: {str(e)}")
                flash("目標の作成に失敗しました。", "error")

        return render_template("new_goal.html")

    except Exception as e:
        current_app.logger.error(f"New goal error: {str(e)}")
        flash("目標作成画面の読み込み中にエラーが発生しました。")
        return redirect(url_for("student_goals_todos.goals"))


@goals_todos_bp.route("/edit_goal/<int:goal_id>", methods=["GET", "POST"])
@login_required
@student_required
def edit_goal(goal_id):
    """目標編集"""
    try:
        goal = Goal.query.get_or_404(goal_id)

        # 権限チェック
        if goal.student_id != current_user.id:
            flash("この目標を編集する権限がありません。")
            return redirect(url_for("student_goals_todos.goals"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            target_date_str = request.form.get("target_date", "").strip()
            status = request.form.get("status", "not_started")
            progress = request.form.get("progress", 0, type=int)

            # 入力値検証
            if not title:
                flash("目標タイトルを入力してください。", "error")
                return render_template("edit_goal.html", goal=goal)

            if not (0 <= progress <= 100):
                flash("進捗は0-100の範囲で入力してください。", "error")
                return render_template("edit_goal.html", goal=goal)

            # 目標期限の処理
            target_date = None
            if target_date_str:
                try:
                    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                except ValueError:
                    flash("正しい日付形式で入力してください。", "error")
                    return render_template("edit_goal.html", goal=goal)

            # 目標を更新
            goal.title = title
            goal.description = description
            goal.target_date = target_date
            goal.status = status
            goal.progress = progress

            # ステータスによる自動完了日設定
            if status == "completed" and not goal.completed_at:
                goal.completed_at = datetime.utcnow()
            elif status != "completed":
                goal.completed_at = None

            try:
                db.session.commit()
                flash("目標を更新しました。", "success")
                return redirect(url_for("student_goals_todos.goals"))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Goal update error: {str(e)}")
                flash("目標の更新に失敗しました。", "error")

        return render_template("edit_goal.html", goal=goal)

    except Exception as e:
        current_app.logger.error(f"Edit goal error: {str(e)}")
        flash("目標編集画面の読み込み中にエラーが発生しました。")
        return redirect(url_for("student_goals_todos.goals"))


@goals_todos_bp.route("/delete_goal/<int:goal_id>")
@login_required
@student_required
def delete_goal(goal_id):
    """目標削除"""
    try:
        goal = Goal.query.get_or_404(goal_id)

        # 権限チェック
        if goal.student_id != current_user.id:
            flash("この目標を削除する権限がありません。")
            return redirect(url_for("student_goals_todos.goals"))

        try:
            db.session.delete(goal)
            db.session.commit()
            flash("目標を削除しました。", "success")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Goal deletion error: {str(e)}")
            flash("目標の削除に失敗しました。", "error")

        return redirect(url_for("student_goals_todos.goals"))

    except Exception as e:
        current_app.logger.error(f"Delete goal error: {str(e)}")
        flash("目標削除中にエラーが発生しました。")
        return redirect(url_for("student_goals_todos.goals"))


@goals_todos_bp.route("/update_goal_progress/<int:goal_id>", methods=["POST"])
@login_required
@student_required
def update_goal_progress(goal_id):
    """目標進捗更新"""
    try:
        goal = Goal.query.get_or_404(goal_id)

        # 権限チェック
        if goal.student_id != current_user.id:
            flash("この目標を更新する権限がありません。")
            return redirect(url_for("student_goals_todos.goals"))

        progress = request.form.get("progress", 0, type=int)

        # 進捗値の検証
        if not (0 <= progress <= 100):
            flash("進捗は0-100の範囲で入力してください。", "error")
            return redirect(url_for("student_goals_todos.goals"))

        # 進捗更新
        goal.progress = progress

        # 進捗によるステータス自動更新
        if progress == 0:
            goal.status = "not_started"
        elif progress == 100:
            goal.status = "completed"
            if not goal.completed_at:
                goal.completed_at = datetime.utcnow()
        else:
            goal.status = "in_progress"
            goal.completed_at = None

        try:
            db.session.commit()
            flash("目標の進捗を更新しました。", "success")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Goal progress update error: {str(e)}")
            flash("進捗の更新に失敗しました。", "error")

        return redirect(url_for("student_goals_todos.goals"))

    except Exception as e:
        current_app.logger.error(f"Update goal progress error: {str(e)}")
        flash("進捗更新中にエラーが発生しました。")
        return redirect(url_for("student_goals_todos.goals"))
