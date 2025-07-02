"""
BaseBuilder Progress Routes
===========================
学習進捗・習熟度管理に関するルートハンドラ

移行元: basebuilder/routes.py の以下のルート:
- /proficiency (GET)
- /history (GET)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from extensions import db
from basebuilder.models import (
    ProblemCategory, BasicKnowledgeItem, AnswerRecord, 
    ProficiencyRecord
)

progress_bp = Blueprint('progress', __name__, url_prefix='/basebuilder')


@progress_bp.route('/proficiency')
@login_required
def view_proficiency():
    """学生の習熟度表示"""
    try:
        if current_user.role != 'student':
            flash('この機能は学生のみ利用可能です。')
            return redirect(url_for('basebuilder.index'))
        
        current_app.logger.info(f"Proficiency view accessed by user {current_user.id}")
        
        # 学生の熟練度記録を取得
        proficiency_records = ProficiencyRecord.query.filter_by(
            student_id=current_user.id
        ).all()
        
        # カテゴリ別の熟練度を整理
        category_proficiency = {}
        for record in proficiency_records:
            category_proficiency[record.category.id] = {
                'category': record.category,
                'level': record.level,
                'updated_at': record.updated_at
            }
        
        # すべてのカテゴリを取得
        all_categories = ProblemCategory.query.all()
        
        # カテゴリごとの問題数を取得
        category_counts = {}
        for category in all_categories:
            count = BasicKnowledgeItem.query.filter_by(
                category_id=category.id,
                is_active=True
            ).count()
            category_counts[category.id] = count
        
        return render_template(
            'basebuilder/proficiency.html',
            proficiency_records=proficiency_records,
            category_proficiency=category_proficiency,
            all_categories=all_categories,
            category_counts=category_counts
        )
        
    except Exception as e:
        current_app.logger.error(f"Proficiency view error: {str(e)}")
        flash('習熟度データの取得中にエラーが発生しました。')
        return redirect(url_for('basebuilder.index'))


@progress_bp.route('/history')
@login_required
def view_history():
    """学習履歴表示"""
    try:
        if current_user.role != 'student':
            flash('この機能は学生のみ利用可能です。')
            return redirect(url_for('basebuilder.index'))
        
        current_app.logger.info(f"History view accessed by user {current_user.id}")
        
        # 学生の解答履歴を取得
        answer_records = AnswerRecord.query.filter_by(
            student_id=current_user.id
        ).order_by(AnswerRecord.created_at.desc()).all()
        
        # カテゴリ別の正解率を計算
        category_stats = {}
        for record in answer_records:
            category_id = record.problem.category_id
            
            if category_id not in category_stats:
                category_stats[category_id] = {
                    'category': record.problem.category,
                    'total': 0,
                    'correct': 0,
                    'incorrect': 0
                }
            
            category_stats[category_id]['total'] += 1
            if record.is_correct:
                category_stats[category_id]['correct'] += 1
            else:
                category_stats[category_id]['incorrect'] += 1
        
        # 正解率を計算
        for stats in category_stats.values():
            stats['accuracy'] = (stats['correct'] / stats['total']) * 100 if stats['total'] > 0 else 0
        
        return render_template(
            'basebuilder/history.html',
            answer_records=answer_records,
            category_stats=category_stats
        )
        
    except Exception as e:
        current_app.logger.error(f"History view error: {str(e)}")
        flash('学習履歴の取得中にエラーが発生しました。')
        return redirect(url_for('basebuilder.index'))