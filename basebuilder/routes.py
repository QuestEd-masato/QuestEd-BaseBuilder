"""
BaseBuilder Routes - Central Blueprint Registration
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

# 各モジュールからBlueprintをインポート
from .routes.categories import categories_bp
from .routes.problems import problems_bp
from .routes.sessions import sessions_bp
from .routes.progress import progress_bp
from .routes.analytics import analytics_bp
from .routes.admin import admin_bp
from .routes.texts import texts_bp

# メインのbasebuilder Blueprint
basebuilder_bp = Blueprint('basebuilder', __name__, url_prefix='/basebuilder')

@basebuilder_bp.route('/')
@login_required
def index():
    """BaseBuilder メインページ - ダッシュボード機能"""
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
        print(f"BaseBuilder index error: {str(e)}")
        # フォールバック: シンプルなリダイレクト
        if current_user.role == 'student':
            return redirect(url_for('problems.problems'))
        else:
            return redirect(url_for('categories.categories'))

def register_all_blueprints(app):
    """すべてのBlueprintを登録"""
    try:
        print("🔄 Starting BaseBuilder blueprint registration...")
        
        # メインBlueprint
        print("  📝 Registering main basebuilder_bp...")
        app.register_blueprint(basebuilder_bp)
        print("  ✅ basebuilder_bp registered")
        
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
                print(f"  📝 Registering {name}...")
                app.register_blueprint(blueprint)
                print(f"  ✅ {name} registered")
            except Exception as e:
                print(f"  ❌ Failed to register {name}: {str(e)}")
                raise e
        
        print("✅ All BaseBuilder blueprints registered successfully")
        
    except Exception as e:
        print(f"❌ Blueprint registration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e