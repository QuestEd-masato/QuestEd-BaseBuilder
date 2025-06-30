# app/student/modules/activities.py
"""学生活動記録機能"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import io
import csv
import uuid
import imghdr
import logging

from app.models import (
    db, ActivityLog, InquiryTheme, Class, ClassEnrollment
)
from ..utils import (
    student_required, allowed_file, validate_image, secure_filename_with_uuid,
    get_upload_path, validate_file_size, check_class_access, format_activity_content
)

# 条件付きインポート（ReportLab）
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

activities_bp = Blueprint('student_activities', __name__)

@activities_bp.route('/activities')
@login_required
@student_required
def activities():
    """活動記録一覧とクラス選択"""
    try:
        # 学生が履修しているクラスを取得
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]
        
        if not classes:
            flash('履修しているクラスがありません。')
            return redirect(url_for('student_dashboard.dashboard'))
        
        # URLパラメータからクラスIDを取得
        selected_class_id = request.args.get('class_id', type=int)
        selected_class = None
        
        if selected_class_id:
            # 指定されたクラスが履修クラスに含まれているかチェック
            selected_class = next((c for c in classes if c.id == selected_class_id), None)
            if not selected_class:
                flash('指定されたクラスにアクセス権限がありません。')
                return redirect(url_for('student_activities.activities'))
        
        # 活動記録を取得
        activities_query = ActivityLog.query.filter_by(student_id=current_user.id)
        
        if selected_class:
            # 特定のクラスの活動記録のみ表示
            activities_query = activities_query.filter_by(class_id=selected_class.id)
        
        activities = activities_query.order_by(ActivityLog.created_at.desc()).all()
        
        # 選択中のテーマを取得
        selected_theme = InquiryTheme.query.filter_by(
            student_id=current_user.id,
            is_selected=True
        ).first()
        
        return render_template('activities.html',
                             classes=classes,
                             selected_class=selected_class,
                             activities=activities,
                             selected_theme=selected_theme)
        
    except Exception as e:
        current_app.logger.error(f"Activities list error: {str(e)}")
        flash('活動記録の読み込み中にエラーが発生しました。')
        return redirect(url_for('student_dashboard.dashboard'))

@activities_bp.route('/new_activity', methods=['GET', 'POST'])
@login_required
@student_required
def new_activity():
    """新規活動記録作成"""
    try:
        # 学生が履修しているクラスを取得
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]
        
        if not classes:
            flash('履修しているクラスがありません。')
            return redirect(url_for('student_dashboard.dashboard'))
        
        # 選択中のテーマを取得
        selected_theme = InquiryTheme.query.filter_by(
            student_id=current_user.id,
            is_selected=True
        ).first()
        
        if request.method == 'POST':
            content = request.form.get('content', '').strip()
            class_id = request.form.get('class_id', type=int)
            
            # 入力値検証
            if not content:
                flash('活動内容を入力してください。', 'error')
                return render_template('new_activity.html',
                                     classes=classes,
                                     selected_theme=selected_theme)
            
            if not class_id or not check_class_access(class_id):
                flash('有効なクラスを選択してください。', 'error')
                return render_template('new_activity.html',
                                     classes=classes,
                                     selected_theme=selected_theme)
            
            # 新しい活動記録を作成
            new_activity = ActivityLog(
                student_id=current_user.id,
                class_id=class_id,
                content=content,
                theme_id=selected_theme.id if selected_theme else None
            )
            
            # 画像ファイルの処理
            image_file = request.files.get('image')
            if image_file and image_file.filename:
                if allowed_file(image_file.filename) and validate_file_size(image_file):
                    # 画像の妥当性をチェック
                    if validate_image(image_file.stream):
                        # セキュアなファイル名を生成
                        filename = secure_filename_with_uuid(image_file.filename)
                        if filename:
                            # ファイルを保存
                            upload_path = get_upload_path()
                            os.makedirs(upload_path, exist_ok=True)
                            
                            file_path = os.path.join(upload_path, filename)
                            image_file.save(file_path)
                            
                            new_activity.image_path = filename
                    else:
                        flash('無効な画像ファイルです。', 'warning')
                else:
                    flash('画像ファイルのサイズまたは形式が無効です。', 'warning')
            
            try:
                db.session.add(new_activity)
                db.session.commit()
                flash('活動記録を作成しました。', 'success')
                return redirect(url_for('student_activities.activities', class_id=class_id))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Activity creation error: {str(e)}")
                flash('活動記録の作成に失敗しました。', 'error')
        
        return render_template('new_activity.html',
                             classes=classes,
                             selected_theme=selected_theme)
        
    except Exception as e:
        current_app.logger.error(f"New activity error: {str(e)}")
        flash('活動記録作成画面の読み込み中にエラーが発生しました。')
        return redirect(url_for('student_activities.activities'))

@activities_bp.route('/edit_activity/<int:activity_id>', methods=['GET', 'POST'])
@login_required
@student_required
def edit_activity(activity_id):
    """活動記録編集"""
    try:
        activity = ActivityLog.query.get_or_404(activity_id)
        
        # 権限チェック
        if activity.student_id != current_user.id:
            flash('この活動記録を編集する権限がありません。')
            return redirect(url_for('student_activities.activities'))
        
        # 学生が履修しているクラスを取得
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]
        
        if request.method == 'POST':
            content = request.form.get('content', '').strip()
            class_id = request.form.get('class_id', type=int)
            
            # 入力値検証
            if not content:
                flash('活動内容を入力してください。', 'error')
                return render_template('edit_activity.html',
                                     activity=activity,
                                     classes=classes)
            
            if not class_id or not check_class_access(class_id):
                flash('有効なクラスを選択してください。', 'error')
                return render_template('edit_activity.html',
                                     activity=activity,
                                     classes=classes)
            
            # 活動記録を更新
            activity.content = content
            activity.class_id = class_id
            activity.updated_at = datetime.utcnow()
            
            try:
                db.session.commit()
                flash('活動記録を更新しました。', 'success')
                return redirect(url_for('student_activities.view_activity', activity_id=activity_id))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Activity update error: {str(e)}")
                flash('活動記録の更新に失敗しました。', 'error')
        
        return render_template('edit_activity.html',
                             activity=activity,
                             classes=classes)
        
    except Exception as e:
        current_app.logger.error(f"Edit activity error: {str(e)}")
        flash('活動記録編集画面の読み込み中にエラーが発生しました。')
        return redirect(url_for('student_activities.activities'))

@activities_bp.route('/delete_activity/<int:activity_id>')
@login_required
@student_required
def delete_activity(activity_id):
    """活動記録削除"""
    try:
        activity = ActivityLog.query.get_or_404(activity_id)
        
        # 権限チェック
        if activity.student_id != current_user.id:
            flash('この活動記録を削除する権限がありません。')
            return redirect(url_for('student_activities.activities'))
        
        class_id = activity.class_id
        
        # 関連ファイルも削除
        if activity.image_path:
            try:
                upload_path = get_upload_path()
                file_path = os.path.join(upload_path, activity.image_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                current_app.logger.warning(f"Failed to delete activity image: {str(e)}")
        
        try:
            db.session.delete(activity)
            db.session.commit()
            flash('活動記録を削除しました。', 'success')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Activity deletion error: {str(e)}")
            flash('活動記録の削除に失敗しました。', 'error')
        
        return redirect(url_for('student_activities.activities', class_id=class_id))
        
    except Exception as e:
        current_app.logger.error(f"Delete activity error: {str(e)}")
        flash('活動記録削除中にエラーが発生しました。')
        return redirect(url_for('student_activities.activities'))

@activities_bp.route('/view_activity/<int:activity_id>')
@login_required
@student_required
def view_activity(activity_id):
    """活動記録詳細表示"""
    try:
        activity = ActivityLog.query.get_or_404(activity_id)
        
        # 権限チェック
        if activity.student_id != current_user.id:
            flash('この活動記録を表示する権限がありません。')
            return redirect(url_for('student_activities.activities'))
        
        return render_template('view_activity.html', activity=activity)
        
    except Exception as e:
        current_app.logger.error(f"View activity error: {str(e)}")
        flash('活動記録詳細の読み込み中にエラーが発生しました。')
        return redirect(url_for('student_activities.activities'))

@activities_bp.route('/export_activities')
@login_required
@student_required
def export_activities():
    """活動記録エクスポート（PDF/CSV）"""
    try:
        export_format = request.args.get('format', 'csv').lower()
        class_id = request.args.get('class_id', type=int)
        
        # 活動記録を取得
        activities_query = ActivityLog.query.filter_by(student_id=current_user.id)
        
        if class_id and check_class_access(class_id):
            activities_query = activities_query.filter_by(class_id=class_id)
            class_obj = Class.query.get(class_id)
            filename_suffix = f"_{class_obj.name}" if class_obj else ""
        else:
            filename_suffix = "_全クラス"
        
        activities = activities_query.order_by(ActivityLog.created_at.desc()).all()
        
        if not activities:
            flash('エクスポートする活動記録がありません。')
            return redirect(url_for('student_activities.activities'))
        
        if export_format == 'pdf':
            return _export_activities_pdf(activities, filename_suffix)
        else:
            return _export_activities_csv(activities, filename_suffix)
        
    except Exception as e:
        current_app.logger.error(f"Export activities error: {str(e)}")
        flash('活動記録のエクスポート中にエラーが発生しました。')
        return redirect(url_for('student_activities.activities'))

def _export_activities_csv(activities, filename_suffix):
    """CSV形式で活動記録をエクスポート"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # ヘッダー行
    writer.writerow(['日付', 'クラス', 'テーマ', '活動内容', '画像'])
    
    # データ行
    for activity in activities:
        writer.writerow([
            activity.created_at.strftime('%Y-%m-%d %H:%M'),
            activity.class_obj.name if activity.class_obj else '不明',
            activity.theme.title if activity.theme else 'なし',
            format_activity_content(activity.content, 200),
            'あり' if activity.image_path else 'なし'
        ])
    
    # UTF-8 BOM付きでレスポンスを作成
    csv_data = '\ufeff' + output.getvalue()
    
    response = send_file(
        io.BytesIO(csv_data.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'活動記録{filename_suffix}_{datetime.now().strftime("%Y%m%d")}.csv'
    )
    
    return response

def _export_activities_pdf(activities, filename_suffix):
    """PDF形式で活動記録をエクスポート"""
    if not REPORTLAB_AVAILABLE:
        flash('PDF機能は利用できません。CSV形式をお試しください。')
        return redirect(url_for('student_activities.activities'))
    
    try:
        # PDFファイルを作成
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # スタイルを設定
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30
        )
        content_style = ParagraphStyle(
            'CustomContent',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=12
        )
        
        # タイトル
        story.append(Paragraph(f'{current_user.username}の活動記録{filename_suffix}', title_style))
        story.append(Spacer(1, 12))
        
        # 各活動記録
        for activity in activities:
            # 日付とクラス
            header = f"{activity.created_at.strftime('%Y年%m月%d日 %H:%M')} - {activity.class_obj.name if activity.class_obj else '不明'}"
            story.append(Paragraph(header, styles['Heading2']))
            
            # テーマ
            if activity.theme:
                story.append(Paragraph(f"テーマ: {activity.theme.title}", styles['Normal']))
            
            # 活動内容
            story.append(Paragraph(f"活動内容: {activity.content}", content_style))
            story.append(Spacer(1, 12))
        
        # PDFを生成
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'活動記録{filename_suffix}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"PDF export error: {str(e)}")
        flash('PDF生成中にエラーが発生しました。CSV形式をお試しください。')
        return redirect(url_for('student_activities.activities'))