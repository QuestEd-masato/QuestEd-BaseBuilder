"""
BaseBuilder Text Management Routes
=================================
テキストアクセス・表示・配信に関するルートハンドラ

不足していたテキスト機能のルートを実装:
- /my_texts (学生向けテキスト一覧)
- /text_sets (教師向けテキスト管理)
- /text/<int:text_id>/view (テキスト詳細表示)
- /text/<int:text_id>/deliver (テキスト配信)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from typing import Dict, List, Any

from extensions import db
from basebuilder.models import (
    TextSet, TextDelivery, ProblemCategory, BasicKnowledgeItem,
    TextProficiencyRecord, AnswerRecord
)
from app.models import User, Class, ClassEnrollment
from basebuilder.utils import require_roles, handle_db_error
# log_activityは内部で定義されているため、basebuilder.utilsからはインポートしない

texts_bp = Blueprint('texts', __name__, url_prefix='/basebuilder')

@texts_bp.route('/debug/text_data')
@login_required
def debug_text_data():
    """デバッグ: テキストデータの状況を確認"""
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # 全テキストセット数
        total_texts = TextSet.query.count()
        
        # 学校別テキスト数
        school_texts = {}
        if hasattr(current_user, 'school_id'):
            school_texts['user_school_id'] = current_user.school_id
            school_texts['user_school_texts'] = TextSet.query.filter_by(
                school_id=current_user.school_id
            ).count()
            school_texts['null_school_texts'] = TextSet.query.filter_by(
                school_id=None
            ).count()
        
        # カテゴリ別テキスト数
        category_texts = db.session.query(
            ProblemCategory.name,
            db.func.count(TextSet.id)
        ).join(
            TextSet, TextSet.category_id == ProblemCategory.id
        ).group_by(ProblemCategory.id).all()
        
        return jsonify({
            'total_texts': total_texts,
            'school_info': school_texts,
            'category_breakdown': [
                {'category': cat, 'count': count} 
                for cat, count in category_texts
            ],
            'user_info': {
                'id': current_user.id,
                'role': current_user.role,
                'school_id': getattr(current_user, 'school_id', None)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def log_activity(action, description):
    """簡易アクティビティログ記録"""
    try:
        current_app.logger.info(
            f"BASEBUILDER_ACTIVITY: user_id={current_user.id}, "
            f"action={action}, description={description}, "
            f"timestamp={datetime.utcnow()}"
        )
    except Exception as e:
        current_app.logger.error(f"Activity log error: {str(e)}")


@texts_bp.route('/my_texts')
@login_required
def my_texts():
    """学生向け: 配信されたテキスト一覧表示"""
    try:
        # 権限チェック
        if current_user.role != 'student':
            flash('学生のみアクセス可能です。')
            return redirect(url_for('index'))
        # 学生の所属クラスを取得
        enrolled_class_ids = [enrollment.class_id for enrollment in 
                            ClassEnrollment.query.filter_by(
                                student_id=current_user.id,
                                is_active=True
                            ).all()]
        
        if not enrolled_class_ids:
            flash('所属クラスが見つかりません。管理者にお問い合わせください。', 'warning')
            return render_template('basebuilder/my_texts.html', 
                                 deliveries=[], 
                                 text_proficiency={},
                                 now=datetime.now())
        
        # 配信されたテキストを取得
        deliveries = TextDelivery.query.filter(
            TextDelivery.class_id.in_(enrolled_class_ids)
        ).join(TextSet).order_by(
            TextDelivery.delivered_at.desc()
        ).all()
        
        # テキスト習熟度を取得
        text_proficiency = {}
        proficiency_records = TextProficiencyRecord.query.filter_by(
            student_id=current_user.id
        ).all()
        
        for record in proficiency_records:
            text_proficiency[record.text_set_id] = {
                'level': record.level,
                'last_study': record.updated_at
            }
        
        log_activity("text_list_viewed", f"Student {current_user.id} viewed text list")
        
        return render_template('basebuilder/my_texts.html',
                             deliveries=deliveries,
                             text_proficiency=text_proficiency,
                             now=datetime.now())
        
    except Exception as e:
        current_app.logger.error(f"My texts error: {str(e)}")
        flash('テキスト一覧の取得中にエラーが発生しました。', 'error')
        return render_template('basebuilder/my_texts.html', 
                             deliveries=[], 
                             text_proficiency={},
                             now=datetime.now())


@texts_bp.route('/text_sets')
@login_required
def text_sets():
    """教師・管理者向け: テキストセット一覧"""
    try:
        # 権限チェック
        if current_user.role not in ['admin', 'teacher']:
            flash('教師または管理者のみアクセス可能です。')
            return redirect(url_for('index'))
        # フィルタリングパラメータ
        category_id = request.args.get('category_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 基本クエリ
        query = TextSet.query
        
        # 教師の場合は自分の学校のテキストのみ
        if current_user.role == 'teacher' and hasattr(current_user, 'school_id'):
            query = query.filter(
                db.or_(
                    TextSet.school_id == current_user.school_id,
                    TextSet.school_id == None  # 全学校共通のテキストも表示
                )
            )
        
        # カテゴリフィルタ
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        # ページネーション
        text_sets_pagination = query.order_by(
            TextSet.created_at.desc()
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # カテゴリ一覧
        categories = ProblemCategory.query.order_by(ProblemCategory.name).all()
        
        # デバッグログ
        current_app.logger.info(f"Text sets query for user {current_user.id} (role: {current_user.role}, school_id: {getattr(current_user, 'school_id', 'None')})")
        current_app.logger.info(f"Found {text_sets_pagination.total} text sets")
        
        # 各テキストセットの問題数を計算
        text_stats = {}
        for text_set in text_sets_pagination.items:
            problem_count = BasicKnowledgeItem.query.filter_by(
                text_set_id=text_set.id
            ).count()
            delivery_count = TextDelivery.query.filter_by(
                text_set_id=text_set.id
            ).count()
            
            text_stats[text_set.id] = {
                'problem_count': problem_count,
                'delivery_count': delivery_count
            }
        
        return render_template('basebuilder/text_sets.html',
                             text_sets=text_sets_pagination.items,
                             pagination=text_sets_pagination,
                             categories=categories,
                             text_stats=text_stats,
                             selected_category=category_id)
        
    except Exception as e:
        current_app.logger.error(f"Text sets error: {str(e)}")
        flash('テキストセット一覧の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('basebuilder.index'))




@texts_bp.route('/text/<int:text_id>/deliver', methods=['GET', 'POST'])
@login_required
def deliver_text(text_id):
    """教師・管理者向け: テキスト配信"""
    try:
        # 権限チェック
        if current_user.role not in ['admin', 'teacher']:
            flash('教師または管理者のみアクセス可能です。')
            return redirect(url_for('index'))
        
        text_set = TextSet.query.get_or_404(text_id)
        
        # 権限チェック（教師は自分の学校のテキストのみ）
        if current_user.role == 'teacher' and text_set.school_id != current_user.school_id:
            flash('このテキストを配信する権限がありません。', 'error')
            return redirect(url_for('texts.text_sets'))
        
        if request.method == 'POST':
            class_ids = request.form.getlist('class_ids')
            due_date_str = request.form.get('due_date')
            instructions = request.form.get('instructions', '').strip()
            
            if not class_ids:
                flash('配信先クラスを選択してください。', 'error')
                return render_template('basebuilder/deliver_text.html',
                                     text_set=text_set,
                                     classes=_get_available_classes())
            
            # 提出期限の処理
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                    if due_date < date.today():
                        flash('提出期限は今日以降の日付を設定してください。', 'error')
                        return render_template('basebuilder/deliver_text.html',
                                             text_set=text_set,
                                             classes=_get_available_classes())
                except ValueError:
                    flash('無効な日付形式です。', 'error')
                    return render_template('basebuilder/deliver_text.html',
                                         text_set=text_set,
                                         classes=_get_available_classes())
            
            # 配信実行
            success_count = 0
            for class_id in class_ids:
                try:
                    class_id = int(class_id)
                    
                    # 既存の配信をチェック
                    existing_delivery = TextDelivery.query.filter_by(
                        text_set_id=text_id,
                        class_id=class_id
                    ).first()
                    
                    if existing_delivery:
                        continue  # 既に配信済みはスキップ
                    
                    # 新しい配信を作成
                    delivery = TextDelivery(
                        text_set_id=text_id,
                        class_id=class_id,
                        delivered_by=current_user.id,
                        delivered_at=datetime.utcnow(),
                        due_date=due_date,
                        instructions=instructions
                    )
                    
                    db.session.add(delivery)
                    success_count += 1
                    
                except (ValueError, TypeError):
                    continue
            
            if success_count > 0:
                db.session.commit()
                log_activity("text_delivered", f"Text {text_id} delivered to {success_count} classes")
                flash(f'テキストを{success_count}クラスに配信しました。', 'success')
            else:
                flash('配信できるクラスがありませんでした（既に配信済みの可能性があります）。', 'warning')
            
            return redirect(url_for('texts.text_sets'))
        
        # GET: 配信フォームを表示
        classes = _get_available_classes()
        return render_template('basebuilder/deliver_text.html',
                             text_set=text_set,
                             classes=classes)
        
    except Exception as e:
        current_app.logger.error(f"Deliver text error: {str(e)}")
        flash('テキスト配信中にエラーが発生しました。', 'error')
        return redirect(url_for('texts.text_sets'))


def _get_available_classes():
    """利用可能なクラス一覧を取得"""
    if current_user.role == 'admin':
        return Class.query.order_by(Class.name).all()
    elif current_user.role == 'teacher':
        return Class.query.filter_by(
            school_id=current_user.school_id
        ).order_by(Class.name).all()
    else:
        return []


@texts_bp.route('/text/<int:text_id>/problems')
@login_required
@handle_db_error("テキスト問題一覧")
def text_problems(text_id):
    """テキスト内の問題一覧（管理用）"""
    try:
        text_set = TextSet.query.get_or_404(text_id)
        
        # 権限チェック
        if current_user.role == 'teacher' and text_set.school_id != current_user.school_id:
            flash('このテキストにアクセスする権限がありません。', 'error')
            return redirect(url_for('texts.text_sets'))
        
        problems = BasicKnowledgeItem.query.filter_by(
            text_set_id=text_id
        ).order_by(BasicKnowledgeItem.order_in_text).all()
        
        return render_template('basebuilder/text_problems.html',
                             text_set=text_set,
                             problems=problems)
        
    except Exception as e:
        current_app.logger.error(f"Text problems error: {str(e)}")
        flash('問題一覧の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('texts.text_sets'))