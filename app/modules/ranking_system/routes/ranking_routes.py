"""
ランキングシステム ルーティング（簡易版）

ランキング表示のAPIエンドポイント
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user

from app.utils.decorators import student_required, teacher_required
from ..services.ranking_service import RankingService

ranking_bp = Blueprint('ranking_system', __name__, url_prefix='/ranking-system')


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