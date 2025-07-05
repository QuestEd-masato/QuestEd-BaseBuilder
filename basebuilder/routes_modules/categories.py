"""
BaseBuilder Categories Routes - Simplified Version
==================================================
最小限の依存関係でカテゴリ管理機能を提供
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime

categories_bp = Blueprint('categories', __name__, url_prefix='/basebuilder')

def log_activity(action, description, category_id=None):
    """簡易アクティビティログ記録"""
    try:
        current_app.logger.info(
            f"BASEBUILDER_ACTIVITY: user_id={current_user.id}, "
            f"action={action}, description={description}, "
            f"category_id={category_id}, timestamp={datetime.utcnow()}"
        )
    except Exception as e:
        current_app.logger.error(f"Activity log error: {str(e)}")

@categories_bp.route('/categories')
@login_required
def categories():
    """カテゴリ一覧表示 - 簡素化版"""
    try:
        # アクティビティログ記録
        log_activity("category_list_view", "Categories list accessed")
        from extensions import db
        from basebuilder.models import ProblemCategory
        
        # 基本的なカテゴリ一覧取得
        categories = ProblemCategory.query.order_by(ProblemCategory.name).all()
        
        # 統計情報を実際のデータから計算
        from basebuilder.models import BasicKnowledgeItem, TextSet, AnswerRecord
        
        category_stats = {}
        for category in categories:
            # 問題数カウント
            problem_count = BasicKnowledgeItem.query.filter_by(category_id=category.id).count()
            
            # テキスト数カウント
            text_count = TextSet.query.filter_by(category_id=category.id).count()
            
            # 使用回数カウント（そのカテゴリの問題への回答数）
            usage_count = AnswerRecord.query.join(BasicKnowledgeItem).filter(
                BasicKnowledgeItem.category_id == category.id
            ).count()
            
            category_stats[category.id] = {
                'problem_count': problem_count,
                'text_count': text_count,
                'usage_count': usage_count
            }
        
        return render_template('basebuilder/categories.html', 
                             categories=categories,
                             category_stats=category_stats)
    
    except Exception as e:
        current_app.logger.error(f"Categories error: {str(e)}")
        flash('カテゴリ一覧の取得中にエラーが発生しました。')
        
        # フォールバック: 基本的なページを表示
        return render_template('basebuilder/categories_fallback.html',
                             categories=[],
                             category_stats={})


@categories_bp.route('/category/create', methods=['GET', 'POST'])
@login_required
def create_category():
    """カテゴリ作成 - 簡素化版"""
    try:
        # 権限チェック
        if current_user.role not in ['admin', 'teacher']:
            flash('カテゴリの作成権限がありません。')
            return redirect(url_for('categories.categories'))
        
        if request.method == 'POST':
            from extensions import db
            from basebuilder.models import ProblemCategory
            
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            subject = request.form.get('subject', '').strip()
            grade_level = request.form.get('grade_level', type=int)
            difficulty_level = request.form.get('difficulty_level', type=int)
            
            if not name:
                flash('カテゴリ名を入力してください。', 'error')
                return render_template('basebuilder/create_category.html')
            
            # 重複チェック
            existing_category = ProblemCategory.query.filter_by(name=name).first()
            if existing_category:
                flash('同じ名前のカテゴリが既に存在します。', 'error')
                return render_template('basebuilder/create_category.html')
            
            # 新しいカテゴリを作成（拡張フィールド対応）
            new_category = ProblemCategory(
                name=name,
                description=description,
                subject=subject,
                grade_level=grade_level,
                difficulty_level=difficulty_level,
                created_by=current_user.id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_category)
            db.session.commit()
            
            # アクティビティログ記録
            log_activity("category_created", f"Category '{name}' created", new_category.id)
            
            flash(f'カテゴリ「{name}」を作成しました。', 'success')
            return redirect(url_for('categories.categories'))
        
        return render_template('basebuilder/create_category.html')
    
    except Exception as e:
        current_app.logger.error(f"Create category error: {str(e)}")
        flash('カテゴリ作成中にエラーが発生しました。')
        return redirect(url_for('categories.categories'))


@categories_bp.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required  
def edit_category(category_id):
    """カテゴリ編集 - 簡素化版"""
    try:
        from extensions import db
        from basebuilder.models import ProblemCategory
        
        category = ProblemCategory.query.get_or_404(category_id)
        
        # 権限チェック
        if current_user.role not in ['admin', 'teacher']:
            flash('カテゴリの編集権限がありません。')
            return redirect(url_for('categories.categories'))
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            subject = request.form.get('subject', '').strip()
            grade_level = request.form.get('grade_level', type=int)
            difficulty_level = request.form.get('difficulty_level', type=int)
            
            if not name:
                flash('カテゴリ名を入力してください。', 'error')
                return render_template('basebuilder/edit_category.html', category=category)
            
            # 重複チェック（自分以外）
            existing_category = ProblemCategory.query.filter(
                ProblemCategory.name == name,
                ProblemCategory.id != category_id
            ).first()
            
            if existing_category:
                flash('同じ名前のカテゴリが既に存在します。', 'error')
                return render_template('basebuilder/edit_category.html', category=category)
            
            # 更新（拡張フィールド対応）
            category.name = name
            category.description = description
            category.subject = subject
            category.grade_level = grade_level
            category.difficulty_level = difficulty_level
            category.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # アクティビティログ記録
            log_activity("category_updated", f"Category '{name}' updated", category.id)
            
            flash(f'カテゴリ「{name}」を更新しました。', 'success')
            return redirect(url_for('categories.categories'))
        
        return render_template('basebuilder/edit_category.html', category=category)
    
    except Exception as e:
        current_app.logger.error(f"Edit category error: {str(e)}")
        flash('カテゴリ編集中にエラーが発生しました。')
        return redirect(url_for('categories.categories'))


@categories_bp.route('/category/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    """カテゴリ削除 - 簡素化版"""
    try:
        from extensions import db
        from basebuilder.models import ProblemCategory
        
        # 権限チェック
        if current_user.role not in ['admin', 'teacher']:
            flash('カテゴリの削除権限がありません。')
            return redirect(url_for('categories.categories'))
        
        category = ProblemCategory.query.get_or_404(category_id)
        category_name = category.name
        
        db.session.delete(category)
        db.session.commit()
        
        # アクティビティログ記録
        log_activity("category_deleted", f"Category '{category_name}' deleted", category_id)
        
        flash(f'カテゴリ「{category_name}」を削除しました。', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Delete category error: {str(e)}")
        flash('カテゴリ削除中にエラーが発生しました。')
    
    return redirect(url_for('categories.categories'))


@categories_bp.route('/category/<int:category_id>/texts')
@login_required
def category_texts(category_id):
    """カテゴリ内のテキスト一覧 - 簡素化版"""
    try:
        from extensions import db
        from basebuilder.models import ProblemCategory, TextSet, BasicKnowledgeItem
        
        category = ProblemCategory.query.get_or_404(category_id)
        
        # カテゴリ内のテキストセットを取得
        query = TextSet.query.filter_by(category_id=category_id)
        
        # 教師の場合は自分の学校のテキストのみ表示
        if current_user.role == 'teacher' and hasattr(current_user, 'school_id'):
            query = query.filter(
                db.or_(
                    TextSet.school_id == current_user.school_id,
                    TextSet.school_id == None  # 全学校共通のテキストも表示
                )
            )
        
        text_sets = query.order_by(TextSet.created_at.desc()).all()
        
        # 各テキストセットの問題数を計算
        text_stats = {}
        for text_set in text_sets:
            problem_count = BasicKnowledgeItem.query.filter_by(
                text_set_id=text_set.id
            ).count()
            
            text_stats[text_set.id] = {
                'problem_count': problem_count
            }
        
        return render_template('basebuilder/category_texts.html',
                             category=category,
                             text_sets=text_sets,
                             text_stats=text_stats)
        
    except Exception as e:
        current_app.logger.error(f"Category texts error: {str(e)}")
        flash('テキスト一覧の取得中にエラーが発生しました。')
        return redirect(url_for('categories.categories'))