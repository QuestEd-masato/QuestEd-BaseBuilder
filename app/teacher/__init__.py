# app/teacher/__init__.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify, session, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime
import json
import csv
import io
import os
import logging

from app.models import (
    db, User, Class, ClassEnrollment, MainTheme, InquiryTheme,
    Milestone, StudentEvaluation, Curriculum, CurriculumUnit, RubricTemplate,
    Group, GroupMembership, School, InterestSurvey, PersonalitySurvey,
    ActivityLog, Goal, Todo, Subject
)
from app.ai import generate_student_evaluation, generate_curriculum_with_ai
from app.utils.model_helpers import mysql_nulls_last

# Conditional import to avoid circular imports
try:
    from app.ai.helpers import generate_activity_summary
except ImportError:
    def generate_activity_summary(*args, **kwargs):
        return "活動概要の生成に失敗しました。"
from app.models import ChatHistory

# Conditional import for PDF generator
try:
    from .pdf_generator import generate_student_report_pdf
except ImportError:
    def generate_student_report_pdf(*args, **kwargs):
        return None

teacher_bp = Blueprint('teacher', __name__)

def teacher_required(f):
    """教師権限を要求するデコレータ"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher':
            flash('この機能は教師のみ利用可能です。')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@teacher_bp.route('/teacher_dashboard')
@login_required
@teacher_required
def dashboard():
    """教師ダッシュボード（統合管理機能付き）"""
    from app.services.curriculum_bridge_service import CurriculumBridgeService
    
    # 教師が担当するクラスを取得
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    
    # 統合統計情報の初期化
    integrated_stats = {
        'total_curriculums': 0,
        'converted_curriculums': 0,
        'total_units': 0,
        'active_units': 0,
        'conversion_rate': 0
    }
    
    # 各クラスの生徒数と統計情報を計算
    class_info = []
    for class_obj in classes:
        # 生徒数を取得
        enrollments = ClassEnrollment.query.filter_by(class_id=class_obj.id).all()
        student_count = len(enrollments)
        
        # アンケート完了数を計算
        survey_completed = 0
        theme_selected = 0
        
        for enrollment in enrollments:
            student = enrollment.student
            # アンケート完了確認
            if student.has_completed_surveys():
                survey_completed += 1
            
            # テーマ選択確認
            selected_theme = InquiryTheme.query.filter_by(
                student_id=student.id,
                is_selected=True
            ).first()
            if selected_theme:
                theme_selected += 1
        
        # 次回のマイルストーンを取得
        next_milestone = Milestone.query.filter_by(class_id=class_obj.id)\
            .filter(Milestone.due_date >= datetime.utcnow().date())\
            .order_by(*mysql_nulls_last(Milestone.due_date, 'asc')).first()
        
        # カリキュラム・単元統合情報を取得
        curriculums = Curriculum.query.filter_by(
            class_id=class_obj.id,
            teacher_id=current_user.id
        ).all()
        
        curriculum_stats = {
            'total_curriculums': len(curriculums),
            'converted_count': 0,
            'total_units': 0,
            'recent_conversions': []
        }
        
        for curriculum in curriculums:
            # 変換状況をチェック
            conversion_status = CurriculumBridgeService.get_conversion_status(curriculum.id)
            if conversion_status.get('is_converted', False):
                curriculum_stats['converted_count'] += 1
                curriculum_stats['total_units'] += conversion_status.get('converted_units', 0)
                
                # 最近の変換履歴
                if conversion_status.get('conversion_date'):
                    curriculum_stats['recent_conversions'].append({
                        'curriculum_title': curriculum.title,
                        'conversion_date': conversion_status['conversion_date'],
                        'units_count': conversion_status.get('converted_units', 0)
                    })
        
        # 統合統計に加算
        integrated_stats['total_curriculums'] += curriculum_stats['total_curriculums']
        integrated_stats['converted_curriculums'] += curriculum_stats['converted_count']
        integrated_stats['total_units'] += curriculum_stats['total_units']
        
        class_info.append({
            'class': class_obj,
            'student_count': student_count,
            'survey_completed': survey_completed,
            'theme_selected': theme_selected,
            'next_milestone': next_milestone,
            'curriculum_stats': curriculum_stats  # 新規追加
        })
    
    # アクティブな単元数を取得
    integrated_stats['active_units'] = CurriculumUnit.query.filter_by(
        created_by=current_user.id,
        is_active=True
    ).count()
    
    # 変換率計算
    if integrated_stats['total_curriculums'] > 0:
        integrated_stats['conversion_rate'] = round(
            (integrated_stats['converted_curriculums'] / integrated_stats['total_curriculums']) * 100, 1
        )
    
    # 承認待ちの学生数を取得
    pending_students_count = 0
    if current_user.school_id:
        pending_students_count = User.query.filter_by(
            role='student',
            school_id=current_user.school_id,
            email_confirmed=True,
            is_approved=False
        ).count()
    
    return render_template('teacher_dashboard.html', 
                         classes=class_info,
                         pending_students_count=pending_students_count,
                         integrated_stats=integrated_stats)  # 新規追加

@teacher_bp.route('/teacher/pending_users')
@login_required
@teacher_required
def pending_users():
    """承認待ちユーザー一覧"""
    # 同じ学校の承認待ち学生を取得
    pending_students = User.query.filter_by(
        role='student',
        school_id=current_user.school_id,
        email_confirmed=True,
        is_approved=False
    ).all()
    
    return render_template('teacher/pending_users.html', pending_students=pending_students)

@teacher_bp.route('/teacher/approve_user/<int:user_id>', methods=['POST'])
@login_required
@teacher_required
def approve_user(user_id):
    """ユーザー承認"""
    user = User.query.get_or_404(user_id)
    
    # 同じ学校の学生のみ承認可能
    if user.school_id != current_user.school_id or user.role != 'student':
        flash('このユーザーを承認する権限がありません。')
        return redirect(url_for('teacher.pending_users'))
    
    user.is_approved = True
    db.session.commit()
    
    flash(f'{user.username} を承認しました。')
    return redirect(url_for('teacher.pending_users'))

# クラス管理
@teacher_bp.route('/classes')
@login_required
def classes():
    """クラス一覧"""
    if current_user.role == 'teacher':
        # 教師の場合は自分が担当するクラスのみ表示
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
        return render_template('teacher_classes.html', classes=classes)
    elif current_user.role == 'student':
        # 生徒の場合は履修しているクラスを表示
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]
        return render_template('student_classes.html', classes=classes)
    else:
        flash('アクセス権限がありません。')
        return redirect(url_for('index'))

@teacher_bp.route('/create_class', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_class():
    """クラス作成"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        subject_id = request.form.get('subject_id')
        schedule = request.form.get('schedule')
        location = request.form.get('location')
        
        # 必須フィールドの確認
        if not name:
            flash('クラス名は必須です。')
            subjects = Subject.query.filter_by(is_active=True).all()
            return render_template('create_class.html', subjects=subjects)
        
        if not subject_id:
            flash('教科は必須です。')
            subjects = Subject.query.filter_by(is_active=True).all()
            return render_template('create_class.html', subjects=subjects)
        
        # 教科名をクラス名に含める
        subject = Subject.query.get(subject_id)
        if subject:
            full_name = f"{name} ({subject.name})"
        else:
            full_name = name
        
        # 新しいクラスを作成
        new_class = Class(
            teacher_id=current_user.id,
            school_id=current_user.school_id,
            subject_id=subject_id,
            name=full_name,
            description=description,
            schedule=schedule,
            location=location
        )
        
        try:
            db.session.add(new_class)
            db.session.commit()
            flash(f'クラス「{full_name}」が作成されました。')
            return redirect(url_for('teacher.class_details', class_id=new_class.id))
        except Exception as e:
            db.session.rollback()
            flash('クラス作成中にエラーが発生しました。')
            logging.error(f"Class creation error: {str(e)}")
    
    # GETリクエスト時は教科リストを渡す
    subjects = Subject.query.filter_by(is_active=True).all()
    return render_template('create_class.html', subjects=subjects)

@teacher_bp.route('/class/<int:class_id>')
@login_required
def class_details(class_id):
    """クラス詳細"""
    class_obj = Class.query.get_or_404(class_id)
    
    # アクセス権限の確認
    if current_user.role == 'teacher' and class_obj.teacher_id != current_user.id:
        flash('このクラスへのアクセス権限がありません。')
        return redirect(url_for('teacher.classes'))
    elif current_user.role == 'student':
        enrollment = ClassEnrollment.query.filter_by(
            class_id=class_id,
            student_id=current_user.id
        ).first()
        if not enrollment:
            flash('このクラスへのアクセス権限がありません。')
            return redirect(url_for('teacher.classes'))
    
    # 生徒一覧を詳細情報と共に取得
    enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
    students_info = []
    
    for enrollment in enrollments:
        student = enrollment.student
        
        # 学生の選択したテーマを取得
        selected_theme = InquiryTheme.query.filter_by(
            student_id=student.id,
            is_selected=True
        ).first()
        
        # 最新の活動記録を取得
        latest_activity = ActivityLog.query.filter_by(
            student_id=student.id
        ).order_by(ActivityLog.timestamp.desc()).first()
        
        # 学生の情報をまとめる
        student_info = {
            'student': student,
            'enrollment': enrollment,
            'selected_theme': selected_theme,
            'latest_activity': latest_activity
        }
        students_info.append(student_info)
    
    # メインテーマを取得
    main_themes = MainTheme.query.filter_by(class_id=class_id).all()
    
    # マイルストーンを取得
    milestones = Milestone.query.filter_by(class_id=class_id).order_by(*mysql_nulls_last(Milestone.due_date, 'asc')).all()
    
    return render_template('class_details.html', 
                         class_obj=class_obj, 
                         students_info=students_info,
                         main_themes=main_themes,
                         milestones=milestones,
                         today=datetime.now().date())

@teacher_bp.route('/view_class/<int:class_id>')
@login_required
def view_class(class_id):
    """クラス詳細表示（リダイレクト用）"""
    return redirect(url_for('teacher.class_details', class_id=class_id))

