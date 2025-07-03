"""
BaseBuilder Module - 問題管理・学習パス管理モジュール
"""

def init_app(app):
    """アプリケーションにBaseBuilderを初期化"""
    try:
        # 方法1: routes.pyファイルから直接インポート
        import basebuilder.routes as routes_module
        if hasattr(routes_module, 'register_all_blueprints'):
            routes_module.register_all_blueprints(app)
            print("✅ BaseBuilder initialized from routes.py")
            return True
    except Exception as e:
        print(f"⚠️ Routes.py import failed: {e}")
    
    try:
        # 方法2: routes/パッケージからインポート
        from .routes import register_all_blueprints
        register_all_blueprints(app)
        print("✅ BaseBuilder initialized from routes/ package")
        return True
    except Exception as e:
        print(f"❌ Routes package import failed: {e}")
    
    print("❌ BaseBuilder initialization failed")
    return False

# エクスポート
__all__ = ['init_app']