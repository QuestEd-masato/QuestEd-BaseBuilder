"""
BaseBuilder Categories Routes - Simplified Version
==================================================
最小限の依存関係でカテゴリ管理機能を提供
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime

categories_bp = Blueprint('categories', __name__, url_prefix='/basebuilder')

@categories_bp.route('/categories')
@login_required
def categories():
    """カテゴリ一覧表示 - 簡素化版"""
    try:
        from extensions import db
        from basebuilder.models import ProblemCategory
        
        # 基本的なカテゴリ一覧取得
        categories = ProblemCategory.query.order_by(ProblemCategory.name).all()
        
        # 統計情報は一旦空で
        category_stats = {}
        for category in categories:
            category_stats[category.id] = {
                'problem_count': 0,
                'text_count': 0,
                'usage_count': 0
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
            
            if not name:
                flash('カテゴリ名を入力してください。', 'error')
                return render_template('basebuilder/create_category.html')
            
            # 重複チェック
            existing_category = ProblemCategory.query.filter_by(name=name).first()
            if existing_category:
                flash('同じ名前のカテゴリが既に存在します。', 'error')
                return render_template('basebuilder/create_category.html')
            
            # 新しいカテゴリを作成
            new_category = ProblemCategory(
                name=name,
                description=description,
                created_by=current_user.id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_category)
            db.session.commit()
            
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
            
            # 更新
            category.name = name
            category.description = description
            category.updated_at = datetime.utcnow()
            
            db.session.commit()
            
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
        
        flash(f'カテゴリ「{category_name}」を削除しました。', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Delete category error: {str(e)}")
        flash('カテゴリ削除中にエラーが発生しました。')
    
    return redirect(url_for('categories.categories'))