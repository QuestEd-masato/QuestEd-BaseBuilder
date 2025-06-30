"""
Rankings API
============
Phase 4.3: API分割実装 - ランキング・統計API

責任:
- 学習ランキングデータの取得
- 統計情報の提供
- ランキングキャッシュ管理
- データエクスポート機能

移行元: app/api/__init__.py の以下6ルート:
- /rankings/<ranking_type> (GET)
- /rankings/student/<int:student_id> (GET)
- /rankings/analytics/<int:class_id> (GET)
- /rankings/cache/clear (POST)
- /rankings/export (GET)
- /stats (GET)
"""

from flask import Blueprint, jsonify, request, make_response
from flask_login import login_required, current_user
import logging
import csv
import io
import json
from datetime import datetime, timedelta

from app.models import db, Ranking, RankingCache, User, Class, ClassEnrollment
from app.utils.rate_limiting import api_limit

rankings_bp = Blueprint('rankings', __name__)


@rankings_bp.route('/rankings/total_points', methods=['GET'])
@login_required
@api_limit()
def get_total_points_ranking():
    """総合ポイントランキング取得API（ダッシュボード用）"""
    try:
        # パラメータ取得
        scope = request.args.get('scope', 'school')  # 'school' or 'class'
        limit = min(request.args.get('limit', 10, type=int), 50)
        
        # 学生の場合は所属する学校のランキングのみ表示
        if current_user.role == 'student':
            school_id = current_user.school_id
            class_id = None
            
            # scopeがclassの場合、学生の所属クラスを取得
            if scope == 'class':
                enrollment = ClassEnrollment.query.filter_by(
                    student_id=current_user.id
                ).first()
                if enrollment:
                    class_id = enrollment.class_id
        
        # 教師の場合は担当クラスのランキングを表示
        elif current_user.role == 'teacher':
            school_id = current_user.school_id
            
            # 最初の担当クラスを取得
            teacher_class = Class.query.filter_by(
                teacher_id=current_user.id
            ).first()
            
            class_id = teacher_class.id if teacher_class and scope == 'class' else None
        else:
            school_id = None
            class_id = None
        
        # ランキングデータを生成
        ranking_data = _generate_ranking_data(
            'total_points',  # 総合ポイントランキング
            class_id=class_id,
            school_id=school_id,
            days_back=30,  # 過去30日間
            limit=limit
        )
        
        # 現在のユーザーのランキング情報を追加
        my_rank = None
        my_score = None
        
        for i, item in enumerate(ranking_data):
            if item['student_id'] == current_user.id:
                my_rank = i + 1
                my_score = item['score']
                break
        
        return jsonify({
            'status': 'success',
            'rankings': ranking_data,
            'my_rank': my_rank,
            'my_score': my_score,
            'scope': scope,
            'period': '過去30日間'
        })
        
    except Exception as e:
        logging.error(f"Get total points ranking error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'ランキング取得中にエラーが発生しました'
        }), 500


@rankings_bp.route('/rankings/<ranking_type>', methods=['GET'])
@login_required
@api_limit()
def get_ranking(ranking_type):
    """ランキングデータ取得API"""
    try:
        # ランキングタイプの妥当性確認
        valid_types = ['learning_time', 'accuracy', 'completion_rate', 'activity_points']
        
        if ranking_type not in valid_types:
            return jsonify({
                'status': 'error',
                'message': f'無効なランキングタイプです。有効な値: {", ".join(valid_types)}'
            }), 400
        
        # パラメータ取得
        class_id = request.args.get('class_id', type=int)
        school_id = request.args.get('school_id', type=int)
        period = request.args.get('period', 'week')  # 'week', 'month', 'all_time'
        limit = min(request.args.get('limit', 20, type=int), 100)
        
        # 期間設定
        period_mapping = {
            'week': 7,
            'month': 30,
            'all_time': None
        }
        
        if period not in period_mapping:
            return jsonify({
                'status': 'error',
                'message': '無効な期間設定です。有効な値: week, month, all_time'
            }), 400
        
        # 学生の場合は自分のクラス・学校のランキングのみ表示
        if current_user.role == 'student':
            if not class_id:
                # 学生が所属するクラスを取得
                enrollment = ClassEnrollment.query.filter_by(
                    student_id=current_user.id
                ).first()
                
                if enrollment:
                    class_id = enrollment.class_id
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'クラスに所属していません'
                    }), 400
            
            school_id = current_user.school_id
        
        # キャッシュキーの生成
        cache_key = f"{ranking_type}_{class_id or 'all'}_{school_id or 'all'}_{period}"
        
        # キャッシュから取得を試行
        cached_ranking = RankingCache.query.filter_by(
            cache_key=cache_key
        ).first()
        
        # キャッシュが有効（5分以内）な場合は使用
        if cached_ranking and cached_ranking.expires_at > datetime.utcnow():
            ranking_data = json.loads(cached_ranking.data)
            
            return jsonify({
                'status': 'success',
                'ranking_type': ranking_type,
                'period': period,
                'rankings': ranking_data,
                'cached': True,
                'cache_expires_at': cached_ranking.expires_at.isoformat()
            })
        
        # 新しいランキングデータを生成
        ranking_data = _generate_ranking_data(
            ranking_type, class_id, school_id, period_mapping[period], limit
        )
        
        # キャッシュに保存
        cache_expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        if cached_ranking:
            cached_ranking.data = json.dumps(ranking_data)
            cached_ranking.expires_at = cache_expires_at
            cached_ranking.updated_at = datetime.utcnow()
        else:
            new_cache = RankingCache(
                cache_key=cache_key,
                data=json.dumps(ranking_data),
                expires_at=cache_expires_at,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(new_cache)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'ranking_type': ranking_type,
            'period': period,
            'rankings': ranking_data,
            'cached': False
        })
        
    except Exception as e:
        logging.error(f"Get ranking error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'ランキング取得中にエラーが発生しました'
        }), 500


