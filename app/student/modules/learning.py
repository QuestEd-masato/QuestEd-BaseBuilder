# app/student/modules/learning.py
"""学生自由進度学習機能"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func, desc

from app.models import db, CurriculumUnit, StudentUnitSelection, User
from ..utils import student_required

learning_bp = Blueprint('student_learning', __name__)

@learning_bp.route('/learning')
@login_required
@student_required
def learning_portal():
    """自由進度学習ポータル"""
    try:
        # 利用可能な単元を取得
        available_units = CurriculumUnit.query.filter_by(is_active=True).order_by(
            CurriculumUnit.subject, CurriculumUnit.order
        ).all()
        
        # 学生の単元選択状況を取得
        my_selections = StudentUnitSelection.query.filter_by(
            student_id=current_user.id
        ).all()
        
        # 選択済み単元IDのセット
        selected_unit_ids = {selection.unit_id for selection in my_selections}
        
        # 科目別に単元を整理
        units_by_subject = {}
        for unit in available_units:
            subject = unit.subject or '未分類'
            if subject not in units_by_subject:
                units_by_subject[subject] = []
            
            # 選択状況を追加
            unit_data = {
                'unit': unit,
                'is_selected': unit.id in selected_unit_ids,
                'selection': next((s for s in my_selections if s.unit_id == unit.id), None)
            }
            units_by_subject[subject].append(unit_data)
        
        # 学習統計
        stats = {
            'total_available': len(available_units),
            'selected_count': len(my_selections),
            'completed_count': len([s for s in my_selections if s.completion_rate >= 100]),
            'in_progress_count': len([s for s in my_selections if 0 < s.completion_rate < 100])
        }
        
        return render_template('learning_portal.html',
                             units_by_subject=units_by_subject,
                             stats=stats,
                             my_selections=my_selections)
        
    except Exception as e:
        current_app.logger.error(f"Learning portal error: {str(e)}")
        flash('学習ポータルの読み込み中にエラーが発生しました。', 'error')
        return redirect(url_for('student_dashboard.dashboard'))

@learning_bp.route('/select_unit/<int:unit_id>', methods=['POST'])
@login_required
@student_required
def select_unit(unit_id):
    """単元を選択"""
    try:
        unit = CurriculumUnit.query.get_or_404(unit_id)
        
        # 既に選択済みかチェック
        existing = StudentUnitSelection.query.filter_by(
            student_id=current_user.id,
            unit_id=unit_id
        ).first()
        
        if existing:
            flash('この単元は既に選択済みです。', 'info')
            return redirect(url_for('student_learning.learning_portal'))
        
        # 新しい選択を作成
        selection = StudentUnitSelection(
            student_id=current_user.id,
            unit_id=unit_id,
            selected_at=datetime.utcnow(),
            completion_rate=0,
            approval_status='pending'
        )
        
        db.session.add(selection)
        db.session.commit()
        
        flash(f'単元「{unit.title}」を選択しました。', 'success')
        return redirect(url_for('student_learning.learning_portal'))
        
    except Exception as e:
        current_app.logger.error(f"Select unit error: {str(e)}")
        db.session.rollback()
        flash('単元選択中にエラーが発生しました。', 'error')
        return redirect(url_for('student_learning.learning_portal'))

@learning_bp.route('/unit/<int:unit_id>')
@login_required
@student_required
def unit_detail(unit_id):
    """単元詳細と学習"""
    try:
        unit = CurriculumUnit.query.get_or_404(unit_id)
        
        # 選択状況を確認
        selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id,
            unit_id=unit_id
        ).first()
        
        if not selection:
            flash('この単元を学習するには、まず選択してください。', 'warning')
            return redirect(url_for('student_learning.learning_portal'))
        
        return render_template('student/unit_detail.html',
                             unit=unit,
                             selection=selection)
        
    except Exception as e:
        current_app.logger.error(f"Unit detail error: {str(e)}")
        flash('単元詳細の読み込み中にエラーが発生しました。', 'error')
        return redirect(url_for('student_learning.learning_portal'))

@learning_bp.route('/update_progress/<int:unit_id>', methods=['POST'])
@login_required
@student_required
def update_progress(unit_id):
    """学習進捗の更新"""
    try:
        selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id,
            unit_id=unit_id
        ).first_or_404()
        
        progress = request.form.get('progress', type=int)
        notes = request.form.get('notes', '').strip()
        
        if progress is None or progress < 0 or progress > 100:
            return jsonify({'success': False, 'message': '進捗は0-100の範囲で入力してください。'})
        
        # 進捗を更新
        selection.completion_rate = progress
        selection.notes = notes
        selection.updated_at = datetime.utcnow()
        
        # 100%完了時の処理
        if progress == 100 and selection.completion_rate < 100:
            selection.completed_at = datetime.utcnow()
            selection.approval_status = 'pending'  # 承認待ちに変更
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'進捗を{progress}%に更新しました。'
        })
        
    except Exception as e:
        current_app.logger.error(f"Update progress error: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'エラーが発生しました。'})

@learning_bp.route('/my_units')
@login_required
@student_required
def my_units():
    """自分の選択済み単元一覧"""
    try:
        selections = StudentUnitSelection.query.filter_by(
            student_id=current_user.id
        ).join(CurriculumUnit).order_by(
            StudentUnitSelection.selected_at.desc()
        ).all()
        
        return render_template('student/my_units.html',
                             selections=selections)
        
    except Exception as e:
        current_app.logger.error(f"My units error: {str(e)}")
        flash('選択済み単元の読み込み中にエラーが発生しました。', 'error')
        return redirect(url_for('student_dashboard.dashboard'))