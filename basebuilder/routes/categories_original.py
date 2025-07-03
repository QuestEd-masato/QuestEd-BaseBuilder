"""
BaseBuilder Categories Routes
============================
カテゴリ管理に関するルートハンドラ

移行元: basebuilder/routes.py の以下のルート:
- /categories (GET)
- /category/create (GET, POST)
- /category/<int:category_id>/edit (GET, POST)
- /category/<int:category_id>/delete (POST)
- /category/<int:category_id>/texts (GET)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime

from extensions import db
from basebuilder.models import ProblemCategory, BasicKnowledgeItem, TextSet
from basebuilder.utils import require_roles, handle_db_error, get_category_statistics, log_activity
from basebuilder.services import CategoryService

categories_bp = Blueprint('categories', __name__, url_prefix='/basebuilder')


@categories_bp.route('/categories')
@login_required
@require_roles('admin', 'teacher', 'student')  # 権限チェック追加
@handle_db_error("カテゴリ一覧取得")  # エラーハンドリング強化
def categories():
    """カテゴリ一覧表示
    
    Returns:
        カテゴリ一覧画面のHTMLレスポンス
    """
    # アクティビティログ記録
    log_activity("category_list_view", "Categories list accessed")
    
    # サービス層を使用して統計情報付きカテゴリを取得
    category_data = CategoryService.get_all_with_stats()
    
    # テンプレート用にデータを整形
    categories = []
    category_stats = {}
    
    for data in category_data:
        category = data['category']
        categories.append(category)
        category_stats[category.id] = {
            'problem_count': data['problem_count'],
            'text_count': data['text_count'],
            'usage_count': data['usage_count']  # 使用回数も追加
        }
    
    return render_template('basebuilder/categories.html', 
                         categories=categories,
                         category_stats=category_stats)


@categories_bp.route('/category/create', methods=['GET', 'POST'])
@login_required
@require_roles('admin', 'teacher')  # 権限チェックをデコレータに統一
@handle_db_error("カテゴリ作成")
def create_category():
    """カテゴリ作成
    
    Returns:
        GET: カテゴリ作成フォーム
        POST: カテゴリ作成処理後のリダイレクト
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        subject = request.form.get('subject', '').strip()
        grade_level = request.form.get('grade_level', type=int)
        difficulty_level = request.form.get('difficulty_level', type=int)
        
        # 入力値検証
        if not name:
            flash('カテゴリ名を入力してください。', 'error')
            return render_template('basebuilder/create_category.html')
        
        # 同名カテゴリの重複チェック
        existing_category = ProblemCategory.query.filter_by(name=name).first()
        if existing_category:
            flash('同じ名前のカテゴリが既に存在します。', 'error')
            return render_template('basebuilder/create_category.html')
        
        # 新しいカテゴリを作成（既存のロジックを保持）
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
        log_activity("category_created", f"Category '{name}' created")
        
        flash(f'カテゴリ「{name}」を作成しました。', 'success')
        return redirect(url_for('categories.categories'))
    
    return render_template('basebuilder/create_category.html')


@categories_bp.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@require_roles('admin', 'teacher')
@handle_db_error("カテゴリ編集")
def edit_category(category_id):
    """カテゴリ編集
    
    Args:
        category_id: 編集対象のカテゴリID
        
    Returns:
        GET: カテゴリ編集フォーム
        POST: カテゴリ更新処理後のリダイレクト
    """
    category = ProblemCategory.query.get_or_404(category_id)
    
    # 作成者または管理者のみ編集可能
    if current_user.role != 'admin' and category.created_by != current_user.id:
        flash('このカテゴリを編集する権限がありません。')
        return redirect(url_for('categories.categories'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        # 入力値検証
        if not name:
            flash('カテゴリ名を入力してください。', 'error')
            return render_template('basebuilder/edit_category.html', category=category)
        
        # 同名カテゴリの重複チェック（自分以外）
        existing_category = ProblemCategory.query.filter(
            ProblemCategory.name == name,
            ProblemCategory.id != category_id
        ).first()
        
        if existing_category:
            flash('同じ名前のカテゴリが既に存在します。', 'error')
            return render_template('basebuilder/edit_category.html', category=category)
        
        # サービス層を使用してカテゴリ更新
        updated_category = CategoryService.update_category(
            category_id=category_id,
            name=name,
            description=description
        )
        
        if updated_category:
            log_activity("category_updated", f"Category '{name}' updated")
            flash(f'カテゴリ「{name}」を更新しました。', 'success')
            return redirect(url_for('categories.categories'))
        else:
            flash('カテゴリの更新に失敗しました。', 'error')
    
    return render_template('basebuilder/edit_category.html', category=category)


@categories_bp.route('/category/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    """カテゴリ削除"""
    try:
        if current_user.role not in ['admin', 'teacher']:
            flash('カテゴリの削除権限がありません。')
            return redirect(url_for('categories.categories'))
        
        category = ProblemCategory.query.get_or_404(category_id)
        
        # 作成者または管理者のみ削除可能
        if current_user.role != 'admin' and category.created_by != current_user.id:
            flash('このカテゴリを削除する権限がありません。')
            return redirect(url_for('categories.categories'))
        
        # 関連する問題の存在チェック
        problem_count = BasicKnowledgeItem.query.filter_by(category_id=category_id).count()
        text_count = TextSet.query.filter_by(category_id=category_id).count()
        
        if problem_count > 0 or text_count > 0:
            flash(f'このカテゴリには{problem_count}個の問題と{text_count}個のテキストが含まれているため削除できません。')
            return redirect(url_for('categories.categories'))
        
        category_name = category.name
        
        try:
            db.session.delete(category)
            db.session.commit()
            
            current_app.logger.info(f"Category deleted: {category_name} by user {current_user.id}")
            flash(f'カテゴリ「{category_name}」を削除しました。', 'success')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Category deletion error: {str(e)}")
            flash('カテゴリの削除に失敗しました。', 'error')
        
        return redirect(url_for('categories.categories'))
        
    except Exception as e:
        current_app.logger.error(f"Delete category error: {str(e)}")
        flash('カテゴリ削除中にエラーが発生しました。')
        return redirect(url_for('categories.categories'))


@categories_bp.route('/category/<int:category_id>/texts')
@login_required
def category_texts(category_id):
    """カテゴリ内のテキスト一覧"""
    try:
        category = ProblemCategory.query.get_or_404(category_id)
        
        # カテゴリ内のテキストセットを取得
        text_sets = TextSet.query.filter_by(
            category_id=category_id
        ).order_by(TextSet.created_at.desc()).all()
        
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