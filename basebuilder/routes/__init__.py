"""
BaseBuilder Routes Module
========================
Phase 4.1: basebuilder/routes.py の分割実装

元の巨大ファイル(3,415行)を機能別に分割し、保守性を向上させる。
元のファイルは basebuilder/routes_legacy.py として保持し、
段階的に新しい構造に移行する。
"""

from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime

from .categories import categories_bp
from .problems import problems_bp
from .sessions import sessions_bp
from .progress import progress_bp
from .analytics import analytics_bp
from .admin import admin_bp

# メインのBaseBuilderインデックス用Blueprint
basebuilder_main_bp = Blueprint('basebuilder', __name__)

@basebuilder_main_bp.route('/')
@login_required
def index():
    """BaseBuilderのトップページ - ダッシュボード機能"""
    try:
        current_app.logger.info(f"BaseBuilder index accessed by user {current_user.id}")
        
        if current_user.role == 'student':
            # 学生向けダッシュボード
            from extensions import db
            from basebuilder.models import (
                ProblemCategory, TextSet, TextDelivery, 
                ProficiencyRecord, AnswerRecord
            )
            
            today = datetime.now().date()
            
            # 学生が所属するクラスを取得
            enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
            
            # 配信されたテキストを取得
            delivered_texts = TextDelivery.query.filter(
                TextDelivery.class_id.in_(enrolled_class_ids)
            ).order_by(TextDelivery.delivered_at.desc()).limit(5).all()
            
            # カテゴリごとのテキストセットをグループ化
            categories_with_texts = {}
            for delivery in delivered_texts:
                category = delivery.text_set.category
                if category.id not in categories_with_texts:
                    categories_with_texts[category.id] = {
                        'category': category,
                        'texts': []
                    }
                categories_with_texts[category.id]['texts'].append(delivery)
            
            # 習熟度記録を取得
            proficiency_records = ProficiencyRecord.query.filter_by(
                student_id=current_user.id
            ).all()
            
            # 最近の回答記録を取得
            recent_answers = AnswerRecord.query.filter_by(
                student_id=current_user.id
            ).order_by(AnswerRecord.created_at.desc()).limit(10).all()
            
            return render_template('basebuilder/student_dashboard.html',
                                 categories_with_texts=categories_with_texts,
                                 proficiency_records=proficiency_records,
                                 recent_answers=recent_answers)
        
        elif current_user.role == 'teacher':
            # 教師向けダッシュボード
            from extensions import db
            from basebuilder.models import (
                ProblemCategory, TextSet, TextDelivery
            )
            
            # 教師が担当するクラスを取得
            teacher_classes = current_user.classes
            
            # 各クラスの統計情報を取得
            class_stats = {}
            for class_obj in teacher_classes:
                # クラスの学生数
                student_count = len(class_obj.enrolled_students)
                
                # 配信済みテキスト数
                delivered_text_count = TextDelivery.query.filter_by(
                    class_id=class_obj.id
                ).count()
                
                class_stats[class_obj.id] = {
                    'student_count': student_count,
                    'delivered_text_count': delivered_text_count
                }
            
            # カテゴリ一覧を取得
            categories = ProblemCategory.query.order_by(ProblemCategory.name).all()
            
            # テキストセット一覧を取得
            text_sets = TextSet.query.order_by(TextSet.created_at.desc()).limit(10).all()
            
            return render_template('basebuilder/teacher_dashboard.html',
                                 teacher_classes=teacher_classes,
                                 class_stats=class_stats,
                                 categories=categories,
                                 text_sets=text_sets)
        
        else:
            # 管理者向けダッシュボード
            from extensions import db
            from basebuilder.models import (
                ProblemCategory, TextSet, TextDelivery, AnswerRecord
            )
            
            # 全体統計を取得
            total_categories = ProblemCategory.query.count()
            total_text_sets = TextSet.query.count()
            total_students = db.session.query(db.func.count(db.distinct(AnswerRecord.student_id))).scalar()
            
            # 最近の活動
            recent_deliveries = TextDelivery.query.order_by(
                TextDelivery.delivered_at.desc()
            ).limit(10).all()
            
            return render_template('basebuilder/admin_dashboard.html',
                                 total_categories=total_categories,
                                 total_text_sets=total_text_sets,
                                 total_students=total_students,
                                 recent_deliveries=recent_deliveries)
        
    except Exception as e:
        current_app.logger.error(f"BaseBuilder index error: {str(e)}")
        flash('ダッシュボードの読み込み中にエラーが発生しました。')
        return redirect(url_for('index'))


def register_basebuilder_routes(app):
    """BaseBuilder関連の全ルートを登録"""
    
    # メインのベースビルダーBlueprintを登録（/basebuilder/ ルート用）
    app.register_blueprint(basebuilder_main_bp, url_prefix='/basebuilder')
    
    # 各モジュールのBlueprintを登録
    app.register_blueprint(categories_bp, url_prefix='/basebuilder')
    app.register_blueprint(problems_bp, url_prefix='/basebuilder')
    app.register_blueprint(sessions_bp, url_prefix='/basebuilder')
    app.register_blueprint(progress_bp, url_prefix='/basebuilder')
    app.register_blueprint(analytics_bp, url_prefix='/basebuilder')
    app.register_blueprint(admin_bp, url_prefix='/basebuilder')


# モジュール情報
__version__ = "2.0.0"
__description__ = "BaseBuilder Routes - Refactored for better maintainability"

# 利用可能な機能モジュールリスト
AVAILABLE_MODULES = [
    'categories',    # カテゴリ管理
    'problems',      # 問題管理
    'sessions',      # セッション管理
    'progress',      # 進捗管理
    'analytics',     # 分析・統計
    'admin'          # 管理機能
]

# リファクタリング情報
REFACTORING_INFO = {
    'original_file_size': '3,415 lines',
    'refactored_modules': len(AVAILABLE_MODULES),
    'total_routes': 47,
    'refactoring_date': '2025-06-27',
    'migration_strategy': 'gradual_with_legacy_fallback'
}