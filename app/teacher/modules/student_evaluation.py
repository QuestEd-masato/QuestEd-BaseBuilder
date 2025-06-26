# app/teacher/modules/student_evaluation.py
"""学生評価機能"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
import logging

from app.models import (
    db, User, Class, ClassEnrollment, InquiryTheme, 
    StudentEvaluation, RubricTemplate, ActivityLog, Goal, Todo
)
from app.ai import generate_student_evaluation
from ..common import teacher_required

# Conditional imports
try:
    from app.ai.helpers import generate_activity_summary
except ImportError:
    def generate_activity_summary(*args, **kwargs):
        return "活動概要の生成に失敗しました。"

try:
    from ..pdf_generator import generate_student_report_pdf
except ImportError:
    def generate_student_report_pdf(*args, **kwargs):
        return None

student_evaluation_bp = Blueprint('teacher_student_evaluation', __name__)

@student_evaluation_bp.route('/class/<int:class_id>/evaluate', methods=['GET', 'POST'])
@login_required
@teacher_required
def generate_evaluations(class_id):
    """AI評価生成"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスの評価を生成する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    # クラスの生徒を取得
    enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
    students = [enrollment.student for enrollment in enrollments]
    
    # カリキュラム情報を取得（評価の参考用）
    from app.models import Curriculum
    curriculum = Curriculum.query.filter_by(
        class_id=class_id, 
        teacher_id=current_user.id
    ).first()
    
    # ルーブリックテンプレートを取得
    rubric = RubricTemplate.query.filter_by(
        school_id=current_user.school_id,
        is_active=True
    ).first()
    
    if request.method == 'POST':
        selected_student_ids = request.form.getlist('student_ids')
        evaluation_criteria = request.form.get('criteria', '')
        evaluation_period = request.form.get('period', '')
        
        if not selected_student_ids:
            flash('評価する生徒を選択してください。')
            return render_template('evaluate_students.html', 
                                 class_obj=class_obj, 
                                 students=students,
                                 curriculum=curriculum,
                                 rubric=rubric)
        
        evaluations = []
        
        for student_id in selected_student_ids:
            student = User.query.get(student_id)
            if not student:
                continue
            
            try:
                # 学生の活動データを収集
                activities = ActivityLog.query.filter_by(
                    student_id=student.id
                ).order_by(ActivityLog.created_at.desc()).limit(20).all()
                
                goals = Goal.query.filter_by(
                    student_id=student.id
                ).all()
                
                todos = Todo.query.filter_by(
                    student_id=student.id
                ).all()
                
                selected_theme = InquiryTheme.query.filter_by(
                    student_id=student.id,
                    is_selected=True
                ).first()
                
                # AI評価を生成
                evaluation_data = {
                    'student_name': student.full_name or student.username,
                    'class_name': class_obj.name,
                    'curriculum': curriculum.content if curriculum else '指定なし',
                    'activities': [activity.content for activity in activities],
                    'goals': [goal.title for goal in goals],
                    'todos': [todo.content for todo in todos],
                    'selected_theme': selected_theme.title if selected_theme else 'なし',
                    'criteria': evaluation_criteria,
                    'period': evaluation_period
                }
                
                evaluation_text = generate_student_evaluation(evaluation_data)
                
                # 評価を保存
                evaluation = StudentEvaluation(
                    student_id=student.id,
                    teacher_id=current_user.id,
                    class_id=class_id,
                    evaluation=evaluation_text,
                    period=evaluation_period,
                    criteria=evaluation_criteria
                )
                db.session.add(evaluation)
                
                evaluations.append({
                    'student': student,
                    'evaluation': evaluation_text
                })
                
            except Exception as e:
                logging.error(f"Evaluation generation error for student {student.id}: {str(e)}")
                evaluations.append({
                    'student': student,
                    'evaluation': f'評価生成中にエラーが発生しました: {str(e)}'
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

@student_evaluation_bp.route('/class/<int:class_id>/student/<int:student_id>/report')
@login_required
@teacher_required
def generate_student_report(class_id, student_id):
    """学生の詳細レポート生成"""
    class_obj = Class.query.get_or_404(class_id)
    student = User.query.get_or_404(student_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このレポートを生成する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    # 学生がクラスに所属しているかチェック
    enrollment = ClassEnrollment.query.filter_by(
        class_id=class_id,
        student_id=student_id
    ).first()
    
    if not enrollment:
        flash('指定された学生はこのクラスに所属していません。')
        return redirect(url_for('teacher_class_management.class_details', class_id=class_id))
    
    try:
        # 学生の詳細データを収集
        activities = ActivityLog.query.filter_by(
            student_id=student.id
        ).order_by(ActivityLog.created_at.desc()).all()
        
        goals = Goal.query.filter_by(
            student_id=student.id
        ).all()
        
        todos = Todo.query.filter_by(
            student_id=student.id
        ).all()
        
        selected_theme = InquiryTheme.query.filter_by(
            student_id=student.id,
            is_selected=True
        ).first()
        
        evaluations = StudentEvaluation.query.filter_by(
            student_id=student.id,
            teacher_id=current_user.id
        ).order_by(StudentEvaluation.created_at.desc()).all()
        
        # 活動概要をAIで生成
        activity_summary = generate_activity_summary(
            activities[:10],  # 最新10件の活動
            student.full_name or student.username
        )
        
        report_data = {
            'student': student,
            'class_obj': class_obj,
            'activities': activities,
            'goals': goals,
            'todos': todos,
            'selected_theme': selected_theme,
            'evaluations': evaluations,
            'activity_summary': activity_summary,
            'enrollment': enrollment
        }
        
        # PDFレポートを生成（オプション）
        pdf_data = generate_student_report_pdf(report_data)
        
        return render_template('student_report.html', 
                             report_data=report_data,
                             pdf_available=pdf_data is not None)
        
    except Exception as e:
        logging.error(f"Student report generation error: {str(e)}")
        flash('レポート生成中にエラーが発生しました。')
        return redirect(url_for('teacher_class_management.class_details', class_id=class_id))

@student_evaluation_bp.route('/teacher/themes')
@login_required
@teacher_required
def teacher_themes():
    """教師のテーマ管理"""
    # 教師が担当するクラスの全テーマを取得
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    
    themes_by_class = {}
    for class_obj in classes:
        # メインテーマ
        main_themes = MainTheme.query.filter_by(class_id=class_obj.id).all()
        
        # 学生の探究テーマ
        enrollments = ClassEnrollment.query.filter_by(class_id=class_obj.id).all()
        inquiry_themes = []
        
        for enrollment in enrollments:
            student_themes = InquiryTheme.query.filter_by(
                student_id=enrollment.student_id
            ).all()
            inquiry_themes.extend(student_themes)
        
        themes_by_class[class_obj] = {
            'main_themes': main_themes,
            'inquiry_themes': inquiry_themes
        }
    
    return render_template('teacher_themes.html', 
                         themes_by_class=themes_by_class)

@student_evaluation_bp.route('/api/student/<int:student_id>/evaluation_history')
@login_required
@teacher_required
def student_evaluation_history(student_id):
    """学生の評価履歴API"""
    student = User.query.get_or_404(student_id)
    
    # 権限チェック: 教師が担当するクラスの学生かどうか
    enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
    authorized = False
    
    for enrollment in enrollments:
        if enrollment.class_obj.teacher_id == current_user.id:
            authorized = True
            break
    
    if not authorized:
        return jsonify({'error': '権限がありません'}), 403
    
    # 評価履歴を取得
    evaluations = StudentEvaluation.query.filter_by(
        student_id=student_id,
        teacher_id=current_user.id
    ).order_by(StudentEvaluation.created_at.desc()).all()
    
    evaluation_data = []
    for evaluation in evaluations:
        evaluation_data.append({
            'id': evaluation.id,
            'evaluation': evaluation.evaluation,
            'period': evaluation.period,
            'criteria': evaluation.criteria,
            'created_at': evaluation.created_at.isoformat(),
            'class_name': evaluation.class_obj.name if evaluation.class_obj else '不明'
        })
    
    return jsonify({
        'student_name': student.full_name or student.username,
        'evaluations': evaluation_data
    })

@student_evaluation_bp.route('/evaluation/<int:evaluation_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_evaluation(evaluation_id):
    """評価編集"""
    evaluation = StudentEvaluation.query.get_or_404(evaluation_id)
    
    # 権限チェック
    if evaluation.teacher_id != current_user.id:
        flash('この評価を編集する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    if request.method == 'POST':
        try:
            evaluation.evaluation = request.form.get('evaluation', evaluation.evaluation)
            evaluation.criteria = request.form.get('criteria', evaluation.criteria)
            evaluation.period = request.form.get('period', evaluation.period)
            evaluation.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('評価が更新されました。', 'success')
            
            return redirect(url_for('teacher_class_management.class_details', 
                                  class_id=evaluation.class_id))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Evaluation update error: {str(e)}")
            flash('評価の更新に失敗しました。', 'error')
    
    return render_template('edit_evaluation.html', evaluation=evaluation)

@student_evaluation_bp.route('/evaluation/<int:evaluation_id>/delete')
@login_required
@teacher_required
def delete_evaluation(evaluation_id):
    """評価削除"""
    evaluation = StudentEvaluation.query.get_or_404(evaluation_id)
    
    # 権限チェック
    if evaluation.teacher_id != current_user.id:
        flash('この評価を削除する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    class_id = evaluation.class_id
    
    try:
        db.session.delete(evaluation)
        db.session.commit()
        flash('評価が削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Evaluation deletion error: {str(e)}")
        flash('評価の削除に失敗しました。', 'error')
    
    return redirect(url_for('teacher_class_management.class_details', class_id=class_id))