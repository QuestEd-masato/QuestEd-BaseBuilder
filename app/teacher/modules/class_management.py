# app/teacher/modules/class_management.py
"""クラス管理機能"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from datetime import datetime
import csv
import io
import logging

from app.models import (
    db, User, Class, ClassEnrollment, MainTheme, InquiryTheme, 
    Milestone, Group, GroupMembership, Subject, ActivityLog
)
from app.utils.model_helpers import mysql_nulls_last
from ..common import teacher_required

# CSV helper functions
def export_to_csv_utf8_bom(data, filename):
    """CSV export with UTF-8 BOM"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    if data:
        writer.writerow(data[0].keys())
        
    # Write data
    for row in data:
        writer.writerow(row.values())
    
    # Convert to bytes with BOM
    csv_data = '\ufeff' + output.getvalue()
    response = Response(
        csv_data.encode('utf-8'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
    return response

class_management_bp = Blueprint('teacher_class_management', __name__)

@class_management_bp.route('/classes')
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

@class_management_bp.route('/create_class', methods=['GET', 'POST'])
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
            return redirect(url_for('teacher_class_management.class_details', class_id=new_class.id))
        except Exception as e:
            db.session.rollback()
            flash('クラス作成中にエラーが発生しました。')
            logging.error(f"Class creation error: {str(e)}")
    
    # GETリクエスト時は教科リストを渡す
    subjects = Subject.query.filter_by(is_active=True).all()
    return render_template('create_class.html', subjects=subjects)

@class_management_bp.route('/class/<int:class_id>')
@login_required
def class_details(class_id):
    """クラス詳細"""
    class_obj = Class.query.get_or_404(class_id)
    
    # アクセス権限の確認
    if current_user.role == 'teacher' and class_obj.teacher_id != current_user.id:
        flash('このクラスへのアクセス権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    elif current_user.role == 'student':
        enrollment = ClassEnrollment.query.filter_by(
            class_id=class_id,
            student_id=current_user.id
        ).first()
        if not enrollment:
            flash('このクラスへのアクセス権限がありません。')
            return redirect(url_for('teacher_class_management.classes'))
    
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
        ).order_by(ActivityLog.created_at.desc()).first()
        
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

@class_management_bp.route('/view_class/<int:class_id>')
@login_required
def view_class(class_id):
    """クラス詳細表示（リダイレクト用）"""
    return redirect(url_for('teacher_class_management.class_details', class_id=class_id))

@class_management_bp.route('/class/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_class(class_id):
    """クラス編集"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスを編集する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
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
        return redirect(url_for('teacher_class_management.class_details', class_id=class_id))
    
    return render_template('edit_class.html', class_obj=class_obj, subjects=subjects)

@class_management_bp.route('/class/<int:class_id>/delete')
@login_required
@teacher_required
def delete_class(class_id):
    """クラス削除"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスを削除する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    # 関連データも含めて削除
    db.session.delete(class_obj)
    db.session.commit()
    
    flash('クラスが削除されました。')
    return redirect(url_for('teacher_class_management.classes'))

@class_management_bp.route('/class/<int:class_id>/add_students', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_students(class_id):
    """クラスに生徒を追加"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスに生徒を追加する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')
        
        for student_id in student_ids:
            # 既に登録されているかチェック
            existing_enrollment = ClassEnrollment.query.filter_by(
                class_id=class_id,
                student_id=student_id
            ).first()
            
            if not existing_enrollment:
                enrollment = ClassEnrollment(
                    class_id=class_id,
                    student_id=student_id
                )
                db.session.add(enrollment)
        
        db.session.commit()
        flash('生徒が追加されました。')
        return redirect(url_for('teacher_class_management.class_details', class_id=class_id))
    
    # まだクラスに追加されていない生徒を取得
    enrolled_student_ids = [e.student_id for e in ClassEnrollment.query.filter_by(class_id=class_id).all()]
    available_students = User.query.filter(
        User.role == 'student',
        User.school_id == current_user.school_id,
        User.is_approved == True,
        ~User.id.in_(enrolled_student_ids)
    ).all()
    
    return render_template('add_students.html', 
                         class_obj=class_obj, 
                         available_students=available_students)

@class_management_bp.route('/class/<int:class_id>/remove_student/<int:student_id>')
@login_required
@teacher_required
def remove_student(class_id, student_id):
    """クラスから生徒を除外"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスから生徒を除外する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    enrollment = ClassEnrollment.query.filter_by(
        class_id=class_id,
        student_id=student_id
    ).first()
    
    if enrollment:
        db.session.delete(enrollment)
        db.session.commit()
        flash('生徒をクラスから除外しました。')
    else:
        flash('指定された生徒はこのクラスに登録されていません。')
    
    return redirect(url_for('teacher_class_management.class_details', class_id=class_id))

@class_management_bp.route('/download_student_template')
@login_required
@teacher_required
def download_student_template():
    """生徒インポート用CSVテンプレートダウンロード"""
    template_data = [
        {
            'username': '例: student001',
            'full_name': '例: 山田太郎',
            'email': '例: student001@example.com'
        }
    ]
    
    return export_to_csv_utf8_bom(template_data, 'students_template.csv')

@class_management_bp.route('/class/<int:class_id>/import_students', methods=['GET', 'POST'])
@login_required
@teacher_required
def import_students(class_id):
    """CSVから生徒をインポート"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスに生徒をインポートする権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    if request.method == 'POST':
        csv_file = request.files.get('csv_file')
        
        if not csv_file or csv_file.filename == '':
            flash('CSVファイルを選択してください。')
            return render_template('import_students.html', class_obj=class_obj)
        
        try:
            # CSVファイルを処理
            result = process_student_csv(csv_file, class_id)
            
            if result['success']:
                flash(f'{result["imported_count"]}人の生徒を追加しました。')
                if result['errors']:
                    flash(f'エラー: {len(result["errors"])}件')
                return redirect(url_for('teacher_class_management.class_details', class_id=class_id))
            else:
                flash('CSVファイルの処理中にエラーが発生しました。')
                for error in result['errors']:
                    flash(error)
        
        except Exception as e:
            flash('CSVファイルの読み込み中にエラーが発生しました。')
            logging.error(f"CSV import error: {str(e)}")
    
    return render_template('import_students.html', class_obj=class_obj)

def process_student_csv(csv_file, class_id):
    """CSV処理ヘルパー関数"""
    result = {
        'success': False,
        'imported_count': 0,
        'errors': []
    }
    
    try:
        # CSVファイルを読み込み
        stream = io.StringIO(csv_file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        for row_num, row in enumerate(csv_input, start=2):
            try:
                username = row.get('username', '').strip()
                full_name = row.get('full_name', '').strip()
                email = row.get('email', '').strip()
                
                if not username or not email:
                    result['errors'].append(f'行 {row_num}: ユーザー名とメールアドレスは必須です')
                    continue
                
                # 既存ユーザーチェック
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    # 既存ユーザーをクラスに追加
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
                        result['imported_count'] += 1
                else:
                    result['errors'].append(f'行 {row_num}: ユーザー {username} が見つかりません')
                    
            except Exception as e:
                result['errors'].append(f'行 {row_num}: {str(e)}')
        
        db.session.commit()
        result['success'] = True
        
    except Exception as e:
        db.session.rollback()
        result['errors'].append(f'CSV処理エラー: {str(e)}')
    
    return result