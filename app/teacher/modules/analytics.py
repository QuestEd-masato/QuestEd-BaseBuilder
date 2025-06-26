# app/teacher/modules/analytics.py
"""分析・統計機能"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from app.models import Class, ClassEnrollment, User, ActivityLog, Goal
from app.services.ranking_service import RankingService
from ..common import teacher_required

analytics_bp = Blueprint('teacher_analytics', __name__)

@analytics_bp.route('/class/<int:class_id>/analytics')
@login_required
@teacher_required
def class_analytics(class_id):
    """クラス分析ダッシュボード"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスの分析データを表示する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    # 基本統計を生成
    analytics_data = _generate_class_analytics(class_id)
    
    return render_template('class_analytics.html', 
                         class_obj=class_obj,
                         analytics=analytics_data)

@analytics_bp.route('/ranking_analysis')
@login_required
@teacher_required
def ranking_analysis():
    """ランキング分析"""
    # 教師が担当するクラスを取得
    teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
    
    if not teacher_classes:
        flash('担当するクラスがありません。')
        return redirect(url_for('teacher_dashboard.dashboard'))
    
    # 各クラスのランキングデータを取得
    class_rankings = {}
    
    for class_obj in teacher_classes:
        try:
            # RankingServiceを使用してランキングを取得
            ranking_data = RankingService.get_class_ranking(
                class_id=class_obj.id,
                limit=10
            )
            
            class_rankings[class_obj.id] = {
                'class': class_obj,
                'ranking': ranking_data.get('ranking', []),
                'stats': ranking_data.get('stats', {}),
                'error': None
            }
            
        except Exception as e:
            class_rankings[class_obj.id] = {
                'class': class_obj,
                'ranking': [],
                'stats': {},
                'error': str(e)
            }
    
    return render_template('ranking_analysis.html', 
                         class_rankings=class_rankings)

