"""
ランキングシステム ルーティング

ランキング表示のUI・APIエンドポイント
"""

from flask import Blueprint, jsonify, request, current_app, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

from app.utils.decorators import student_required, teacher_required
from ..services.ranking_service import RankingService

ranking_bp = Blueprint('ranking_system', __name__, url_prefix='/ranking-system')


# === UI表示用ルート ===

@ranking_bp.route('/student/dashboard')
@login_required
@student_required
def student_ranking_dashboard():
    """学生用：ランキングダッシュボード"""
    try:
        # 学生のクラス情報を取得
        student_class = current_user.get_current_class()
        
        if not student_class:
            flash("クラス情報が見つかりません。", "warning")
            return redirect(url_for('student_dashboard.dashboard'))
        
        # 各種ランキングデータを取得
        lesson_progress_ranking = RankingService.get_lesson_progress_ranking(student_class.id, 10)
        vocabulary_ranking = RankingService.get_vocabulary_ranking(student_class.id, 10)
        overall_ranking = RankingService.get_overall_ranking(student_class.id, 10)
        
        # 学生の現在の順位を取得
        student_rank = RankingService.get_student_rank(current_user.id, student_class.id)
        
        # 統計情報を取得
        ranking_stats = RankingService.get_ranking_statistics(student_class.id)
        
        return render_template(
            'ranking_system/student/ranking_dashboard.html',
            lesson_progress_ranking=lesson_progress_ranking,
            vocabulary_ranking=vocabulary_ranking,
            overall_ranking=overall_ranking,
            student_rank=student_rank,
            ranking_stats=ranking_stats,
            student_class=student_class
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in student_ranking_dashboard: {e}")
        flash("ランキングダッシュボードの読み込み中にエラーが発生しました。", "error")
        return redirect(url_for('student_dashboard.dashboard'))


@ranking_bp.route('/teacher/class-ranking')
@login_required
@teacher_required
def teacher_class_ranking():
    """教師用：クラスランキング管理"""
    try:
        # 教師のクラス一覧を取得
        teacher_classes = current_user.get_teacher_classes()
        
        # 選択されたクラスIDを取得（デフォルトは最初のクラス）
        selected_class_id = request.args.get('class_id', type=int)
        if not selected_class_id and teacher_classes:
            selected_class_id = teacher_classes[0].id
        
        selected_class = None
        ranking_data = {}
        
        if selected_class_id:
            selected_class = next((cls for cls in teacher_classes if cls.id == selected_class_id), None)
            
            if selected_class:
                # 各種ランキングデータを取得
                ranking_data = {
                    'lesson_progress': RankingService.get_lesson_progress_ranking(selected_class_id, 20),
                    'vocabulary': RankingService.get_vocabulary_ranking(selected_class_id, 20),
                    'overall': RankingService.get_overall_ranking(selected_class_id, 20)
                }
                
                # 詳細統計情報を取得
                ranking_data['statistics'] = RankingService.get_detailed_ranking_statistics(selected_class_id)
        
        return render_template(
            'ranking_system/teacher/class_ranking.html',
            teacher_classes=teacher_classes,
            selected_class=selected_class,
            ranking_data=ranking_data
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in teacher_class_ranking: {e}")
        flash("クラスランキングの読み込み中にエラーが発生しました。", "error")
        return redirect(url_for('teacher_dashboard.dashboard'))


# === API エンドポイント ===

@ranking_bp.route('/api/lesson-progress')
@login_required
def get_lesson_progress_ranking():
    """レッスン進捗ランキングAPI"""
    try:
        class_id = request.args.get('class_id', type=int)
        limit = request.args.get('limit', 10, type=int)
        
        rankings = RankingService.get_lesson_progress_ranking(class_id, limit)
        
        return jsonify({
            'success': True,
            'rankings': rankings
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_lesson_progress_ranking: {e}")
        return jsonify({
            'success': False,
            'message': 'ランキングの取得に失敗しました。'
        }), 500


@ranking_bp.route('/api/vocabulary')
@login_required
def get_vocabulary_ranking():
    """語彙習熟度ランキングAPI"""
    try:
        class_id = request.args.get('class_id', type=int)
        limit = request.args.get('limit', 10, type=int)
        
        rankings = RankingService.get_vocabulary_ranking(class_id, limit)
        
        return jsonify({
            'success': True,
            'rankings': rankings
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_vocabulary_ranking: {e}")
        return jsonify({
            'success': False,
            'message': 'ランキングの取得に失敗しました。'
        }), 500


@ranking_bp.route('/api/overall')
@login_required
def get_overall_ranking():
    """総合ランキングAPI"""
    try:
        class_id = request.args.get('class_id', type=int)
        limit = request.args.get('limit', 10, type=int)
        
        rankings = RankingService.get_overall_ranking(class_id, limit)
        
        return jsonify({
            'success': True,
            'rankings': rankings
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_overall_ranking: {e}")
        return jsonify({
            'success': False,
            'message': 'ランキングの取得に失敗しました。'
        }), 500