"""
BaseBuilder Routes - Central Blueprint Registration
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

# 各モジュールからBlueprintをインポート
from .routes_modules.categories import categories_bp
from .routes_modules.problems import problems_bp
from .routes_modules.sessions import sessions_bp
from .routes_modules.progress import progress_bp
from .routes_modules.analytics import analytics_bp
from .routes_modules.admin import admin_bp
from .routes_modules.texts import texts_bp

# メインのbasebuilder Blueprint
basebuilder_bp = Blueprint('basebuilder', __name__, url_prefix='/basebuilder')

@basebuilder_bp.route('/')
@login_required
def index():
    """BaseBuilder メインページ - 統一ホームページ"""
    try:
        from extensions import db
        from basebuilder.models import (
            ProblemCategory, TextSet, BasicKnowledgeItem, 
            AnswerRecord
        )
        
        # 統計情報を取得
        stats = {
            'total_categories': ProblemCategory.query.count(),
            'total_problems': BasicKnowledgeItem.query.count(),
            'total_texts': TextSet.query.count(),
            'total_sessions': AnswerRecord.query.with_entities(
                AnswerRecord.student_id
            ).distinct().count()
        }
        
        return render_template('basebuilder/index.html', stats=stats)
        
    except Exception as e:
        print(f"BaseBuilder index error: {str(e)}")
        # フォールバック: カテゴリページにリダイレクト
        return redirect(url_for('categories.categories'))


@basebuilder_bp.route('/dashboard')
@login_required
def dashboard():
    """BaseBuilder ダッシュボード - 役割別ダッシュボード機能"""
    try:
        from extensions import db
        from basebuilder.models import (
            ProblemCategory, TextSet, TextDelivery, 
            ProficiencyRecord, AnswerRecord
        )
        from datetime import datetime
        
        if current_user.role == 'student':
            # 学生向けダッシュボード
            enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
            
            delivered_texts = TextDelivery.query.filter(
                TextDelivery.class_id.in_(enrolled_class_ids)
            ).order_by(TextDelivery.delivered_at.desc()).limit(5).all()
            
            categories_with_texts = {}
            for delivery in delivered_texts:
                category = delivery.text_set.category
                if category.id not in categories_with_texts:
                    categories_with_texts[category.id] = {
                        'category': category,
                        'texts': []
                    }
                categories_with_texts[category.id]['texts'].append(delivery)
            
            proficiency_records = ProficiencyRecord.query.filter_by(
                student_id=current_user.id
            ).all()
            
            recent_answers = AnswerRecord.query.filter_by(
                student_id=current_user.id
            ).order_by(AnswerRecord.created_at.desc()).limit(10).all()
            
            return render_template('basebuilder/student_dashboard.html',
                                 categories_with_texts=categories_with_texts,
                                 proficiency_records=proficiency_records,
                                 recent_answers=recent_answers)
        
        elif current_user.role == 'teacher':
            # 教師向けダッシュボード
            teacher_classes = current_user.classes
            
            class_stats = {}
            for class_obj in teacher_classes:
                student_count = len(class_obj.enrolled_students)
                delivered_text_count = TextDelivery.query.filter_by(
                    class_id=class_obj.id
                ).count()
                
                class_stats[class_obj.id] = {
                    'student_count': student_count,
                    'delivered_text_count': delivered_text_count
                }
            
            categories = ProblemCategory.query.order_by(ProblemCategory.name).all()
            text_sets = TextSet.query.order_by(TextSet.created_at.desc()).limit(10).all()
            
            return render_template('basebuilder/teacher_dashboard.html',
                                 teacher_classes=teacher_classes,
                                 class_stats=class_stats,
                                 categories=categories,
                                 text_sets=text_sets)
        
        else:
            # 管理者向けダッシュボード
            total_categories = ProblemCategory.query.count()
            total_text_sets = TextSet.query.count()
            total_students = db.session.query(db.func.count(db.distinct(AnswerRecord.student_id))).scalar()
            
            recent_deliveries = TextDelivery.query.order_by(
                TextDelivery.delivered_at.desc()
            ).limit(10).all()
            
            return render_template('basebuilder/admin_dashboard.html',
                                 total_categories=total_categories,
                                 total_text_sets=total_text_sets,
                                 total_students=total_students,
                                 recent_deliveries=recent_deliveries)
        
    except Exception as e:
        print(f"BaseBuilder dashboard error: {str(e)}")
        # フォールバック: シンプルなリダイレクト
        if current_user.role == 'student':
            return redirect(url_for('problems.problems'))
        else:
            return redirect(url_for('categories.categories'))

def register_all_blueprints(app):
    """すべてのBlueprintを登録"""
    try:
        print("[INFO] Starting BaseBuilder blueprint registration...")
        
        # メインBlueprint
        print("  [INFO] Registering main basebuilder_bp...")
        app.register_blueprint(basebuilder_bp)
        print("  [SUCCESS] basebuilder_bp registered")
        
        # サブBlueprints（url_prefixは各Blueprintで定義済み）
        blueprints = [
            ('categories_bp', categories_bp),
            ('problems_bp', problems_bp),
            ('sessions_bp', sessions_bp),
            ('progress_bp', progress_bp),
            ('analytics_bp', analytics_bp),
            ('admin_bp', admin_bp),
            ('texts_bp', texts_bp)
        ]
        
        for name, blueprint in blueprints:
            try:
                print(f"  [INFO] Registering {name}...")
                app.register_blueprint(blueprint)
                print(f"  [SUCCESS] {name} registered")
            except Exception as e:
                print(f"  [ERROR] Failed to register {name}: {str(e)}")
                raise e
        
        print("[SUCCESS] All BaseBuilder blueprints registered successfully")
        
    except Exception as e:
        print(f"[ERROR] Blueprint registration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e