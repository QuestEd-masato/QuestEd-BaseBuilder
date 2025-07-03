"""
BaseBuilder Routes Package
Individual route modules are imported by the parent routes.py
"""

def register_all_blueprints(app):
    """すべてのBlueprintを登録 - 本番環境対応版"""
    try:
        # 各モジュールからBlueprintをインポート
        from .categories import categories_bp
        from .problems import problems_bp
        from .sessions import sessions_bp
        from .progress import progress_bp
        from .analytics import analytics_bp
        from .admin import admin_bp
        from .texts import texts_bp
        
        # メインのbasebuilder Blueprintを作成
        from flask import Blueprint
        basebuilder_bp = Blueprint('basebuilder', __name__, url_prefix='/basebuilder')
        
        @basebuilder_bp.route('/')
        def index():
            """BaseBuilder メインページ"""
            from flask import render_template, redirect, url_for
            from flask_login import current_user
            
            if current_user.role == 'student':
                return redirect(url_for('categories.categories'))
            else:
                return redirect(url_for('categories.categories'))
        
        # すべてのBlueprintを登録
        app.register_blueprint(basebuilder_bp)
        app.register_blueprint(categories_bp)
        app.register_blueprint(problems_bp)
        app.register_blueprint(sessions_bp)
        app.register_blueprint(progress_bp)
        app.register_blueprint(analytics_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(texts_bp)
        
        print("✅ All BaseBuilder blueprints registered successfully")
        
    except ImportError as e:
        print(f"❌ Blueprint import error: {str(e)}")
        # 最低限のfallback
        from flask import Blueprint
        fallback_bp = Blueprint('basebuilder_fallback', __name__, url_prefix='/basebuilder')
        
        @fallback_bp.route('/')
        @fallback_bp.route('/categories')
        def fallback():
            from flask import render_template
            return render_template('basebuilder/categories_fallback.html')
        
        app.register_blueprint(fallback_bp)
        print("⚠️ Registered fallback BaseBuilder blueprint")
    
    except Exception as e:
        print(f"❌ Blueprint registration error: {str(e)}")
        import traceback
        traceback.print_exc()