@teacher_bp.route('/class/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_class(class_id):
    """クラス編集"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスを編集する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    # 教科リストを取得
    subjects = Subject.query.filter_by(is_active=True).order_by(Subject.id).all()
    
    if request.method == 'POST':
        class_obj.name = request.form.get('name', class_obj.name)
        class_obj.description = request.form.get('description', class_obj.description)
        class_obj.schedule = request.form.get('schedule', class_obj.schedule)
        class_obj.location = request.form.get('location', class_obj.location)
        
        # 教科IDを保存
        subject_id = request.form.get('subject_id')
        if subject_id:
            class_obj.subject_id = int(subject_id)
        else:
            class_obj.subject_id = None
        
        db.session.commit()
        flash('クラス情報が更新されました。')
        return redirect(url_for('teacher.class_details', class_id=class_id))
    
    return render_template('edit_class.html', class_obj=class_obj, subjects=subjects)

@teacher_bp.route('/class/<int:class_id>/delete')
@login_required
@teacher_required
def delete_class(class_id):
    """クラス削除"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスを削除する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    # 関連データも含めて削除
    db.session.delete(class_obj)
    db.session.commit()
    
    flash('クラスが削除されました。')
    return redirect(url_for('teacher.classes'))

@teacher_bp.route('/class/<int:class_id>/add_students', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_students(class_id):
    """クラスに生徒を追加"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスに生徒を追加する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        added_count = 0
        error_count = 0
        
        # CSVファイルアップロードの処理
        if 'csv_file' in request.files:
            file = request.files['csv_file']
            if file and file.filename.endswith('.csv'):
                try:
                    # CSVファイルを読み込む
                    import csv
                    import io
                    stream = io.StringIO(file.stream.read().decode('utf-8'))
                    csv_reader = csv.DictReader(stream)
                    
                    for row in csv_reader:
                        username = row.get('username', '').strip()
                        if username:
                            student = User.query.filter_by(username=username, role='student').first()
                            if student and student.school_id == current_user.school_id:
                                # 既に登録されていないか確認
                                existing = ClassEnrollment.query.filter_by(
                                    class_id=class_id,
                                    student_id=student.id
                                ).first()
                                
                                if not existing:
                                    enrollment = ClassEnrollment(
                                        class_id=class_id,
                                        student_id=student.id
                                    )
                                    db.session.add(enrollment)
                                    added_count += 1
                            else:
                                error_count += 1
                except Exception as e:
                    flash(f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
                    return redirect(url_for('teacher.add_students', class_id=class_id))
        
        # テキスト入力での処理（フォールバック）
        elif 'student_usernames' in request.form:
            student_usernames = request.form.get('student_usernames', '').split(',')
            
            for username in student_usernames:
                username = username.strip()
                if username:
                    student = User.query.filter_by(username=username, role='student').first()
                    if student and student.school_id == current_user.school_id:
                        # 既に登録されていないか確認
                        existing = ClassEnrollment.query.filter_by(
                            class_id=class_id,
                            student_id=student.id
                        ).first()
                        
                        if not existing:
                            enrollment = ClassEnrollment(
                                class_id=class_id,
                                student_id=student.id
                            )
                            db.session.add(enrollment)
                            added_count += 1
        
        db.session.commit()
        
        if added_count > 0:
            flash(f'{added_count}名の生徒をクラスに追加しました。')
        if error_count > 0:
            flash(f'{error_count}名の生徒が見つからないか、追加できませんでした。')
        if added_count == 0 and error_count == 0:
            flash('生徒が追加されませんでした。CSVファイルまたはユーザー名を確認してください。')
        
        return redirect(url_for('teacher.class_details', class_id=class_id))
    
    # 未登録の生徒一覧を取得
    enrolled_student_ids = [e.student_id for e in ClassEnrollment.query.filter_by(class_id=class_id).all()]
    available_students = User.query.filter_by(
        role='student',
        school_id=current_user.school_id,
        is_approved=True
    ).filter(~User.id.in_(enrolled_student_ids)).all()
    
    return render_template('add_students.html', class_obj=class_obj, available_students=available_students)

@teacher_bp.route('/download_student_template')
@login_required
@teacher_required
def download_student_template():
    """生徒追加用CSVテンプレートダウンロード"""
    from app.utils.csv_helper import export_to_csv_utf8_bom
    
    # サンプルデータを作成
    template_data = [
        {'username': 'taro_yamada'},
        {'username': 'hanako_tanaka'},
        {'username': 'jiro_suzuki'}
    ]
    
    return export_to_csv_utf8_bom(
        template_data,
        'student_add_template.csv',
        headers=['username']
    )

@teacher_bp.route('/class/<int:class_id>/remove_student/<int:student_id>', methods=['POST'])
@login_required
@teacher_required
def remove_student(class_id, student_id):
    """クラスから生徒を削除"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    enrollment = ClassEnrollment.query.filter_by(
        class_id=class_id,
        student_id=student_id
    ).first()
    
    if enrollment:
        db.session.delete(enrollment)
        db.session.commit()
        flash('生徒をクラスから削除しました。')
    
    return redirect(url_for('teacher.class_details', class_id=class_id))

# メインテーマ管理
@teacher_bp.route('/class/<int:class_id>/main_themes')
@login_required
@teacher_required
def view_main_themes(class_id):
    """メインテーマ一覧"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのテーマを表示する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    main_themes = MainTheme.query.filter_by(class_id=class_id).all()
    
    return render_template('main_themes.html', class_obj=class_obj, main_themes=main_themes)

@teacher_bp.route('/class/<int:class_id>/main_themes/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_main_theme(class_id):
    """メインテーマ作成"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスにテーマを作成する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        if not title:
            flash('タイトルは必須です。')
            return render_template('create_main_theme.html', class_obj=class_obj)
        
        new_theme = MainTheme(
            teacher_id=current_user.id,
            class_id=class_id,
            title=title,
            description=description
        )
        
        db.session.add(new_theme)
        db.session.commit()
        
        flash('メインテーマが作成されました。')
        return redirect(url_for('teacher.view_main_themes', class_id=class_id))
    
    return render_template('create_main_theme.html', class_obj=class_obj)

@teacher_bp.route('/main_theme/<int:theme_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_main_theme(theme_id):
    """メインテーマ編集"""
    theme = MainTheme.query.get_or_404(theme_id)
    
    # 権限チェック
    if theme.teacher_id != current_user.id:
        flash('このテーマを編集する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        theme.title = request.form.get('title', theme.title)
        theme.description = request.form.get('description', theme.description)
        theme.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('メインテーマが更新されました。')
        return redirect(url_for('teacher.view_main_themes', class_id=theme.class_id))
    
    return render_template('edit_main_theme.html', theme=theme)

@teacher_bp.route('/main_theme/<int:theme_id>/delete')
@login_required
@teacher_required
def delete_main_theme(theme_id):
    """メインテーマ削除"""
    theme = MainTheme.query.get_or_404(theme_id)
    
    # 権限チェック
    if theme.teacher_id != current_user.id:
        flash('このテーマを削除する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    class_id = theme.class_id
    db.session.delete(theme)
    db.session.commit()
    
    flash('メインテーマが削除されました。')
    return redirect(url_for('teacher.view_main_themes', class_id=class_id))

# マイルストーン管理
@teacher_bp.route('/create_milestone/<int:class_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_milestone(class_id):
    """マイルストーン作成"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスにマイルストーンを作成する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date_str = request.form.get('due_date')
        
        if not title or not due_date_str:
            flash('タイトルと期限日は必須です。')
            return render_template('create_milestone.html', class_=class_obj, now=datetime.now())
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('日付の形式が正しくありません。')
            return render_template('create_milestone.html', class_=class_obj, now=datetime.now())
        
        new_milestone = Milestone(
            class_id=class_id,
            title=title,
            description=description,
            due_date=due_date
        )
        
        db.session.add(new_milestone)
        db.session.commit()
        
        flash('マイルストーンが作成されました。')
        return redirect(url_for('teacher.class_details', class_id=class_id))
    
    return render_template('create_milestone.html', class_=class_obj, now=datetime.now())

@teacher_bp.route('/edit_milestone/<int:milestone_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_milestone(milestone_id):
    """マイルストーン編集"""
    milestone = Milestone.query.get_or_404(milestone_id)
    class_obj = milestone.class_obj
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このマイルストーンを編集する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        milestone.title = request.form.get('title', milestone.title)
        milestone.description = request.form.get('description', milestone.description)
        
        due_date_str = request.form.get('due_date')
        if due_date_str:
            try:
                milestone.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('日付の形式が正しくありません。')
                return render_template('edit_milestone.html', milestone=milestone)
        
        db.session.commit()
        flash('マイルストーンが更新されました。')
        return redirect(url_for('teacher.class_details', class_id=class_obj.id))
    
    return render_template('edit_milestone.html', milestone=milestone)

@teacher_bp.route('/delete_milestone/<int:milestone_id>')
@login_required
@teacher_required
def delete_milestone(milestone_id):
    """マイルストーン削除"""
    milestone = Milestone.query.get_or_404(milestone_id)
    class_obj = milestone.class_obj
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このマイルストーンを削除する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    db.session.delete(milestone)
    db.session.commit()
    
    flash('マイルストーンが削除されました。')
    return redirect(url_for('teacher.class_details', class_id=class_obj.id))

# 評価関連
@teacher_bp.route('/class/<int:class_id>/generate_evaluations', methods=['GET', 'POST'])
@login_required
@teacher_required
def generate_evaluations(class_id):
    """生徒評価生成"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスの評価を生成する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    # 生徒一覧を取得
    enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
    students = [enrollment.student for enrollment in enrollments]
    
    # カリキュラムを取得
    curriculum = Curriculum.query.filter_by(class_id=class_id).first()
    
    # ルーブリックテンプレートを取得
    rubric = RubricTemplate.query.filter_by(class_id=class_id).first()
    
    if request.method == 'POST':
        selected_student_ids = request.form.getlist('student_ids')
        
        if not selected_student_ids:
            flash('評価する生徒を選択してください。')
            return render_template('evaluate_students.html', 
                                 class_obj=class_obj, 
                                 students=students,
                                 curriculum=curriculum,
                                 rubric=rubric)
        
        evaluations = []
        
        for student_id in selected_student_ids:
            student = User.query.get(int(student_id))
            if not student:
                continue
            
            # 生徒の探究テーマを取得
            theme = InquiryTheme.query.filter_by(
                student_id=student.id,
                is_selected=True
            ).first()
            
            # 生徒の目標を取得
            goals = Goal.query.filter_by(student_id=student.id).all()
            
            # 生徒の活動記録を取得
            activity_logs = ActivityLog.query.filter_by(student_id=student.id).all()
            
            # カリキュラムとルーブリックのデータを準備
            curriculum_data = json.loads(curriculum.content) if curriculum and curriculum.content else None
            rubric_data = json.loads(rubric.content) if rubric and rubric.content else None
            
            # AI評価を生成
            evaluation_text = generate_student_evaluation(
                student, theme, goals, activity_logs, curriculum_data, rubric_data
            )
            
            # 評価を保存
            existing_eval = StudentEvaluation.query.filter_by(
                student_id=student.id,
                class_id=class_id
            ).first()
            
            if existing_eval:
                existing_eval.evaluation_text = evaluation_text
                existing_eval.updated_at = datetime.utcnow()
            else:
                new_eval = StudentEvaluation(
                    student_id=student.id,
                    class_id=class_id,
                    evaluation_text=evaluation_text
                )
                db.session.add(new_eval)
            
            evaluations.append({
                'student': student,
                'evaluation': evaluation_text
            })
        
        db.session.commit()
        
        # 評価をセッションに保存（エクスポート用）
        import json
        session['evaluations'] = json.dumps([
            {
                'student_name': eval['student'].username,
                'evaluation': eval['evaluation']
            } for eval in evaluations
        ])
        session['class_name'] = class_obj.name
        session['class_id'] = class_id
        
        flash(f'{len(evaluations)}名の評価を生成しました。')
        return render_template('evaluation_results.html', 
                             evaluations=evaluations,
                             class_obj=class_obj)
    
    return render_template('evaluate_students.html', 
                         class_obj=class_obj, 
                         students=students,
                         curriculum=curriculum,
                         rubric=rubric)

# カリキュラム管理
@teacher_bp.route('/class/<int:class_id>/curriculums')
@login_required
@teacher_required
def view_curriculums(class_id):
    """カリキュラム一覧"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのカリキュラムを表示する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    curriculums = Curriculum.query.filter_by(class_id=class_id).all()
    
    return render_template('curriculums.html', 
                         class_obj=class_obj, 
                         curriculums=curriculums)

@teacher_bp.route('/class/<int:class_id>/curriculum/create')
@login_required
@teacher_required
def create_curriculum_form(class_id):
    """カリキュラム作成フォーム"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのカリキュラムを作成する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    # メインテーマを取得
    main_themes = MainTheme.query.filter_by(class_id=class_id).all()
    
    return render_template('create_curriculum.html', 
                         class_obj=class_obj,
                         main_themes=main_themes)

@teacher_bp.route('/class/<int:class_id>/curriculum/generate', methods=['POST'])
@login_required
@teacher_required
def generate_curriculum(class_id):
    """AIによるカリキュラム生成"""
    try:
        class_obj = Class.query.get_or_404(class_id)
        # 権限チェック
        if class_obj.teacher_id != current_user.id:
            return jsonify({'error': '権限がありません'}), 403
        
        # フォームデータとJSONデータの両方に対応
        if request.is_json:
            data = request.get_json()
        else:
            # 通常のフォームデータの場合
            data = {
                'title': request.form.get('title', ''),
                'subject': request.form.get('subject', ''),
                'grade': request.form.get('grade', ''),
                'duration': request.form.get('duration', ''),
                'focus_areas': request.form.get('focus_areas', '')
            }
        
        if not data or not data.get('title'):
            return jsonify({'error': 'タイトルは必須です'}), 400
        
        # AIでカリキュラムを生成
        try:
            from app.ai import generate_curriculum_with_ai
            curriculum_content = generate_curriculum_with_ai(data)
        except Exception as ai_error:
            current_app.logger.error(f"AI generation error: {str(ai_error)}")
            # フォールバック
            curriculum_content = {
                'title': data.get('title'),
                'description': f"{class_obj.name}のカリキュラム",
                'content': '1. 基礎学習\n2. 応用学習\n3. 発展学習'
            }
        
        # カリキュラムを保存
        new_curriculum = Curriculum(
            class_id=class_id,
            title=curriculum_content.get('title', data.get('title')),
            description=curriculum_content.get('description', ''),
            content=curriculum_content.get('content', ''),
            teacher_id=current_user.id
        )
        db.session.add(new_curriculum)
        db.session.commit()
        
        # フォームからのリクエストの場合はリダイレクト
        if not request.is_json:
            flash('カリキュラムが作成されました。', 'success')
            return redirect(url_for('teacher.view_curriculums', class_id=class_id))
        
        # JSONリクエストの場合
        return jsonify({
            'success': True,
            'redirect': url_for('teacher.view_curriculums', class_id=class_id)
        })
        
    except Exception as e:
        current_app.logger.error(f"Curriculum generation error: {str(e)}")
        db.session.rollback()
        
        if not request.is_json:
            flash('カリキュラムの生成に失敗しました。', 'error')
            return redirect(url_for('teacher.create_curriculum', class_id=class_id))
        
        return jsonify({
            'error': 'カリキュラムの生成に失敗しました',
            'details': str(e)
        }), 500

# グループ管理
@teacher_bp.route('/class/<int:class_id>/groups')
@login_required
@teacher_required
def view_groups(class_id):
    """グループ一覧"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのグループを表示する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    groups = Group.query.filter_by(class_id=class_id).all()
    
    return render_template('view_groups.html', 
                         class_obj=class_obj, 
                         groups=groups)

@teacher_bp.route('/class/<int:class_id>/groups/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_group(class_id):
    """グループ作成"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスにグループを作成する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            flash('グループ名は必須です。')
            return render_template('create_group.html', class_obj=class_obj)
        
        new_group = Group(
            name=name,
            description=description,
            class_id=class_id,
            created_by=current_user.id
        )
        
        db.session.add(new_group)
        db.session.commit()
        
        flash('グループが作成されました。')
        return redirect(url_for('teacher.view_groups', class_id=class_id))
    
    return render_template('create_group.html', class_obj=class_obj)

# 生徒インポート
def process_student_csv(file, class_id, current_user):
    """CSVファイルから生徒情報を処理"""
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_reader = csv.DictReader(stream)
    
    results = {
        'created': [],
        'enrolled': [],
        'errors': []
    }
    
    for row_num, row in enumerate(csv_reader, 2):
        try:
            # 必須フィールドの確認
            username = row.get('username', '').strip()
            email = row.get('email', '').strip()
            student_number = row.get('student_number', '').strip()
            
            if not username or not email:
                results['errors'].append(f"行 {row_num}: ユーザー名とメールアドレスは必須です")
                continue
            
            # 既存ユーザーチェック
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                # 既存ユーザーをクラスに登録
                if existing_user.role == 'student' and existing_user.school_id == current_user.school_id:
                    existing_enrollment = ClassEnrollment.query.filter_by(
                        class_id=class_id,
                        student_id=existing_user.id
                    ).first()
                    
                    if not existing_enrollment:
                        enrollment = ClassEnrollment(
                            class_id=class_id,
                            student_id=existing_user.id
                        )
                        db.session.add(enrollment)
                        results['enrolled'].append(username)
                    else:
                        results['errors'].append(f"行 {row_num}: {username} は既にクラスに登録されています")
                else:
                    results['errors'].append(f"行 {row_num}: {username} は生徒ではないか、異なる学校に所属しています")
            else:
                # 新規ユーザー作成
                existing_email = User.query.filter_by(email=email).first()
                if existing_email:
                    results['errors'].append(f"行 {row_num}: メール {email} は既に使用されています")
                    continue
                
                # パスワード生成
                import random
                import string
                password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
                
                new_user = User(
                    username=username,
                    email=email,
                    password=generate_password_hash(password),
                    role='student',
                    school_id=current_user.school_id,
                    email_confirmed=True,
                    is_approved=True
                )
                
                db.session.add(new_user)
                db.session.flush()  # IDを取得
                
                # クラスに登録
                enrollment = ClassEnrollment(
                    class_id=class_id,
                    student_id=new_user.id
                )
                db.session.add(enrollment)
                
                results['created'].append({
                    'username': username,
                    'password': password
                })
                
        except Exception as e:
            results['errors'].append(f"行 {row_num}: エラー - {str(e)}")
    
    return results

@teacher_bp.route('/class/<int:class_id>/students/import', methods=['GET', 'POST'])
@login_required
@teacher_required
def import_students(class_id):
    """生徒一括インポート"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスに生徒をインポートする権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('ファイルが選択されていません。')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('ファイルが選択されていません。')
            return redirect(request.url)
        
        if not file.filename.endswith('.csv'):
            flash('CSVファイルを選択してください。')
            return redirect(request.url)
        
        try:
            results = process_student_csv(file, class_id, current_user)
            
            # コミット
            db.session.commit()
            
            # 結果メッセージ
            if results['created']:
                flash(f"{len(results['created'])}名の新規生徒を作成しました。")
            if results['enrolled']:
                flash(f"{len(results['enrolled'])}名の既存生徒をクラスに追加しました。")
            if results['errors']:
                for error in results['errors'][:5]:  # 最初の5件のエラーを表示
                    flash(error, 'error')
                if len(results['errors']) > 5:
                    flash(f"... 他 {len(results['errors']) - 5} 件のエラー", 'error')
            
            # 作成されたアカウント情報を表示
            if results['created']:
                return render_template('import_results.html', 
                                     created_accounts=results['created'],
                                     class_obj=class_obj)
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"生徒インポートエラー: {e}")
            flash(f'インポート中にエラーが発生しました: {str(e)}', 'error')
        
        return redirect(url_for('teacher.class_details', class_id=class_id))
    
    return render_template('teacher_import_students.html', class_obj=class_obj)

# テーマ管理
@teacher_bp.route('/teacher_themes')
@login_required
@teacher_required
def teacher_themes():
    """教師のテーマ管理ページ"""
    # 教師が担当するクラスを取得
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    
    # 各クラスのメインテーマを取得
    classes_with_themes = []  # 変数名をテンプレートに合わせて変更
    for class_obj in classes:
        main_themes = MainTheme.query.filter_by(class_id=class_obj.id).all()  # themesをmain_themesに変更
        classes_with_themes.append({
            'class': class_obj,
            'main_themes': main_themes  # キー名をmain_themesに変更
        })
    
    return render_template('teacher_themes.html', classes_with_themes=classes_with_themes)  # 変数名を変更

# 最初のクラスを取得するAPI
@teacher_bp.route('/api/teacher/first_class')
@login_required
@teacher_required
def api_teacher_first_class():
    """教師の最初のクラスを取得"""
    first_class = Class.query.filter_by(teacher_id=current_user.id).first()
    if first_class:
        return jsonify({'class_id': first_class.id})
    else:
        return jsonify({'class_id': None})

# チャット機能
@teacher_bp.route('/teacher_chat')
@login_required
def chat_page():
    """チャットページ"""
    # デバッグ用ログ
    current_app.logger.info(f"Teacher chat access by user: {current_user.username}, role: {current_user.role}")
    
    # チャット履歴を取得
    from app.models import ChatHistory
    chat_history = ChatHistory.query.filter_by(user_id=current_user.id)\
        .order_by(ChatHistory.timestamp)\
        .all()
    
    return render_template('chat.html', chat_history=chat_history)

@teacher_bp.route('/class/<int:class_id>/student/<int:student_id>/generate_report', methods=['POST'])
@login_required
@teacher_required
def generate_student_report(class_id, student_id):
    """学生の活動報告PDFを生成"""
    # 権限確認
    class_obj = Class.query.get_or_404(class_id)
    if class_obj.teacher_id != current_user.id:
        flash('このクラスにアクセスする権限がありません。')
        return redirect(url_for('teacher.dashboard'))
    
    # 学生情報取得
    student = User.query.get_or_404(student_id)
    enrollment = ClassEnrollment.query.filter_by(
        student_id=student_id,
        class_id=class_id,
        is_active=True
    ).first()
    
    if not enrollment:
        flash('この学生はクラスに所属していません。')
        return redirect(url_for('teacher.class_details', class_id=class_id))
    
    try:
        # 探究テーマを取得
        theme = InquiryTheme.query.filter_by(
            student_id=student_id,
            class_id=class_id,
            is_selected=True
        ).first()
        
        # 活動記録を取得（最新50件）
        activities = ActivityLog.query.filter_by(
            student_id=student_id,
            class_id=class_id
        ).order_by(ActivityLog.timestamp.desc()).limit(50).all()
        
        # チャット履歴を取得（最新100件）
        chat_histories = ChatHistory.query.filter_by(
            user_id=student_id,
            class_id=class_id
        ).order_by(ChatHistory.timestamp.desc()).limit(100).all()
        
        # AI要約を生成
        activity_texts = [a.content for a in activities if a.content]
        chat_texts = [c.message for c in chat_histories if c.is_user and c.message]
        ai_summary = generate_activity_summary(activity_texts, chat_texts)
        
        # PDF生成
        pdf_buffer = generate_student_report_pdf(
            student, class_obj, activities, chat_histories, theme, ai_summary
        )
        
        # レスポンス作成（メモリから直接送信、保存しない）
        from flask import make_response
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=report_{student.username}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        current_app.logger.info(f"PDF generated for student {student.username} in class {class_obj.name}")
        return response
        
    except Exception as e:
        current_app.logger.error(f"PDF generation error: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash('PDF生成中にエラーが発生しました。')
        return redirect(url_for('teacher.class_details', class_id=class_id))

# カリキュラム関連の追加ルート
@teacher_bp.route('/class/<int:class_id>/curriculum/import', methods=['GET', 'POST'])
@login_required
@teacher_required
def import_curriculum(class_id):
    """カリキュラムのインポート"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのカリキュラムをインポートする権限がありません。')
        return redirect(url_for('teacher.dashboard'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('ファイルが選択されていません。')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('ファイルが選択されていません。')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                # CSVファイルを読み込む
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_reader = csv.DictReader(stream)
                
                # カリキュラムデータを解析
                curriculum_data = []
                for row in csv_reader:
                    curriculum_data.append(row)
                
                # カリキュラムを作成
                new_curriculum = Curriculum(
                    class_id=class_id,
                    teacher_id=current_user.id,
                    title=request.form.get('title', f'{class_obj.name}のカリキュラム'),
                    description=request.form.get('description', ''),
                    total_hours=int(request.form.get('total_hours', 35)),
                    has_fieldwork=request.form.get('has_fieldwork') == 'true',
                    fieldwork_count=int(request.form.get('fieldwork_count', 0)),
                    has_presentation=request.form.get('has_presentation') == 'true',
                    presentation_format=request.form.get('presentation_format', 'プレゼンテーション'),
                    group_work_level=request.form.get('group_work_level', 'ハイブリッド'),
                    external_collaboration=request.form.get('external_collaboration') == 'true',
                    content=json.dumps(curriculum_data, ensure_ascii=False)
                )
                
                db.session.add(new_curriculum)
                db.session.commit()
                
                flash('カリキュラムをインポートしました。')
                return redirect(url_for('teacher.view_curriculums', class_id=class_id))
                
            except Exception as e:
                flash(f'インポートエラー: {str(e)}')
                return redirect(request.url)
    
    return render_template('upload_curriculum.html', class_obj=class_obj)

@teacher_bp.route('/curriculum/<int:curriculum_id>', methods=['GET', 'POST'])
@login_required
def view_curriculum(curriculum_id):
    """統合されたカリキュラム表示・編集画面"""
    from app.models import ProblemCategory, TextSet
    from sqlalchemy import text
    
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    can_edit = False
    if current_user.role == 'teacher' and curriculum.teacher_id == current_user.id:
        can_edit = True
    elif current_user.role == 'student':
        # 生徒のクラス所属確認
        enrollment = db.session.execute(text("""
            SELECT 1 FROM class_enrollments 
            WHERE student_id = :student_id AND class_id = :class_id AND is_active = 1
        """), {
            'student_id': current_user.id,
            'class_id': curriculum.class_id
        }).first()
        
        if enrollment:
            can_edit = False  # 生徒は閲覧のみ
        else:
            flash('このカリキュラムにアクセスする権限がありません。', 'error')
            return redirect(url_for('student.dashboard'))
    else:
        # その他のユーザーはアクセス不可
        flash('このページへのアクセス権限がありません。', 'error')
        return redirect(url_for('index'))
    
    # クラス情報を取得
    class_obj = Class.query.get_or_404(curriculum.class_id)
    
    # POST処理（編集保存）
    if request.method == 'POST' and can_edit:
        try:
            # 基本情報の更新
            curriculum.title = request.form.get('title', '').strip()
            curriculum.description = request.form.get('description', '').strip()
            
            # formatがtableまたは未設定の場合の処理
            if not hasattr(curriculum, 'format') or curriculum.format == 'table' or not curriculum.format:
                # テーブル形式での保存
                items_count = int(request.form.get('items_count', 0))
                
                # 既存アイテムをクリア
                db.session.execute(text("""
                    DELETE FROM curriculum_items WHERE curriculum_id = :curriculum_id
                """), {'curriculum_id': curriculum_id})
                
                # 新規アイテムを保存
                for i in range(items_count):
                    phase = request.form.get(f'phase_{i}', '')
                    week = request.form.get(f'week_{i}', '')
                    hours = request.form.get(f'hours_{i}', '0')
                    category = request.form.get(f'category_{i}', '')
                    activity = request.form.get(f'activity_{i}', '')
                    teacher_support = request.form.get(f'teacher_support_{i}', '')
                    evaluation_method = request.form.get(f'evaluation_method_{i}', '')
                    
                    if phase or week or activity:  # 少なくとも1つのフィールドに値がある場合
                        db.session.execute(text("""
                            INSERT INTO curriculum_items 
                            (curriculum_id, phase, week, hours, category, activity, 
                             teacher_support, evaluation_method, order_index)
                            VALUES 
                            (:curriculum_id, :phase, :week, :hours, :category, 
                             :activity, :teacher_support, :evaluation_method, :order_index)
                        """), {
                            'curriculum_id': curriculum_id,
                            'phase': phase,
                            'week': week,
                            'hours': int(hours) if hours.isdigit() else 0,
                            'category': category,
                            'activity': activity,
                            'teacher_support': teacher_support,
                            'evaluation_method': evaluation_method,
                            'order_index': i
                        })
                
                # formatを更新
                if hasattr(curriculum, 'format'):
                    curriculum.format = 'table'
                curriculum.updated_at = datetime.utcnow()
                db.session.commit()
                flash('カリキュラムを更新しました。', 'success')
            
            else:
                # レガシーJSON形式の処理（既存のまま）
                flash('JSON形式のカリキュラムは現在サポートされていません。', 'warning')
                
        except Exception as e:
            db.session.rollback()
            flash(f'保存中にエラーが発生しました: {str(e)}', 'error')
            current_app.logger.error(f"Curriculum save error: {str(e)}")
        
        return redirect(url_for('teacher.view_curriculum', curriculum_id=curriculum_id))
    
    # GET処理（表示）
    curriculum_items = []
    problem_categories = []
    
    try:
        # カリキュラム項目の取得
        items = db.session.execute(text("""
            SELECT id, phase, week, hours, category, activity, 
                   teacher_support, evaluation_method, order_index
            FROM curriculum_items
            WHERE curriculum_id = :curriculum_id
            ORDER BY order_index, id
        """), {'curriculum_id': curriculum_id}).fetchall()
        
        for item in items:
            curriculum_items.append({
                'id': item.id,
                'phase': item.phase,
                'week': item.week,
                'hours': item.hours,
                'category': item.category,
                'activity': item.activity,
                'teacher_support': item.teacher_support,
                'evaluation_method': item.evaluation_method
            })
        
        # 問題カテゴリの取得
        problem_categories = ProblemCategory.query.filter(
            (ProblemCategory.school_id == current_user.school_id) | 
            (ProblemCategory.school_id.is_(None))
        ).order_by(ProblemCategory.name).all()
        
    except Exception as e:
        current_app.logger.error(f"Error loading curriculum data: {str(e)}")
        flash('データの読み込み中にエラーが発生しました。', 'warning')
    
    # 表示データの準備
    context = {
        'curriculum': curriculum,
        'class_obj': class_obj,
        'curriculum_items': curriculum_items,
        'problem_categories': problem_categories,
        'can_edit': can_edit
    }
    
    return render_template('curriculum_unified.html', **context)

@teacher_bp.route('/curriculum/<int:curriculum_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_curriculum(curriculum_id):
    """カリキュラム編集"""
    from app.services.curriculum_service import CurriculumService
    
    if request.method == 'POST':
        # 更新データの準備
        update_data = {
            'title': request.form.get('title', '').strip(),
            'description': request.form.get('description', '').strip()
        }
        
        # カリキュラム設定の収集
        curriculum_settings = {}
        
        # 基本設定
        if request.form.get('total_hours'):
            try:
                curriculum_settings['total_hours'] = int(request.form.get('total_hours', 0))
            except ValueError:
                curriculum_settings['total_hours'] = 0
        
        # フィールドワーク設定
        curriculum_settings['has_fieldwork'] = 'has_fieldwork' in request.form
        if curriculum_settings['has_fieldwork']:
            try:
                curriculum_settings['fieldwork_count'] = int(request.form.get('fieldwork_count', 0))
            except ValueError:
                curriculum_settings['fieldwork_count'] = 0
        
        # 発表設定
        curriculum_settings['has_presentation'] = 'has_presentation' in request.form
        if curriculum_settings['has_presentation']:
            curriculum_settings['presentation_format'] = request.form.get('presentation_format', '')
        
        # その他設定
        curriculum_settings['group_work_level'] = request.form.get('group_work_level', 'medium')
        curriculum_settings['external_collaboration'] = 'external_collaboration' in request.form
        
        # JSON コンテンツの処理
        raw_content = request.form.get('content')
        if raw_content:
            try:
                import json
                parsed_content = json.loads(raw_content)
                curriculum_settings.update(parsed_content)
            except json.JSONDecodeError:
                flash('カリキュラム内容の形式が正しくありません。', 'error')
                # エラー時は再表示
                curriculum, curriculum_data, error = CurriculumService.get_curriculum_safe(
                    curriculum_id, current_user.id
                )
                if error:
                    flash(error, 'error')
                    return redirect(url_for('teacher.dashboard'))
                
                class_obj = Class.query.get_or_404(curriculum.class_id)
                display_data = CurriculumService.get_curriculum_display_data(curriculum)
                now = datetime.now()
                
                return render_template('edit_curriculum.html',
                                     curriculum=curriculum,
                                     class_obj=class_obj,
                                     curriculum_content=curriculum_data,
                                     curriculum_data=display_data,
                                     now=now,
                                     error_occurred=True,
                                     **display_data)
        
        # コンテンツ設定をupdate_dataに追加
        if curriculum_settings:
            update_data['content'] = curriculum_settings
        
        # CurriculumServiceの安全な更新メソッドを使用
        success, message = CurriculumService.update_curriculum_safe(
            curriculum_id, update_data, current_user.id
        )
        
        if success:
            # 自動同期トリガー
            try:
                from app.services.auto_sync_service import AutoSyncService, SyncTriggerType
                
                # 自動同期すべきかチェック
                should_sync, sync_info = AutoSyncService.should_auto_sync(curriculum_id)
                
                if should_sync:
                    # 非同期で自動同期を実行（バックグラウンド）
                    current_app.logger.info(f"Triggering auto sync for curriculum {curriculum_id}")
                    # 注意: 実際の本番環境では、Celeryやrq等のタスクキューを使用すべき
                    # ここでは簡易実装として直接実行
                    sync_result = AutoSyncService.execute_auto_sync(
                        curriculum_id, SyncTriggerType.AUTO_UPDATE
                    )
                    
                    if sync_result['success']:
                        flash(f'{message} 関連単元も自動更新されました。', 'success')
                    else:
                        flash(f'{message} 注意: 単元の自動更新に問題がありました。', 'warning')
                else:
                    flash(message, 'success')
                    
            except Exception as e:
                current_app.logger.error(f"Auto sync trigger error: {str(e)}", exc_info=True)
                flash(f'{message} 注意: 自動同期でエラーが発生しました。', 'warning')
            
            return redirect(url_for('teacher.view_curriculum', curriculum_id=curriculum_id))
        else:
            flash(message, 'error')
    
    # GET時または更新失敗時の表示処理
    curriculum, curriculum_data, error_message = CurriculumService.get_curriculum_safe(
        curriculum_id, current_user.id
    )
    
    if error_message:
        flash(error_message, 'error')
        return redirect(url_for('teacher.dashboard'))
    
    # クラス情報を取得
    class_obj = Class.query.get_or_404(curriculum.class_id)
    
    # 表示用データの準備
    display_data = CurriculumService.get_curriculum_display_data(curriculum)
    now = datetime.now()
    
    return render_template('edit_curriculum.html',
                         curriculum=curriculum,
                         class_obj=class_obj,
                         curriculum_content=curriculum_data,
                         curriculum_data=display_data,
                         now=now,
                         **display_data)

@teacher_bp.route('/curriculum/<int:curriculum_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_curriculum(curriculum_id):
    """カリキュラム削除"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    class_obj = Class.query.get_or_404(curriculum.class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このカリキュラムを削除する権限がありません。')
        return redirect(url_for('teacher.dashboard'))
    
    db.session.delete(curriculum)
    db.session.commit()
    
    flash('カリキュラムを削除しました。')
    return redirect(url_for('teacher.view_curriculums', class_id=class_obj.id))

@teacher_bp.route('/curriculum/<int:curriculum_id>/export')
@login_required
@teacher_required
def export_curriculum(curriculum_id):
    """カリキュラムエクスポート"""
    from app.services.curriculum_service import CurriculumService
    from app.utils.csv_helper import export_to_csv_utf8_bom
    
    # CurriculumServiceの安全なCSVエクスポートメソッドを使用
    csv_data, error_message = CurriculumService.export_curriculum_to_csv(curriculum_id)
    
    if error_message:
        flash(f'エクスポートエラー: {error_message}', 'error')
        return redirect(url_for('teacher.dashboard'))
    
    if not csv_data:
        flash('エクスポートするデータがありません。', 'warning')
        return redirect(url_for('teacher.view_curriculum', curriculum_id=curriculum_id))
    
    # カリキュラム情報を取得してファイル名に使用
    curriculum = Curriculum.query.get(curriculum_id)
    filename = f'curriculum_{curriculum.title.replace(" ", "_")}_{curriculum_id}.csv' if curriculum else f'curriculum_{curriculum_id}.csv'
    
    return export_to_csv_utf8_bom(
        csv_data,
        filename,
        field_order=list(csv_data[0].keys()) if csv_data else None
    )

@teacher_bp.route('/curriculum/download_template')
@login_required
@teacher_required
def download_curriculum_template():
    """カリキュラムテンプレートダウンロード"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # テンプレートヘッダー
    writer.writerow(['週', '時限', 'テーマ', '活動内容', '評価方法'])
    
    # サンプルデータ
    writer.writerow(['1', '1-2', 'オリエンテーション', '探究学習の概要説明', '参加態度'])
    writer.writerow(['2', '1-2', 'テーマ設定', '興味関心の探索', 'ワークシート'])
    
    output.seek(0)
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=curriculum_template.csv'
        }
    )
    
    return response


# ランキング分析機能
@teacher_bp.route('/ranking_analysis')
@login_required
@teacher_required
def ranking_analysis():
    """ランキング分析ページ"""
    from app.services.ranking_service import RankingService
    
    # 教師が担当するクラス一覧を取得  
    # Note: Class.is_activeフィールドが存在しないため、フィルタを削除
    teacher_classes = Class.query.filter_by(
        teacher_id=current_user.id
    ).all()
    
    # クエリパラメータを取得
    ranking_type = request.args.get('type', 'total_points')
    class_id = request.args.get('class_id', type=int)
    
    # デフォルトで最初のクラスを選択
    if not class_id and teacher_classes:
        class_id = teacher_classes[0].id
    
    ranking_data = {}
    class_analytics = {}
    
    if class_id:
        # 選択されたクラスのランキングデータを取得
        ranking_data = RankingService.get_ranking(ranking_type, 'class', class_id)
        
        # クラス分析データを作成
        class_analytics = _generate_class_analytics(class_id, ranking_type)
    
    return render_template('teacher/ranking_analysis.html',
                         ranking_data=ranking_data,
                         class_analytics=class_analytics,
                         ranking_type=ranking_type,
                         class_id=class_id,
                         teacher_classes=teacher_classes)


@teacher_bp.route('/api/class_ranking/<int:class_id>/<ranking_type>')
@login_required
@teacher_required
def api_class_ranking(class_id, ranking_type):
    """クラスランキングAPI"""
    from app.services.ranking_service import RankingService
    
    # 教師の権限チェック
    class_obj = Class.query.filter_by(
        id=class_id,
        teacher_id=current_user.id,
        is_active=True
    ).first()
    
    if not class_obj:
        return {'error': 'アクセス権限がありません'}, 403
    
    ranking_data = RankingService.get_ranking(ranking_type, 'class', class_id)
    
    # 詳細分析データを追加
    analytics = _generate_class_analytics(class_id, ranking_type)
    ranking_data['analytics'] = analytics
    
    return ranking_data


def _generate_class_analytics(class_id: int, ranking_type: str) -> dict:
    """クラス分析データを生成"""
    from app.services.ranking_service import RankingService
    
    analytics = {
        'class_average': 0,
        'school_average': 0,
        'top_performers': [],
        'improvement_needed': [],
        'trends': {},
        'participation_rate': 0
    }
    
    try:
        # クラスのランキングデータを取得
        class_ranking = RankingService.get_ranking(ranking_type, 'class', class_id, limit=100)
        
        if class_ranking['rankings']:
            # クラス平均を計算
            scores = [r['score'] for r in class_ranking['rankings']]
            analytics['class_average'] = round(sum(scores) / len(scores), 2)
            
            # トップパフォーマーと改善が必要な学生を特定
            sorted_rankings = sorted(class_ranking['rankings'], key=lambda x: x['score'], reverse=True)
            
            analytics['top_performers'] = sorted_rankings[:3]  # 上位3名
            analytics['improvement_needed'] = sorted_rankings[-3:] if len(sorted_rankings) >= 3 else []  # 下位3名
            
            # 参加率を計算
            from app.models import ClassEnrollment
            total_students = ClassEnrollment.query.filter_by(
                class_id=class_id,
                is_active=True
            ).count()
            
            if total_students > 0:
                analytics['participation_rate'] = round((len(class_ranking['rankings']) / total_students) * 100, 1)
        
        # 学校全体の平均と比較
        school_ranking = RankingService.get_ranking(ranking_type, 'school', None, limit=1000)
        if school_ranking['rankings']:
            school_scores = [r['score'] for r in school_ranking['rankings']]
            analytics['school_average'] = round(sum(school_scores) / len(school_scores), 2)
        
    except Exception as e:
        logger.error(f"クラス分析データ生成エラー: {str(e)}")
    
    return analytics


# ========================================
# カリキュラム機能 v2 - シンプル設計
# ========================================

@teacher_bp.route('/curriculum/<int:curriculum_id>/view-v2')
@login_required
def view_curriculum_simple(curriculum_id):
    """シンプルなカリキュラム表示 (v2)"""
    from app.services.curriculum_service_v2 import CurriculumServiceV2
    
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    class_obj = Class.query.get_or_404(curriculum.class_id)
    
    # 権限チェック
    if not (current_user.role == 'teacher' and current_user.id == curriculum.teacher_id):
        if current_user.role == 'student':
            # 生徒の場合はクラス所属チェック
            enrollment = ClassEnrollment.query.filter_by(
                student_id=current_user.id,
                class_id=curriculum.class_id
            ).first()
            if not enrollment:
                flash('このカリキュラムを閲覧する権限がありません。', 'error')
                return redirect(url_for('main.index'))
        else:
            flash('権限がありません', 'error')
            return redirect(url_for('main.index'))
    
    # カリキュラム項目取得
    curriculum_items = CurriculumServiceV2.get_curriculum_items(curriculum_id)
    curriculum_stats = CurriculumServiceV2.get_curriculum_stats(curriculum_id)
    
    return render_template('curriculum/view_simple.html',
                         curriculum=curriculum,
                         class_obj=class_obj,
                         curriculum_items=curriculum_items,
                         curriculum_stats=curriculum_stats,
                         now=datetime.now())

@teacher_bp.route('/curriculum/<int:curriculum_id>/edit-v2', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_curriculum_simple(curriculum_id):
    """シンプルなカリキュラム編集 (v2)"""
    from app.services.curriculum_service_v2 import CurriculumServiceV2
    
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    class_obj = Class.query.get_or_404(curriculum.class_id)
    
    if curriculum.teacher_id != current_user.id:
        flash('編集権限がありません', 'error')
        return redirect(url_for('teacher.dashboard'))
    
    if request.method == 'POST':
        data = request.get_json()
        
        try:
            # 基本情報更新
            curriculum.title = data.get('title', curriculum.title)
            curriculum.description = data.get('description', curriculum.description)
            curriculum.updated_at = datetime.utcnow()
            
            # 項目の更新
            items = data.get('items', [])
            success, message = CurriculumServiceV2.save_curriculum_items(curriculum_id, items)
            
            if success:
                db.session.commit()
                logger.info(f"Curriculum {curriculum_id} updated successfully by user {current_user.id}")
                return jsonify({'success': True, 'message': message})
            else:
                db.session.rollback()
                return jsonify({'success': False, 'message': message}), 500
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Curriculum update error for ID {curriculum_id}: {str(e)}")
            return jsonify({'success': False, 'message': 'エラーが発生しました'}), 500
    
    # GET: 編集画面表示
    curriculum_items = CurriculumServiceV2.get_curriculum_items(curriculum_id)
    return render_template('curriculum/edit_simple.html',
                         curriculum=curriculum,
                         class_obj=class_obj,
                         curriculum_items=curriculum_items,
                         now=datetime.now())

@teacher_bp.route('/curriculum/<int:curriculum_id>/import-v2', methods=['POST'])
@login_required
@teacher_required
def import_curriculum_v2(curriculum_id):
    """CSVインポート (v2)"""
    from app.services.curriculum_service_v2 import CurriculumServiceV2
    
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    if curriculum.teacher_id != current_user.id:
        return jsonify({'success': False, 'message': '権限がありません'}), 403
    
    data = request.get_json()
    csv_content = data.get('csv_content', '')
    
    success, message = CurriculumServiceV2.import_from_csv(curriculum_id, csv_content)
    
    if success:
        logger.info(f"CSV imported for curriculum {curriculum_id} by user {current_user.id}")
    
    return jsonify({'success': success, 'message': message})

@teacher_bp.route('/curriculum/<int:curriculum_id>/export-v2')
@login_required
def export_curriculum_v2(curriculum_id):
    """CSVエクスポート (v2)"""
    from app.services.curriculum_service_v2 import CurriculumServiceV2
    from app.utils.csv_helper import export_to_csv_utf8_bom
    
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック（教師または所属学生）
    if current_user.role == 'teacher':
        if curriculum.teacher_id != current_user.id:
            flash('エクスポート権限がありません', 'error')
            return redirect(url_for('teacher.dashboard'))
    elif current_user.role == 'student':
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=curriculum.class_id
        ).first()
        if not enrollment:
            flash('エクスポート権限がありません', 'error')
            return redirect(url_for('main.index'))
    else:
        flash('権限がありません', 'error')
        return redirect(url_for('main.index'))
    
    # CSVデータ生成
    csv_data, error_message = CurriculumServiceV2.export_to_csv(curriculum_id)
    
    if error_message:
        flash(f'エクスポートエラー: {error_message}', 'error')
        return redirect(url_for('teacher.view_curriculum_simple', curriculum_id=curriculum_id))
    
    if not csv_data:
        flash('エクスポートするデータがありません。', 'warning')
        return redirect(url_for('teacher.view_curriculum_simple', curriculum_id=curriculum_id))
    
    # ファイル名生成
    safe_title = curriculum.title.replace(' ', '_').replace('/', '_')
    filename = f'curriculum_{safe_title}_{curriculum_id}.csv'
    
    return export_to_csv_utf8_bom(
        csv_data,
        filename,
        field_order=['フェーズ', '週', '時間数', 'カテゴリ', '活動内容', '教師のサポート', '評価方法']
    )

@teacher_bp.route('/curriculum/<int:curriculum_id>/migrate', methods=['POST'])
@login_required
@teacher_required
def migrate_curriculum_to_v2(curriculum_id):
    """JSONフォーマットから新フォーマットへの移行"""
    from app.services.curriculum_service_v2 import CurriculumServiceV2
    
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    if curriculum.teacher_id != current_user.id:
        return jsonify({'success': False, 'message': '権限がありません'}), 403
    
    success, message = CurriculumServiceV2.migrate_from_json(curriculum_id)
    
    if success:
        logger.info(f"Curriculum {curriculum_id} migrated to v2 format by user {current_user.id}")
    
    return jsonify({'success': success, 'message': message})

@teacher_bp.route('/curriculum/<int:curriculum_id>/convert-to-units', methods=['POST'])
@login_required
@teacher_required
def convert_curriculum_to_units(curriculum_id):
    """カリキュラムを自由進度学習単元に変換"""
    from app.services.curriculum_bridge_service import CurriculumBridgeService
    
    current_app.logger.info(f"Starting curriculum conversion for ID {curriculum_id} by user {current_user.id}")
    
    try:
        curriculum = Curriculum.query.get_or_404(curriculum_id)
        current_app.logger.info(f"Found curriculum: {curriculum.title}")
        
        # 権限チェック
        if curriculum.teacher_id != current_user.id:
            current_app.logger.warning(f"Permission denied: curriculum {curriculum_id} belongs to user {curriculum.teacher_id}, requested by {current_user.id}")
            return jsonify({
                'success': False, 
                'message': 'このカリキュラムを変換する権限がありません'
            }), 403
        
        # カリキュラムデータの事前チェック
        if not curriculum.curriculum_data:
            current_app.logger.warning(f"Curriculum {curriculum_id} has no curriculum_data")
            return jsonify({
                'success': False,
                'message': 'カリキュラムデータが設定されていません'
            }), 400
        
        # JSON解析チェック
        try:
            import json
            curriculum_data = json.loads(curriculum.curriculum_data)
            items = curriculum_data.get('items', [])
            current_app.logger.info(f"Curriculum {curriculum_id} has {len(items)} items to convert")
            
            if not items:
                return jsonify({
                    'success': False,
                    'message': 'カリキュラムに変換可能な項目がありません'
                }), 400
                
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Invalid JSON in curriculum {curriculum_id}: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'カリキュラムデータの形式が不正です'
            }), 400
        
        # トランザクション開始
        db.session.begin()
        
        # 変換実行
        current_app.logger.info(f"Executing conversion for curriculum {curriculum_id}")
        result = CurriculumBridgeService.convert_curriculum_to_units(
            curriculum_id, 
            current_user.id
        )
        
        if result['success']:
            # トランザクションコミット
            db.session.commit()
            
            current_app.logger.info(
                f"Curriculum {curriculum_id} converted successfully by user {current_user.id}: "
                f"{result['converted_count']} created, {result.get('updated_count', 0)} updated"
            )
            
            return jsonify({
                'success': True,
                'message': result['message'],
                'data': {
                    'converted_count': result['converted_count'],
                    'updated_count': result.get('updated_count', 0),
                    'total_items': result.get('total_items', 0),
                    'curriculum_title': curriculum.title
                }
            })
        else:
            # トランザクションロールバック
            db.session.rollback()
            current_app.logger.error(f"Conversion failed for curriculum {curriculum_id}: {result['message']}")
            
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        # トランザクションロールバック
        db.session.rollback()
        current_app.logger.error(f"Curriculum conversion error for ID {curriculum_id}: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'message': f'変換中にエラーが発生しました: {str(e)}',
            'error_details': str(e) if current_app.debug else None
        }), 500

@teacher_bp.route('/curriculum/sync-all', methods=['POST'])
@login_required
@teacher_required
def sync_all_curriculums():
    """全カリキュラムを単元に一括変換"""
    from app.services.curriculum_bridge_service import CurriculumBridgeService
    
    try:
        # 1. 教師の全カリキュラムを取得
        curriculums = Curriculum.query.filter_by(
            teacher_id=current_user.id
        ).all()
        
        if not curriculums:
            return jsonify({
                'success': True,
                'message': '変換対象のカリキュラムがありません',
                'data': {
                    'converted_count': 0,
                    'failed_count': 0,
                    'total_count': 0
                }
            })
        
        # 2. 各カリキュラムを単元に変換
        converted_count = 0
        failed_count = 0
        conversion_results = []
        
        for curriculum in curriculums:
            try:
                current_app.logger.info(f"Converting curriculum {curriculum.id}: {curriculum.title}")
                
                result = CurriculumBridgeService.convert_curriculum_to_units(
                    curriculum.id, 
                    current_user.id
                )
                
                if result['success']:
                    converted_count += 1
                    conversion_results.append({
                        'id': curriculum.id,
                        'title': curriculum.title,
                        'status': 'success',
                        'converted_count': result['converted_count'],
                        'updated_count': result.get('updated_count', 0)
                    })
                else:
                    failed_count += 1
                    conversion_results.append({
                        'id': curriculum.id,
                        'title': curriculum.title,
                        'status': 'failed',
                        'error': result['message']
                    })
                    
            except Exception as e:
                failed_count += 1
                current_app.logger.error(f"Individual curriculum conversion error: {str(e)}", exc_info=True)
                conversion_results.append({
                    'id': curriculum.id,
                    'title': curriculum.title,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # 3. 結果を返す
        success_message = f'{converted_count}個のカリキュラムを単元に変換しました'
        if failed_count > 0:
            success_message += f'（{failed_count}個のカリキュラムで失敗）'
        
        current_app.logger.info(f"Bulk curriculum conversion completed: {converted_count} success, {failed_count} failed")
        
        return jsonify({
            'success': True,
            'message': success_message,
            'data': {
                'converted_count': converted_count,
                'failed_count': failed_count,
                'total_count': len(curriculums),
                'details': conversion_results
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Sync all curriculums error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'一括変換中にエラーが発生しました: {str(e)}'
        }), 500

@teacher_bp.route('/curriculum/<int:curriculum_id>/conversion-status')
@login_required
@teacher_required
def get_curriculum_conversion_status(curriculum_id):
    """カリキュラムの変換状況を取得"""
    from app.services.curriculum_bridge_service import CurriculumBridgeService
    
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        status = CurriculumBridgeService.get_conversion_status(curriculum_id)
        return jsonify(status)
        
    except Exception as e:
        current_app.logger.error(f"Conversion status error: {str(e)}", exc_info=True)
        return jsonify({'error': '状況取得エラー'}), 500

@teacher_bp.route('/curriculum/batch-convert', methods=['POST'])
@login_required
@teacher_required
def batch_convert_curriculums():
    """複数カリキュラムの一括変換"""
    from app.services.curriculum_bridge_service import CurriculumBridgeService
    
    try:
        data = request.get_json()
        curriculum_ids = data.get('curriculum_ids', [])
        
        if not curriculum_ids:
            return jsonify({'success': False, 'message': '変換対象のカリキュラムが選択されていません'}), 400
        
        # 権限チェック：すべてのカリキュラムが自分のものか確認
        invalid_curriculums = []
        for curriculum_id in curriculum_ids:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum or curriculum.teacher_id != current_user.id:
                invalid_curriculums.append(curriculum_id)
        
        if invalid_curriculums:
            return jsonify({
                'success': False, 
                'message': f'権限のないカリキュラムが含まれています: {invalid_curriculums}'
            }), 403
        
        # 一括変換実行
        conversion_results = []
        total_converted = 0
        total_updated = 0
        failed_conversions = []
        
        for curriculum_id in curriculum_ids:
            try:
                result = CurriculumBridgeService.convert_curriculum_to_units(
                    curriculum_id, current_user.id
                )
                
                if result['success']:
                    conversion_results.append({
                        'curriculum_id': curriculum_id,
                        'success': True,
                        'converted_count': result['converted_count'],
                        'updated_count': result.get('updated_count', 0)
                    })
                    total_converted += result['converted_count']
                    total_updated += result.get('updated_count', 0)
                else:
                    failed_conversions.append({
                        'curriculum_id': curriculum_id,
                        'error': result['message']
                    })
                    
            except Exception as e:
                failed_conversions.append({
                    'curriculum_id': curriculum_id,
                    'error': str(e)
                })
        
        # 結果の集計
        success_count = len(conversion_results)
        failure_count = len(failed_conversions)
        
        response_data = {
            'success': True,
            'message': f'一括変換完了: {success_count}件成功, {failure_count}件失敗',
            'summary': {
                'processed': len(curriculum_ids),
                'successful': success_count,
                'failed': failure_count,
                'total_converted_units': total_converted,
                'total_updated_units': total_updated
            },
            'results': conversion_results,
            'failures': failed_conversions
        }
        
        current_app.logger.info(
            f"Batch conversion completed by user {current_user.id}: "
            f"{success_count} successful, {failure_count} failed"
        )
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Batch conversion error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': '一括変換中にエラーが発生しました'
        }), 500

@teacher_bp.route('/curriculum/sync-all', methods=['POST'])
@login_required
@teacher_required
def sync_all_converted_curriculums():
    """変換済みカリキュラムの一括同期"""
    from app.services.curriculum_bridge_service import CurriculumBridgeService
    
    try:
        # 自分が作成した変換済みカリキュラムを取得
        converted_curriculums = Curriculum.query.filter_by(
            teacher_id=current_user.id,
            is_converted_to_units=True
        ).all()
        
        if not converted_curriculums:
            return jsonify({
                'success': False,
                'message': '同期対象の変換済みカリキュラムがありません'
            })
        
        sync_results = []
        successful_syncs = 0
        failed_syncs = []
        
        for curriculum in converted_curriculums:
            try:
                result = CurriculumBridgeService.sync_curriculum_updates(curriculum.id)
                
                if result['success']:
                    sync_results.append({
                        'curriculum_id': curriculum.id,
                        'curriculum_title': curriculum.title,
                        'success': True,
                        'message': result['message']
                    })
                    successful_syncs += 1
                else:
                    failed_syncs.append({
                        'curriculum_id': curriculum.id,
                        'curriculum_title': curriculum.title,
                        'error': result['message']
                    })
                    
            except Exception as e:
                failed_syncs.append({
                    'curriculum_id': curriculum.id,
                    'curriculum_title': curriculum.title,
                    'error': str(e)
                })
        
        response_data = {
            'success': True,
            'message': f'一括同期完了: {successful_syncs}件成功, {len(failed_syncs)}件失敗',
            'summary': {
                'processed': len(converted_curriculums),
                'successful': successful_syncs,
                'failed': len(failed_syncs)
            },
            'results': sync_results,
            'failures': failed_syncs
        }
        
        current_app.logger.info(
            f"Batch sync completed by user {current_user.id}: "
            f"{successful_syncs} successful, {len(failed_syncs)} failed"
        )
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Batch sync error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': '一括同期中にエラーが発生しました'
        }), 500

@teacher_bp.route('/integrated-management')
@login_required
@teacher_required
def integrated_management():
    """統合管理画面"""
    from app.services.curriculum_bridge_service import CurriculumBridgeService
    
    try:
        # 教師の全カリキュラムを取得
        curriculums = Curriculum.query.filter_by(teacher_id=current_user.id).all()
        
        # 各カリキュラムの詳細情報を収集
        curriculum_details = []
        for curriculum in curriculums:
            conversion_status = CurriculumBridgeService.get_conversion_status(curriculum.id)
            
            # 関連する単元を取得
            units = CurriculumUnit.query.filter_by(
                legacy_curriculum_id=curriculum.id,
                is_active=True
            ).all()
            
            curriculum_details.append({
                'curriculum': curriculum,
                'conversion_status': conversion_status,
                'units': units,
                'units_count': len(units)
            })
        
        # 全体統計
        overall_stats = {
            'total_curriculums': len(curriculums),
            'converted_count': sum(1 for detail in curriculum_details if detail['conversion_status'].get('is_converted', False)),
            'total_units': sum(detail['units_count'] for detail in curriculum_details),
            'active_units': CurriculumUnit.query.filter_by(created_by=current_user.id, is_active=True).count()
        }
        
        return render_template('teacher/integrated_management.html',
                             curriculum_details=curriculum_details,
                             overall_stats=overall_stats)
                             
    except Exception as e:
        current_app.logger.error(f"Integrated management error: {str(e)}", exc_info=True)
        flash('統合管理画面の読み込みに失敗しました。')
        return redirect(url_for('teacher.dashboard'))

@teacher_bp.route('/unit/<int:unit_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_unit(unit_id):
    """単元編集"""
    unit = CurriculumUnit.query.get_or_404(unit_id)
    
    # 権限チェック
    if unit.created_by != current_user.id:
        flash('この単元を編集する権限がありません。')
        return redirect(url_for('teacher.integrated_management'))
    
    if request.method == 'POST':
        try:
            # フォームデータを取得
            unit.title = request.form.get('title', '').strip()
            unit.description = request.form.get('description', '').strip()
            unit.difficulty_level = int(request.form.get('difficulty_level', 2))
            unit.estimated_minutes = int(request.form.get('estimated_minutes', 45))
            unit.learning_objectives = request.form.get('learning_objectives', '').strip()
            unit.is_active = 'is_active' in request.form
            unit.updated_at = datetime.utcnow()
            
            # タグの処理
            tags_input = request.form.get('tags', '').strip()
            if tags_input:
                tags_list = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                unit.tags = json.dumps(tags_list, ensure_ascii=False)
            else:
                unit.tags = None
            
            db.session.commit()
            
            flash('単元が正常に更新されました。', 'success')
            return redirect(url_for('teacher.integrated_management'))
            
        except ValueError as e:
            flash(f'入力値に誤りがあります: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unit edit error: {str(e)}", exc_info=True)
            flash('単元の更新に失敗しました。', 'error')
    
    # 元のカリキュラム情報を取得
    source_curriculum = None
    if unit.legacy_curriculum_id:
        source_curriculum = Curriculum.query.get(unit.legacy_curriculum_id)
    
    # タグを文字列に変換
    tags_string = ''
    if unit.tags:
        try:
            tags_list = json.loads(unit.tags)
            tags_string = ', '.join(tags_list)
        except (json.JSONDecodeError, TypeError):
            tags_string = ''
    
    return render_template('teacher/edit_unit.html',
                         unit=unit,
                         source_curriculum=source_curriculum,
                         tags_string=tags_string)

@teacher_bp.route('/unit/<int:unit_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_unit(unit_id):
    """単元削除（論理削除）"""
    unit = CurriculumUnit.query.get_or_404(unit_id)
    
    # 権限チェック
    if unit.created_by != current_user.id:
        return jsonify({'success': False, 'message': '権限がありません'}), 403
    
    try:
        # 論理削除（is_activeをFalseに）
        unit.is_active = False
        unit.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        current_app.logger.info(f"Unit {unit_id} deactivated by user {current_user.id}")
        
        return jsonify({
            'success': True,
            'message': '単元が正常に削除されました'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unit delete error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': '単元の削除に失敗しました'
        }), 500

@teacher_bp.route('/curriculum/<int:curriculum_id>/auto-sync-settings', methods=['GET', 'POST'])
@login_required
@teacher_required
def auto_sync_settings(curriculum_id):
    """自動同期設定画面"""
    from app.services.auto_sync_service import AutoSyncService
    
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash('この機能を利用する権限がありません。')
        return redirect(url_for('teacher.dashboard'))
    
    if request.method == 'POST':
        try:
            # フォームから設定を取得
            settings = {
                'auto_sync_enabled': 'auto_sync_enabled' in request.form,
                'sync_on_curriculum_update': 'sync_on_curriculum_update' in request.form,
                'sync_on_item_change': 'sync_on_item_change' in request.form,
                'conflict_resolution_strategy': request.form.get('conflict_resolution_strategy', 'prompt'),
                'sync_delay_minutes': int(request.form.get('sync_delay_minutes', 5)),
                'batch_sync_window': int(request.form.get('batch_sync_window', 30))
            }
            
            # 設定更新
            result = AutoSyncService.update_sync_settings(curriculum_id, settings, current_user.id)
            
            if result['success']:
                flash('自動同期設定が更新されました。', 'success')
            else:
                flash(f'設定の更新に失敗しました: {result["message"]}', 'error')
                
        except ValueError as e:
            flash(f'入力値に誤りがあります: {str(e)}', 'error')
        except Exception as e:
            flash(f'設定の更新中にエラーが発生しました: {str(e)}', 'error')
            current_app.logger.error(f"Auto sync settings update error: {str(e)}", exc_info=True)
    
    # 現在の設定を取得
    current_settings = AutoSyncService.get_sync_settings(curriculum_id)
    
    # 同期履歴を取得
    sync_history = AutoSyncService.get_sync_history(curriculum_id, limit=10)
    
    # 変更検知結果を取得
    change_detection = AutoSyncService.detect_curriculum_changes(curriculum_id)
    
    return render_template('teacher/auto_sync_settings.html',
                         curriculum=curriculum,
                         current_settings=current_settings,
                         sync_history=sync_history,
                         change_detection=change_detection)

@teacher_bp.route('/curriculum/<int:curriculum_id>/enable-auto-sync', methods=['POST'])
@login_required
@teacher_required
def enable_auto_sync(curriculum_id):
    """自動同期の有効化"""
    from app.services.auto_sync_service import AutoSyncService
    
    result = AutoSyncService.enable_auto_sync_for_curriculum(curriculum_id, current_user.id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': result['message'],
            'settings': result['settings']
        })
    else:
        return jsonify({
            'success': False,
            'message': result['message']
        }), 400

@teacher_bp.route('/curriculum/<int:curriculum_id>/sync-status')
@login_required
@teacher_required
def get_sync_status(curriculum_id):
    """同期状況の取得"""
    from app.services.auto_sync_service import AutoSyncService
    
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        # 現在の同期状況
        should_sync, sync_info = AutoSyncService.should_auto_sync(curriculum_id)
        
        # 変更検知
        change_detection = AutoSyncService.detect_curriculum_changes(curriculum_id)
        
        # 最新の同期ログ
        sync_history = AutoSyncService.get_sync_history(curriculum_id, limit=3)
        
        return jsonify({
            'should_sync': should_sync,
            'sync_info': sync_info,
            'change_detection': change_detection,
            'recent_syncs': sync_history,
            'settings': AutoSyncService.get_sync_settings(curriculum_id)
        })
        
    except Exception as e:
        current_app.logger.error(f"Sync status error: {str(e)}", exc_info=True)
        return jsonify({'error': '状況取得エラー'}), 500

@teacher_bp.route('/curriculum/<int:curriculum_id>/manual-sync', methods=['POST'])
@login_required
@teacher_required
def manual_sync(curriculum_id):
    """手動同期の実行"""
    from app.services.auto_sync_service import AutoSyncService, SyncTriggerType
    
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        return jsonify({'success': False, 'message': '権限がありません'}), 403
    
    try:
        # 強制同期オプション
        force_sync = request.json.get('force', False) if request.is_json else False
        
        if not force_sync:
            # 通常の同期条件をチェック
            should_sync, sync_info = AutoSyncService.should_auto_sync(curriculum_id)
            if not should_sync:
                return jsonify({
                    'success': False,
                    'message': f'同期の必要がありません: {sync_info.get("reason", "不明")}',
                    'sync_info': sync_info
                })
        
        # 手動同期を実行
        sync_result = AutoSyncService.execute_auto_sync(
            curriculum_id, SyncTriggerType.MANUAL
        )
        
        if sync_result['success']:
            return jsonify({
                'success': True,
                'message': '手動同期が完了しました',
                'sync_result': sync_result
            })
        else:
            return jsonify({
                'success': False,
                'message': sync_result.get('message', '同期に失敗しました'),
                'sync_result': sync_result
            })
            
    except Exception as e:
        current_app.logger.error(f"Manual sync error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': '手動同期中にエラーが発生しました'
        }), 500

@teacher_bp.route('/api/sync-notifications/<int:curriculum_id>')
@login_required 
@teacher_required
def sync_notifications(curriculum_id):
    """同期通知のSSE エンドポイント（将来実装）"""
    # Server-Sent Events (SSE) でリアルタイム通知を実装
    # 現在は基本的なレスポンスのみ
    
    def generate():
        # 将来的にはリアルタイム同期状況をストリーミング
        yield f"data: {json.dumps({'status': 'connected', 'curriculum_id': curriculum_id})}\n\n"
    
    return Response(generate(), mimetype='text/plain')

@teacher_bp.route('/system/scheduled-sync-admin')
@login_required
@teacher_required  
def scheduled_sync_admin():
    """スケジュール同期管理画面（管理者用）"""
    from app.services.scheduled_sync_service import ScheduledSyncService
    
    # 簡易権限チェック（実際には管理者権限をチェック）
    if current_user.role != 'teacher':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('teacher.dashboard'))
    
    try:
        # スケジュール同期の概要を取得
        sync_summary = ScheduledSyncService.get_scheduled_sync_summary()
        
        return render_template('teacher/scheduled_sync_admin.html',
                             sync_summary=sync_summary)
                             
    except Exception as e:
        current_app.logger.error(f"Scheduled sync admin error: {str(e)}", exc_info=True)
        flash('スケジュール同期管理画面の読み込みに失敗しました。')
        return redirect(url_for('teacher.dashboard'))

@teacher_bp.route('/api/scheduled-sync/test', methods=['POST'])
@login_required
@teacher_required
def test_scheduled_sync():
    """スケジュール同期のテスト実行"""
    from app.services.scheduled_sync_service import ScheduledSyncService
    
    try:
        result = ScheduledSyncService.test_scheduled_sync()
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Test scheduled sync error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'テスト実行中にエラーが発生しました'
        }), 500

@teacher_bp.route('/api/scheduled-sync/run', methods=['POST'])
@login_required
@teacher_required
def run_scheduled_sync():
    """スケジュール同期の手動実行"""
    from app.services.scheduled_sync_service import ScheduledSyncService
    
    try:
        result = ScheduledSyncService.run_scheduled_sync_check()
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Run scheduled sync error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': '手動実行中にエラーが発生しました'
        }), 500