@rankings_bp.route('/rankings/student/<int:student_id>', methods=['GET'])
@login_required
@api_limit()
def get_student_ranking(student_id):
    """個別学生ランキング取得API"""
    try:
        # 権限確認
        if current_user.role == 'student' and current_user.id != student_id:
            return jsonify({
                'status': 'error',
                'message': '他の学生のランキングを表示する権限がありません'
            }), 403
        
        # 教師の場合は自分のクラスの学生のみ
        if current_user.role == 'teacher':
            student_in_class = db.session.query(ClassEnrollment).join(
                Class, ClassEnrollment.class_id == Class.id
            ).filter(
                Class.teacher_id == current_user.id,
                ClassEnrollment.student_id == student_id
            ).first()
            
            if not student_in_class:
                return jsonify({
                    'status': 'error',
                    'message': 'この学生のデータにアクセスする権限がありません'
                }), 403
        
        # 学生情報取得
        student = User.query.get(student_id)
        if not student or student.role != 'student':
            return jsonify({
                'status': 'error',
                'message': '指定された学生が見つかりません'
            }), 404
        
        # 各ランキングタイプでの順位を取得
        ranking_types = ['learning_time', 'accuracy', 'completion_rate', 'activity_points']
        student_rankings = {}
        
        for ranking_type in ranking_types:
            ranking_data = _generate_ranking_data(
                ranking_type, 
                class_id=None,  # 全体ランキング
                school_id=student.school_id,
                days_back=30,  # 過去30日
                limit=None  # 制限なし（順位計算のため）
            )
            
            # 学生の順位を見つける
            student_rank = None
            student_score = None
            
            for i, rank_item in enumerate(ranking_data):
                if rank_item['student_id'] == student_id:
                    student_rank = i + 1
                    student_score = rank_item['score']
                    break
            
            student_rankings[ranking_type] = {
                'rank': student_rank,
                'score': student_score,
                'total_participants': len(ranking_data)
            }
        
        # 学生の基本情報
        student_info = {
            'id': student.id,
            'name': student.name,
            'school_id': student.school_id
        }
        
        return jsonify({
            'status': 'success',
            'student': student_info,
            'rankings': student_rankings
        })
        
    except Exception as e:
        logging.error(f"Get student ranking error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '学生ランキング取得中にエラーが発生しました'
        }), 500