@analytics_bp.route('/api/class/<int:class_id>/ranking')
@login_required
@teacher_required
def api_class_ranking(class_id):
    """クラスランキングAPI"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        # RankingServiceを使用
        ranking_data = RankingService.get_class_ranking(
            class_id=class_id,
            limit=request.args.get('limit', 20, type=int)
        )
        
        return jsonify({
            'success': True,
            'class_name': class_obj.name,
            'ranking': ranking_data.get('ranking', []),
            'stats': ranking_data.get('stats', {}),
            'updated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'ランキングデータの取得に失敗しました: {str(e)}'
        }), 500

@analytics_bp.route('/api/class/<int:class_id>/activity_trends')
@login_required
@teacher_required
def api_activity_trends(class_id):
    """活動トレンドAPI"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        # 過去30日間の活動データを取得
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # クラスの学生IDを取得
        enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
        student_ids = [e.student_id for e in enrollments]
        
        if not student_ids:
            return jsonify({
                'success': True,
                'trends': [],
                'summary': {'total_activities': 0, 'active_students': 0}
            })
        
        # 日別活動数を集計
        from sqlalchemy import func, text
        
        activity_trends = db.session.query(
            func.date(ActivityLog.created_at).label('date'),
            func.count(ActivityLog.id).label('activity_count'),
            func.count(func.distinct(ActivityLog.student_id)).label('active_students')
        ).filter(
            ActivityLog.student_id.in_(student_ids),
            ActivityLog.created_at >= start_date,
            ActivityLog.created_at <= end_date
        ).group_by(
            func.date(ActivityLog.created_at)
        ).order_by(
            func.date(ActivityLog.created_at)
        ).all()
        
        # データをフォーマット
        trends_data = []
        for trend in activity_trends:
            trends_data.append({
                'date': trend.date.isoformat(),
                'activity_count': trend.activity_count,
                'active_students': trend.active_students
            })
        
        # サマリー統計
        total_activities = sum(t['activity_count'] for t in trends_data)
        max_active_students = max((t['active_students'] for t in trends_data), default=0)
        
        return jsonify({
            'success': True,
            'trends': trends_data,
            'summary': {
                'total_activities': total_activities,
                'max_active_students': max_active_students,
                'period_days': 30
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'活動トレンドの取得に失敗しました: {str(e)}'
        }), 500

@analytics_bp.route('/api/class/<int:class_id>/goal_completion')
@login_required
@teacher_required
def api_goal_completion(class_id):
    """目標達成状況API"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        # クラスの学生IDを取得
        enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
        student_ids = [e.student_id for e in enrollments]
        
        if not student_ids:
            return jsonify({
                'success': True,
                'completion_stats': {},
                'student_goals': []
            })
        
        # 目標達成状況を集計
        from sqlalchemy import func
        
        goal_stats = db.session.query(
            Goal.status,
            func.count(Goal.id).label('count')
        ).filter(
            Goal.student_id.in_(student_ids)
        ).group_by(Goal.status).all()
        
        completion_stats = {}
        for stat in goal_stats:
            completion_stats[stat.status] = stat.count
        
        # 学生別目標データ
        student_goals = []
        for enrollment in enrollments:
            student = enrollment.student
            goals = Goal.query.filter_by(student_id=student.id).all()
            
            student_goal_data = {
                'student_id': student.id,
                'student_name': student.full_name or student.username,
                'total_goals': len(goals),
                'completed_goals': len([g for g in goals if g.status == 'completed']),
                'in_progress_goals': len([g for g in goals if g.status == 'in_progress']),
                'not_started_goals': len([g for g in goals if g.status == 'not_started'])
            }
            
            if student_goal_data['total_goals'] > 0:
                student_goal_data['completion_rate'] = round(
                    (student_goal_data['completed_goals'] / student_goal_data['total_goals']) * 100, 1
                )
            else:
                student_goal_data['completion_rate'] = 0
            
            student_goals.append(student_goal_data)
        
        return jsonify({
            'success': True,
            'completion_stats': completion_stats,
            'student_goals': student_goals
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'目標達成状況の取得に失敗しました: {str(e)}'
        }), 500

def _generate_class_analytics(class_id):
    """クラス分析データ生成ヘルパー"""
    try:
        # 基本統計
        enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
        total_students = len(enrollments)
        
        if total_students == 0:
            return {
                'basic_stats': {
                    'total_students': 0,
                    'active_students': 0,
                    'total_activities': 0,
                    'avg_activities_per_student': 0
                },
                'activity_distribution': [],
                'recent_activity': []
            }
        
        student_ids = [e.student_id for e in enrollments]
        
        # 活動統計
        from sqlalchemy import func
        
        # 過去7日間のアクティブ学生数
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        active_students = db.session.query(
            func.count(func.distinct(ActivityLog.student_id))
        ).filter(
            ActivityLog.student_id.in_(student_ids),
            ActivityLog.created_at >= seven_days_ago
        ).scalar() or 0
        
        # 総活動数
        total_activities = ActivityLog.query.filter(
            ActivityLog.student_id.in_(student_ids)
        ).count()
        
        # 学生別活動分布
        activity_distribution = db.session.query(
            User.username,
            func.count(ActivityLog.id).label('activity_count')
        ).join(
            ActivityLog, User.id == ActivityLog.student_id
        ).filter(
            User.id.in_(student_ids)
        ).group_by(
            User.id, User.username
        ).order_by(
            func.count(ActivityLog.id).desc()
        ).limit(10).all()
        
        # 最近の活動（過去10件）
        recent_activities = db.session.query(
            ActivityLog.content,
            ActivityLog.created_at,
            User.username
        ).join(
            User, ActivityLog.student_id == User.id
        ).filter(
            ActivityLog.student_id.in_(student_ids)
        ).order_by(
            ActivityLog.created_at.desc()
        ).limit(10).all()
        
        return {
            'basic_stats': {
                'total_students': total_students,
                'active_students': active_students,
                'total_activities': total_activities,
                'avg_activities_per_student': round(total_activities / total_students, 1) if total_students > 0 else 0
            },
            'activity_distribution': [
                {
                    'username': dist.username,
                    'activity_count': dist.activity_count
                } for dist in activity_distribution
            ],
            'recent_activities': [
                {
                    'content': activity.content,
                    'created_at': activity.created_at.strftime('%Y-%m-%d %H:%M'),
                    'username': activity.username
                } for activity in recent_activities
            ]
        }
        
    except Exception as e:
        logging.error(f"Analytics generation error: {str(e)}")
        return {
            'basic_stats': {
                'total_students': 0,
                'active_students': 0,
                'total_activities': 0,
                'avg_activities_per_student': 0
            },
            'activity_distribution': [],
            'recent_activities': [],
            'error': str(e)
        }