@teacher_bp.route('/curriculum/<int:curriculum_id>/units')
@login_required
@teacher_required
def view_converted_units(curriculum_id):
    """変換済み単元の一覧表示"""
    from app.services.curriculum_bridge_service import CurriculumBridgeService
    
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash('このカリキュラムを表示する権限がありません。')
        return redirect(url_for('teacher.view_curriculums', class_id=curriculum.class_id))
    
    # 変換済み単元を取得
    units = CurriculumUnit.query.filter_by(
        legacy_curriculum_id=curriculum_id,
        is_active=True
    ).order_by(CurriculumUnit.order_index).all()
    
    # 変換状況を取得
    conversion_status = CurriculumBridgeService.get_conversion_status(curriculum_id)
    
    return render_template('curriculum_units_view.html',
                         curriculum=curriculum,
                         units=units,
                         conversion_status=conversion_status)

@teacher_bp.route('/api/curriculum/problems')
@login_required
def get_curriculum_problems():
    """カテゴリに関連する問題を取得"""
    from app.services.curriculum_service_v2 import CurriculumServiceV2
    
    category = request.args.get('category', '')
    item_id = request.args.get('item_id', type=int)
    
    if not category:
        return jsonify({'problems': [], 'review_problems': []})
    
    # 関連問題を取得
    problems = CurriculumServiceV2.get_related_problems(category, current_user.id)
    
    # 復習推奨問題も取得
    review_problems = []
    if item_id and current_user.role == 'student':
        review_problems = CurriculumServiceV2.generate_review_problems(item_id, current_user.id)
    
    return jsonify({
        'problems': problems,
        'review_problems': review_problems
    })

