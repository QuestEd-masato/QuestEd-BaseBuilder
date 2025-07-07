# app/student/modules/ranking.py
"""学生ランキング詳細機能"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import logging

from app.models import db, User, Class, ClassEnrollment
from basebuilder.models import WordProficiency, AnswerRecord
from ..utils import student_required

ranking_bp = Blueprint('student_ranking', __name__)

@ranking_bp.route('/ranking')
@login_required
@student_required
def ranking():
    """基礎学力マスターランキング詳細ページ"""
    try:
        # 学生が履修しているクラスを取得
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]
        
        # ClassEnrollmentが空の場合、User.class_idから取得を試行
        if not classes and current_user.class_id:
            direct_class = Class.query.get(current_user.class_id)
            if direct_class:
                classes = [direct_class]
        
        if not classes:
            flash('所属クラスが見つかりません。先生に連絡して、クラスに登録してもらってください。')
            return redirect(url_for('student_dashboard.dashboard'))
        
        class_ids = [cls.id for cls in classes]
        
        # 期間別ランキングを生成
        rankings = {
            'overall': _get_overall_ranking(class_ids),
            'this_month': _get_monthly_ranking(class_ids),
            'this_week': _get_weekly_ranking(class_ids)
        }
        
        # 自分の順位を計算
        my_position = _get_my_position(rankings['overall'], current_user.id)
        
        # Adapt data for existing template
        ranking_type = request.args.get('type', 'total_points')
        scope = request.args.get('scope', 'class')
        
        # Use overall ranking as primary ranking data
        primary_ranking = rankings['overall']
        
        # Calculate my rank data
        my_rank = None
        if my_position and primary_ranking:
            total_participants = len(primary_ranking)
            percentile = round((total_participants - my_position + 1) / total_participants * 100)
            my_score = primary_ranking[my_position - 1]['word_count'] if my_position <= len(primary_ranking) else 0
            
            my_rank = {
                'rank': my_position,
                'score': my_score,
                'total_participants': total_participants,
                'percentile': percentile
            }
        
        # Prepare ranking data structure for template
        ranking_data = {
            'rankings': primary_ranking,
            'type': ranking_type,
            'scope': scope
        }
        
        return render_template('student/ranking.html',
                             ranking_data=ranking_data,
                             ranking_type=ranking_type,
                             scope=scope,
                             my_rank=my_rank,
                             student_classes=classes)
        
    except Exception as e:
        current_app.logger.error(f"Ranking page error: {str(e)}")
        flash('ランキング情報の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('student_dashboard.dashboard'))

def _get_overall_ranking(class_ids):
    """全期間の総合ランキング"""
    # ClassEnrollmentから学生IDを取得
    student_ids = db.session.query(ClassEnrollment.student_id).filter(
        ClassEnrollment.class_id.in_(class_ids)
    ).distinct().all()
    
    if not student_ids:
        return []
    
    student_ids = [sid[0] for sid in student_ids]
    
    # 各学生の熟練度5達成単語数を計算
    ranking_data = db.session.query(
        WordProficiency.student_id,
        func.count(WordProficiency.id).label('mastered_count'),
        func.avg(WordProficiency.level).label('avg_level')
    ).filter(
        WordProficiency.student_id.in_(student_ids),
        WordProficiency.level == 5
    ).group_by(WordProficiency.student_id).all()
    
    # 学生情報と結合
    ranking = []
    for student_id, mastered_count, avg_level in ranking_data:
        user = User.query.get(student_id)
        if user:
            ranking.append({
                'student_id': student_id,
                'full_name': user.full_name or user.username,
                'username': user.username,
                'word_count': mastered_count,
                'avg_level': round(avg_level, 1) if avg_level else 0
            })
    
    # 習得単語数で降順ソート
    ranking.sort(key=lambda x: x['word_count'], reverse=True)
    
    return ranking

def _get_monthly_ranking(class_ids):
    """今月のランキング"""
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 今月に更新された熟練度5の記録
    student_ids = db.session.query(ClassEnrollment.student_id).filter(
        ClassEnrollment.class_id.in_(class_ids)
    ).distinct().all()
    
    if not student_ids:
        return []
    
    student_ids = [sid[0] for sid in student_ids]
    
    ranking_data = db.session.query(
        WordProficiency.student_id,
        func.count(WordProficiency.id).label('monthly_mastered')
    ).filter(
        WordProficiency.student_id.in_(student_ids),
        WordProficiency.level == 5,
        WordProficiency.updated_at >= month_start
    ).group_by(WordProficiency.student_id).all()
    
    ranking = []
    for student_id, monthly_mastered in ranking_data:
        user = User.query.get(student_id)
        if user:
            ranking.append({
                'student_id': student_id,
                'full_name': user.full_name or user.username,
                'username': user.username,
                'word_count': monthly_mastered
            })
    
    ranking.sort(key=lambda x: x['word_count'], reverse=True)
    return ranking

def _get_weekly_ranking(class_ids):
    """今週のランキング"""
    week_start = datetime.now() - timedelta(days=7)
    
    student_ids = db.session.query(ClassEnrollment.student_id).filter(
        ClassEnrollment.class_id.in_(class_ids)
    ).distinct().all()
    
    if not student_ids:
        return []
    
    student_ids = [sid[0] for sid in student_ids]
    
    # 今週の正解数をカウント
    ranking_data = db.session.query(
        AnswerRecord.student_id,
        func.count(AnswerRecord.id).label('weekly_correct')
    ).filter(
        AnswerRecord.student_id.in_(student_ids),
        AnswerRecord.is_correct == True,
        AnswerRecord.created_at >= week_start
    ).group_by(AnswerRecord.student_id).all()
    
    ranking = []
    for student_id, weekly_correct in ranking_data:
        user = User.query.get(student_id)
        if user:
            ranking.append({
                'student_id': student_id,
                'full_name': user.full_name or user.username,
                'username': user.username,
                'word_count': weekly_correct
            })
    
    ranking.sort(key=lambda x: x['word_count'], reverse=True)
    return ranking

@ranking_bp.route('/ranking_analysis')
@login_required
@student_required
def ranking_analysis():
    """ランキング分析ページ（学生用）- rankingページにリダイレクト"""
    flash('学生用のランキング詳細ページにアクセスしています。', 'info')
    return redirect(url_for('student_ranking.ranking'))

def _get_my_position(ranking, user_id):
    """自分の順位を取得"""
    for index, user_data in enumerate(ranking):
        if user_data['student_id'] == user_id:
            return index + 1
    return None