@rankings_bp.route('/rankings/analytics/<int:class_id>', methods=['GET'])
@login_required
@api_limit()
def get_ranking_analytics(class_id):
    """クラス別ランキング分析API"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({
                'status': 'error',
                'message': 'この機能は教師・管理者のみ利用できます'
            }), 403
        
        # 権限確認（教師は自分のクラスのみ）
        if current_user.role == 'teacher':
            class_obj = Class.query.filter_by(
                id=class_id,
                teacher_id=current_user.id
            ).first()
            
            if not class_obj:
                return jsonify({
                    'status': 'error',
                    'message': 'このクラスにアクセスする権限がありません'
                }), 403
        else:
            class_obj = Class.query.get(class_id)
            
            if not class_obj:
                return jsonify({
                    'status': 'error',
                    'message': '指定されたクラスが見つかりません'
                }), 404
        
        # クラスの学生数
        student_count = ClassEnrollment.query.filter_by(class_id=class_id).count()
        
        # 各ランキングタイプの分析
        analytics_data = {}
        ranking_types = ['learning_time', 'accuracy', 'completion_rate', 'activity_points']
        
        for ranking_type in ranking_types:
            class_ranking = _generate_ranking_data(
                ranking_type,
                class_id=class_id,
                school_id=None,
                days_back=30,
                limit=None
            )
            
            if class_ranking:
                scores = [item['score'] for item in class_ranking]
                
                analytics_data[ranking_type] = {
                    'student_count': len(class_ranking),
                    'average_score': sum(scores) / len(scores) if scores else 0,
                    'max_score': max(scores) if scores else 0,
                    'min_score': min(scores) if scores else 0,
                    'top_students': class_ranking[:3],  # 上位3名
                    'bottom_students': class_ranking[-3:] if len(class_ranking) >= 3 else []
                }
            else:
                analytics_data[ranking_type] = {
                    'student_count': 0,
                    'average_score': 0,
                    'max_score': 0,
                    'min_score': 0,
                    'top_students': [],
                    'bottom_students': []
                }
        
        # クラス情報
        class_info = {
            'id': class_obj.id,
            'name': class_obj.name,
            'teacher_name': class_obj.teacher.name if class_obj.teacher else 'Unknown',
            'total_students': student_count
        }
        
        return jsonify({
            'status': 'success',
            'class': class_info,
            'analytics': analytics_data,
            'analysis_period': '過去30日間'
        })
        
    except Exception as e:
        logging.error(f"Get ranking analytics error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'ランキング分析取得中にエラーが発生しました'
        }), 500


@rankings_bp.route('/rankings/cache/clear', methods=['POST'])
@login_required
@api_limit()
def clear_ranking_cache():
    """ランキングキャッシュクリアAPI"""
    try:
        # 管理者のみアクセス可能
        if current_user.role != 'admin':
            return jsonify({
                'status': 'error',
                'message': 'この機能は管理者のみ利用できます'
            }), 403
        
        data = request.get_json()
        cache_type = data.get('cache_type', 'all') if data else 'all'
        
        if cache_type == 'all':
            # 全キャッシュをクリア
            deleted_count = RankingCache.query.delete()
        elif cache_type == 'expired':
            # 期限切れキャッシュのみクリア
            deleted_count = RankingCache.query.filter(
                RankingCache.expires_at <= datetime.utcnow()
            ).delete()
        else:
            # 特定のキーパターンをクリア
            deleted_count = RankingCache.query.filter(
                RankingCache.cache_key.like(f'{cache_type}%')
            ).delete()
        
        db.session.commit()
        
        logging.info(f"Ranking cache cleared: type={cache_type}, count={deleted_count}, admin_id={current_user.id}")
        
        return jsonify({
            'status': 'success',
            'message': f'{deleted_count}件のキャッシュをクリアしました',
            'cleared_count': deleted_count
        })
        
    except Exception as e:
        logging.error(f"Clear ranking cache error: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'キャッシュクリア中にエラーが発生しました'
        }), 500


@rankings_bp.route('/rankings/export', methods=['GET'])
@login_required
@api_limit()
def export_ranking_data():
    """ランキングデータエクスポートAPI"""
    try:
        # 教師・管理者のみアクセス可能
        if current_user.role not in ['teacher', 'admin']:
            return jsonify({
                'status': 'error',
                'message': 'この機能は教師・管理者のみ利用できます'
            }), 403
        
        # パラメータ取得
        ranking_type = request.args.get('ranking_type', 'learning_time')
        class_id = request.args.get('class_id', type=int)
        period = request.args.get('period', 'month')
        format_type = request.args.get('format', 'csv')
        
        # 権限確認（教師は自分のクラスのみ）
        if current_user.role == 'teacher':
            if class_id:
                class_obj = Class.query.filter_by(
                    id=class_id,
                    teacher_id=current_user.id
                ).first()
                
                if not class_obj:
                    return jsonify({
                        'status': 'error',
                        'message': 'このクラスのデータをエクスポートする権限がありません'
                    }), 403
            else:
                # 教師の全クラスを取得
                teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
                if not teacher_classes:
                    return jsonify({
                        'status': 'error',
                        'message': 'エクスポート可能なクラスがありません'
                    }), 400
        
        # ランキングデータ取得
        period_mapping = {'week': 7, 'month': 30, 'all_time': None}
        ranking_data = _generate_ranking_data(
            ranking_type,
            class_id=class_id,
            school_id=current_user.school_id if current_user.role == 'teacher' else None,
            days_back=period_mapping.get(period),
            limit=None
        )
        
        if format_type == 'csv':
            # CSV形式でエクスポート
            output = io.StringIO()
            writer = csv.writer(output)
            
            # ヘッダー
            writer.writerow(['順位', '学生名', 'スコア', '学校ID', 'クラス名'])
            
            # データ行
            for i, item in enumerate(ranking_data):
                writer.writerow([
                    i + 1,
                    item['student_name'],
                    item['score'],
                    item.get('school_id', ''),
                    item.get('class_name', '')
                ])
            
            # レスポンス作成
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename="ranking_{ranking_type}_{period}.csv"'
            
            return response
        
        else:
            # JSON形式（デフォルト）
            return jsonify({
                'status': 'success',
                'ranking_type': ranking_type,
                'period': period,
                'export_date': datetime.utcnow().isoformat(),
                'data': ranking_data
            })
        
    except Exception as e:
        logging.error(f"Export ranking data error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'データエクスポート中にエラーが発生しました'
        }), 500


@rankings_bp.route('/stats', methods=['GET'])
@login_required
@api_limit()
def get_user_stats():
    """ユーザー統計取得API"""
    try:
        # 統計タイプ
        stat_type = request.args.get('type', 'overview')  # 'overview', 'detailed', 'comparison'
        
        if current_user.role == 'student':
            # 学生の個人統計
            stats = _get_student_stats(current_user.id, stat_type)
        elif current_user.role == 'teacher':
            # 教師のクラス統計
            stats = _get_teacher_stats(current_user.id, stat_type)
        else:
            # 管理者の全体統計
            stats = _get_admin_stats(stat_type)
        
        return jsonify({
            'status': 'success',
            'user_role': current_user.role,
            'stats': stats
        })
        
    except Exception as e:
        logging.error(f"Get user stats error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '統計取得中にエラーが発生しました'
        }), 500


# ヘルパー関数

def _generate_ranking_data(ranking_type, class_id=None, school_id=None, days_back=None, limit=None):
    """ランキングデータを生成"""
    # TODO: 実際のランキング計算ロジックを実装
    # ここでは仮のデータを返す
    
    # 基本クエリ構築
    query = db.session.query(User).filter_by(role='student')
    
    if school_id:
        query = query.filter_by(school_id=school_id)
    
    if class_id:
        query = query.join(ClassEnrollment).filter(ClassEnrollment.class_id == class_id)
    
    students = query.all()
    
    # 仮のランキングデータ生成
    ranking_data = []
    import random  # 開発用の仮データ生成
    
    for student in students:
        # TODO: 実際の計算ロジック
        # 現在は仮のスコアを生成
        if ranking_type == 'total_points':
            score = random.randint(500, 5000)  # 総合ポイント
        elif ranking_type == 'learning_time':
            score = random.randint(10, 300)  # 学習時間（分）
        elif ranking_type == 'accuracy':
            score = random.randint(60, 100)  # 正解率（%）
        elif ranking_type == 'completion_rate':
            score = random.randint(0, 100)  # 完了率（%）
        elif ranking_type == 'activity_points':
            score = random.randint(0, 1000)  # 活動ポイント
        else:
            score = 100  # デフォルト
        
        ranking_data.append({
            'student_id': student.id,
            'student_name': student.full_name or student.username,
            'score': score,
            'school_id': student.school_id,
            'class_name': 'Unknown'  # TODO: クラス名取得
        })
    
    # スコア順にソート
    ranking_data.sort(key=lambda x: x['score'], reverse=True)
    
    if limit:
        ranking_data = ranking_data[:limit]
    
    return ranking_data


def _get_student_stats(student_id, stat_type):
    """学生統計を取得"""
    # TODO: 実際の統計計算
    return {
        'learning_time_today': 45,
        'accuracy_rate': 85.5,
        'completed_units': 12,
        'total_activities': 156
    }


def _get_teacher_stats(teacher_id, stat_type):
    """教師統計を取得"""
    # TODO: 実際の統計計算
    return {
        'total_students': 25,
        'active_students': 23,
        'pending_approvals': 3,
        'average_class_progress': 67.8
    }


def _get_admin_stats(stat_type):
    """管理者統計を取得"""
    # TODO: 実際の統計計算
    return {
        'total_users': 1250,
        'active_students': 890,
        'total_teachers': 45,
        'system_utilization': 78.5
    }