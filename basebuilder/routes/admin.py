"""
BaseBuilder Admin Routes
========================
管理者・教師向け管理機能に関するルートハンドラ

移行元: basebuilder/routes.py の以下のルート:
- /theme_relations (GET)
- /theme_relation/create (POST)
- /theme_relation/delete (POST)
- /problem/<int:problem_id>/delete (POST)
- /learning_paths (GET)
- /learning_path/create (GET, POST)
- /learning_path/<int:path_id>/edit (GET, POST)
- /learning_path/<int:path_id>/assign (GET, POST)
- /learning_path/<int:assignment_id>/start (GET)
- /learning_path/<int:assignment_id>/update_progress (POST)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
import json

from extensions import db
from app.models import InquiryTheme
from basebuilder.models import (
    ProblemCategory, BasicKnowledgeItem, KnowledgeThemeRelation,
    AnswerRecord, BaseBuilderLearningPath, PathAssignment
)

admin_bp = Blueprint('basebuilder_admin', __name__)


@admin_bp.route('/theme_relations')
@login_required
def theme_relations():
    """テーマと問題の関連付け管理"""
    try:
        if current_user.role != 'teacher':
            flash('この機能は教師のみ利用可能です。')
            return redirect(url_for('basebuilder_module.index'))
        
        current_app.logger.info(f"Theme relations accessed by teacher {current_user.id}")
        
        # すべてのテーマを取得
        themes = InquiryTheme.query.all()
        
        # すべての問題を取得
        problems = BasicKnowledgeItem.query.filter_by(is_active=True).all()
        
        # 既存の関連付けを取得
        existing_relations = KnowledgeThemeRelation.query.all()
        
        # テーマ別の関連問題を整理
        theme_problems = {}
        for relation in existing_relations:
            if relation.theme_id not in theme_problems:
                theme_problems[relation.theme_id] = []
            theme_problems[relation.theme_id].append({
                'problem': relation.problem,
                'relevance': relation.relevance
            })
        
        return render_template(
            'basebuilder/theme_relations.html',
            themes=themes,
            problems=problems,
            theme_problems=theme_problems
        )
        
    except Exception as e:
        current_app.logger.error(f"Theme relations error: {str(e)}")
        flash('テーマ関連付け画面の読み込み中にエラーが発生しました。')
        return redirect(url_for('basebuilder_module.index'))


@admin_bp.route('/theme_relation/create', methods=['POST'])
@login_required
def create_theme_relation():
    """テーマと問題の関連付け作成"""
    try:
        if current_user.role != 'teacher':
            return jsonify({'error': 'この機能は教師のみ利用可能です。'}), 403
        
        theme_id = request.form.get('theme_id', type=int)
        problem_id = request.form.get('problem_id', type=int)
        relevance = request.form.get('relevance', type=int, default=3)
        
        if not theme_id or not problem_id:
            return jsonify({'error': 'テーマと問題は必須です。'}), 400
        
        # 既に関連付けが存在するか確認
        existing = KnowledgeThemeRelation.query.filter_by(
            theme_id=theme_id,
            problem_id=problem_id
        ).first()
        
        if existing:
            # 関連性のみ更新
            existing.relevance = relevance
            db.session.commit()
            
            current_app.logger.info(f"Theme relation updated by teacher {current_user.id}: theme {theme_id}, problem {problem_id}")
            return jsonify({'success': True, 'message': '関連性が更新されました。'})
        
        # 新しい関連付けを作成
        new_relation = KnowledgeThemeRelation(
            theme_id=theme_id,
            problem_id=problem_id,
            relevance=relevance,
            created_by=current_user.id
        )
        
        db.session.add(new_relation)
        db.session.commit()
        
        current_app.logger.info(f"Theme relation created by teacher {current_user.id}: theme {theme_id}, problem {problem_id}")
        return jsonify({'success': True, 'message': '関連付けが作成されました。'})
        
    except Exception as e:
        current_app.logger.error(f"Create theme relation error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': '関連付けの作成中にエラーが発生しました。'}), 500


@admin_bp.route('/theme_relation/delete', methods=['POST'])
@login_required
def delete_theme_relation():
    """テーマと問題の関連付け削除"""
    try:
        if current_user.role != 'teacher':
            return jsonify({'error': 'この機能は教師のみ利用可能です。'}), 403
        
        theme_id = request.form.get('theme_id', type=int)
        problem_id = request.form.get('problem_id', type=int)
        
        if not theme_id or not problem_id:
            return jsonify({'error': 'テーマと問題は必須です。'}), 400
        
        # 関連付けを取得
        relation = KnowledgeThemeRelation.query.filter_by(
            theme_id=theme_id,
            problem_id=problem_id
        ).first_or_404()
        
        # 関連付けを削除
        db.session.delete(relation)
        db.session.commit()
        
        current_app.logger.info(f"Theme relation deleted by teacher {current_user.id}: theme {theme_id}, problem {problem_id}")
        return jsonify({'success': True, 'message': '関連付けが削除されました。'})
        
    except Exception as e:
        current_app.logger.error(f"Delete theme relation error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': '関連付けの削除中にエラーが発生しました。'}), 500


@admin_bp.route('/problem/<int:problem_id>/delete', methods=['POST'])
@login_required
def delete_problem(problem_id):
    """問題削除"""
    try:
        if current_user.role != 'teacher':
            flash('この機能は教師のみ利用可能です。')
            return redirect(url_for('basebuilder_module.index'))
        
        # 問題を取得
        problem = BasicKnowledgeItem.query.get_or_404(problem_id)
        
        # 作成者本人か確認
        if problem.created_by != current_user.id:
            flash('この問題を削除する権限がありません。')
            return redirect(url_for('problems.problems'))
        
        # 問題に関連する解答記録を削除（外部キー制約がある場合）
        AnswerRecord.query.filter_by(problem_id=problem_id).delete()
        
        # 問題に関連する関連付けを削除
        KnowledgeThemeRelation.query.filter_by(problem_id=problem_id).delete()
        
        # 問題を削除
        db.session.delete(problem)
        db.session.commit()
        
        current_app.logger.info(f"Problem {problem_id} deleted by teacher {current_user.id}")
        flash('問題が削除されました。')
        return redirect(url_for('problems.problems'))
        
    except Exception as e:
        current_app.logger.error(f"Delete problem error: {str(e)}")
        db.session.rollback()
        flash('問題の削除中にエラーが発生しました。')
        return redirect(url_for('problems.problems'))


@admin_bp.route('/learning_paths')
@login_required
def learning_paths():
    """学習パス管理"""
    try:
        # 学校に所属していない場合の対応
        if not current_user.school_id:
            flash('学習パスを表示するには学校に所属している必要があります。')
            return redirect(url_for('basebuilder_module.index'))
        
        current_app.logger.info(f"Learning paths accessed by user {current_user.id}")
        
        if current_user.role == 'student':
            # 学生向け - 割り当てられた学習パスを表示
            assigned_paths = PathAssignment.query.filter_by(
                student_id=current_user.id
            ).all()
            
            return render_template(
                'basebuilder/student_learning_paths.html',
                assigned_paths=assigned_paths
            )
        
        elif current_user.role == 'teacher':
            # 教師向け - 作成した学習パス + 同じ学校の学習パスを表示
            paths = BaseBuilderLearningPath.query.filter(
                (BaseBuilderLearningPath.created_by == current_user.id) |
                (BaseBuilderLearningPath.school_id == current_user.school_id)
            ).all()
            
            return render_template(
                'basebuilder/teacher_learning_paths.html',
                paths=paths
            )
        
        # その他のロールの場合
        return redirect(url_for('basebuilder_module.index'))
        
    except Exception as e:
        current_app.logger.error(f"Learning paths error: {str(e)}")
        flash('学習パス一覧の取得中にエラーが発生しました。')
        return redirect(url_for('basebuilder_module.index'))


@admin_bp.route('/learning_path/create', methods=['GET', 'POST'])
@login_required
def create_learning_path():
    """学習パス作成"""
    try:
        if current_user.role != 'teacher':
            flash('この機能は教師のみ利用可能です。')
            return redirect(url_for('basebuilder_module.index'))
        
        # 学校に所属していない場合の対応
        if not current_user.school_id:
            flash('学習パスを作成するには学校に所属している必要があります。')
            return redirect(url_for('basebuilder_module.index'))
        
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description', '')
            steps = request.form.get('steps', '[]')
            
            if not title:
                flash('タイトルは必須です。')
                return render_template('basebuilder/create_learning_path.html')
            
            # ステップがJSONとして有効かチェック
            try:
                steps_json = json.loads(steps)
            except json.JSONDecodeError:
                flash('ステップが正しいJSON形式ではありません。')
                return render_template('basebuilder/create_learning_path.html')
            
            # 新しい学習パスを作成
            new_path = BaseBuilderLearningPath(
                title=title,
                description=description,
                steps=steps,
                created_by=current_user.id,
                school_id=current_user.school_id  # 学校IDを設定
            )
            
            db.session.add(new_path)
            db.session.commit()
            
            current_app.logger.info(f"Learning path created by teacher {current_user.id}: {title}")
            flash('学習パスが作成されました。')
            return redirect(url_for('basebuilder_admin.learning_paths'))
        
        # 同じ学校のカテゴリを取得（ステップ作成用）
        categories = ProblemCategory.query.filter_by(school_id=current_user.school_id).all()
        
        return render_template(
            'basebuilder/create_learning_path.html',
            categories=categories
        )
        
    except Exception as e:
        current_app.logger.error(f"Create learning path error: {str(e)}")
        flash('学習パス作成画面の読み込み中にエラーが発生しました。')
        return redirect(url_for('basebuilder_admin.learning_paths'))


@admin_bp.route('/learning_path/<int:path_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_learning_path(path_id):
    """学習パス編集"""
    try:
        if current_user.role != 'teacher':
            flash('この機能は教師のみ利用可能です。')
            return redirect(url_for('basebuilder_module.index'))
        
        # 学習パスを取得
        path = BaseBuilderLearningPath.query.get_or_404(path_id)
        
        # 作成者本人か確認
        if path.created_by != current_user.id:
            flash('この学習パスを編集する権限がありません。')
            return redirect(url_for('basebuilder_admin.learning_paths'))
        
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description', '')
            steps = request.form.get('steps', '[]')
            is_active = 'is_active' in request.form
            
            if not title:
                flash('タイトルは必須です。')
                return render_template('basebuilder/edit_learning_path.html', path=path)
            
            # ステップがJSONとして有効かチェック
            try:
                steps_json = json.loads(steps)
            except json.JSONDecodeError:
                flash('ステップが正しいJSON形式ではありません。')
                return render_template('basebuilder/edit_learning_path.html', path=path)
            
            # 学習パスを更新
            path.title = title
            path.description = description
            path.steps = steps
            path.is_active = is_active
            
            db.session.commit()
            
            current_app.logger.info(f"Learning path {path_id} updated by teacher {current_user.id}")
            flash('学習パスが更新されました。')
            return redirect(url_for('basebuilder_admin.learning_paths'))
        
        # 問題カテゴリを取得（ステップ作成用）
        categories = ProblemCategory.query.all()
        
        return render_template(
            'basebuilder/edit_learning_path.html',
            path=path,
            categories=categories
        )
        
    except Exception as e:
        current_app.logger.error(f"Edit learning path error: {str(e)}")
        flash('学習パス編集画面の読み込み中にエラーが発生しました。')
        return redirect(url_for('basebuilder_admin.learning_paths'))


@admin_bp.route('/learning_path/<int:path_id>/assign', methods=['GET', 'POST'])
@login_required
def assign_learning_path(path_id):
    """学習パス割り当て"""
    try:
        if current_user.role != 'teacher':
            flash('この機能は教師のみ利用可能です。')
            return redirect(url_for('basebuilder_module.index'))
        
        # 学習パスを取得
        path = BaseBuilderLearningPath.query.get_or_404(path_id)
        
        # 教師のクラスを取得
        classes = getattr(current_user, 'classes_teaching', [])
        
        if request.method == 'POST':
            class_id = request.form.get('class_id', type=int)
            student_ids = request.form.getlist('student_ids')
            due_date_str = request.form.get('due_date', '')
            
            if not class_id or not student_ids:
                flash('クラスと学生は必須です。')
                return render_template(
                    'basebuilder/assign_learning_path.html',
                    path=path,
                    classes=classes
                )
            
            # 日付文字列をdateオブジェクトに変換
            due_date = None
            if due_date_str:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            
            # 選択した学生に学習パスを割り当て
            for student_id_str in student_ids:
                try:
                    student_id = int(student_id_str)
                    
                    # 既に割り当てられているか確認
                    existing = PathAssignment.query.filter_by(
                        path_id=path_id,
                        student_id=student_id
                    ).first()
                    
                    if existing:
                        # 既存の割り当てを更新
                        existing.due_date = due_date
                        existing.assigned_by = current_user.id
                        existing.assigned_at = datetime.utcnow()
                    else:
                        # 新しい割り当てを作成
                        assignment = PathAssignment(
                            path_id=path_id,
                            student_id=student_id,
                            assigned_by=current_user.id,
                            due_date=due_date
                        )
                        db.session.add(assignment)
                
                except ValueError:
                    continue
            
            db.session.commit()
            
            current_app.logger.info(f"Learning path {path_id} assigned to {len(student_ids)} students by teacher {current_user.id}")
            flash('学習パスが割り当てられました。')
            return redirect(url_for('basebuilder_admin.learning_paths'))
        
        return render_template(
            'basebuilder/assign_learning_path.html',
            path=path,
            classes=classes
        )
        
    except Exception as e:
        current_app.logger.error(f"Assign learning path error: {str(e)}")
        flash('学習パス割り当て画面の読み込み中にエラーが発生しました。')
        return redirect(url_for('basebuilder_admin.learning_paths'))


@admin_bp.route('/learning_path/<int:assignment_id>/start')
@login_required
def start_learning_path(assignment_id):
    """学習パス開始"""
    try:
        if current_user.role != 'student':
            flash('この機能は学生のみ利用可能です。')
            return redirect(url_for('basebuilder_module.index'))
        
        # 割り当てを取得
        assignment = PathAssignment.query.get_or_404(assignment_id)
        
        # 自分の割り当てか確認
        if assignment.student_id != current_user.id:
            flash('この学習パスを開始する権限がありません。')
            return redirect(url_for('basebuilder_admin.learning_paths'))
        
        # 学習パスを取得
        path = assignment.path
        
        # 進行状況を計算
        progress = assignment.progress
        
        # 学習パスのステップを取得
        steps = json.loads(path.steps)
        
        # 現在のステップを決定
        current_step_index = int(len(steps) * (progress / 100)) if steps else 0
        current_step = steps[current_step_index] if current_step_index < len(steps) else None
        
        current_app.logger.info(f"Learning path {assignment.path_id} started by student {current_user.id}")
        
        return render_template(
            'basebuilder/start_learning_path.html',
            assignment=assignment,
            path=path,
            steps=steps,
            current_step_index=current_step_index,
            current_step=current_step,
            progress=progress
        )
        
    except Exception as e:
        current_app.logger.error(f"Start learning path error: {str(e)}")
        flash('学習パスの開始中にエラーが発生しました。')
        return redirect(url_for('basebuilder_admin.learning_paths'))


@admin_bp.route('/learning_path/<int:assignment_id>/update_progress', methods=['POST'])
@login_required
def update_path_progress(assignment_id):
    """学習パス進捗更新"""
    try:
        if current_user.role != 'student':
            return jsonify({'error': 'この機能は学生のみ利用可能です。'}), 403
        
        # 割り当てを取得
        assignment = PathAssignment.query.get_or_404(assignment_id)
        
        # 自分の割り当てか確認
        if assignment.student_id != current_user.id:
            return jsonify({'error': 'この学習パスの進捗を更新する権限がありません。'}), 403
        
        # 進捗を更新
        progress = request.form.get('progress', type=int, default=0)
        completed = request.form.get('completed', type=bool, default=False)
        
        # 値の範囲を確認
        progress = max(0, min(100, progress))
        
        # 進捗を更新
        assignment.progress = progress
        assignment.completed = completed or (progress == 100)
        
        db.session.commit()
        
        current_app.logger.info(f"Learning path progress updated: assignment {assignment_id}, progress {progress}%")
        
        return jsonify({
            'success': True,
            'progress': progress,
            'completed': assignment.completed
        })
        
    except Exception as e:
        current_app.logger.error(f"Update path progress error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': '進捗更新中にエラーが発生しました。'}), 500