# ==== リアルタイム同期関連のAPIエンドポイント ====

@teacher_bp.route('/curriculum/<int:curriculum_id>/sync', methods=['POST'])
@login_required
@teacher_required
def manual_sync_curriculum(curriculum_id):
    """カリキュラムの手動同期実行"""
    from app.tasks.sync_tasks import SyncTaskManager
    
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        return jsonify({'success': False, 'message': '権限がありません'}), 403
    
    try:
        data = request.get_json() or {}
        trigger_type = data.get('trigger_type', 'manual')
        
        # バックグラウンド同期の開始
        task_result = SyncTaskManager.start_background_sync(
            curriculum_id, trigger_type, current_user.id
        )
        
        return jsonify({
            'success': True,
            'message': '同期を開始しました',
            'task_info': task_result
        })
        
    except Exception as e:
        current_app.logger.error(f"Manual sync error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'同期開始エラー: {str(e)}'
        }), 500

@teacher_bp.route('/curriculum/<int:curriculum_id>/sync-stats')
@login_required
@teacher_required
def get_curriculum_sync_stats(curriculum_id):
    """カリキュラムの同期統計を取得"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        return jsonify({'success': False, 'message': '権限がありません'}), 403
    
    try:
        # 関連単元数
        units_count = CurriculumUnit.query.filter_by(
            legacy_curriculum_id=curriculum_id,
            is_active=True
        ).count()
        
        # 最終同期時間
        last_sync_time = None
        if curriculum.units_conversion_date:
            last_sync_time = curriculum.units_conversion_date.isoformat()
        
        # 競合数（実装例）
        conflicts_count = 0  # 将来的には実際の競合データから取得
        
        stats = {
            'units_count': units_count,
            'last_sync_time': last_sync_time,
            'conflicts_count': conflicts_count,
            'is_converted': curriculum.is_converted_to_units or False
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Sync stats error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': '統計取得エラー'
        }), 500

@teacher_bp.route('/realtime-stats')
@login_required
@teacher_required
def get_realtime_stats():
    """リアルタイム接続統計を取得"""
    try:
        from app.realtime import RealtimeSyncNotifier
        
        # 接続ユーザー情報を取得
        users_info = RealtimeSyncNotifier.get_connected_users_info()
        
        stats = {
            'connected_users': users_info.get('total_connected', 0),
            'users_detail': users_info.get('users', {})
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Realtime stats error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'リアルタイム統計取得エラー'
        }), 500

@teacher_bp.route('/sync-overview-stats')
@login_required
@teacher_required
def get_sync_overview_stats():
    """同期オーバービュー統計を取得"""
    try:
        from app.services.auto_sync_service import AutoSyncService
        from datetime import datetime, timedelta
        
        # 今日の同期完了数
        today = datetime.utcnow().date()
        completed_today = 0  # 実装例：実際はログから取得
        
        # アクティブ同期数（実装例）
        active_syncs = 0
        
        # 待機中同期数（実装例）
        pending_syncs = 0
        
        # 競合数（実装例）
        conflicts = 0
        
        # 最近のアクティビティ（実装例）
        recent_activities = [
            {
                'type': 'sync_completed',
                'message': 'サンプル同期完了',
                'timestamp': datetime.utcnow().isoformat(),
                'success': True
            }
        ]
        
        stats = {
            'active_syncs': active_syncs,
            'pending_syncs': pending_syncs,
            'completed_today': completed_today,
            'conflicts': conflicts,
            'recent_activities': recent_activities
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Sync overview stats error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': '同期概要統計取得エラー'
        }), 500

@teacher_bp.route('/curriculum/<int:curriculum_id>/sync-task-status/<task_id>')
@login_required
@teacher_required
def get_sync_task_status(curriculum_id, task_id):
    """同期タスクのステータスを取得"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        return jsonify({'success': False, 'message': '権限がありません'}), 403
    
    try:
        from app.tasks.sync_tasks import SyncTaskManager
        
        task_status = SyncTaskManager.get_task_status(task_id)
        
        return jsonify({
            'success': True,
            'task_status': task_status
        })
        
    except Exception as e:
        current_app.logger.error(f"Task status error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'タスクステータス取得エラー'
        }), 500