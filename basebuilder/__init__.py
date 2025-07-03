"""
BaseBuilder Module - 問題管理・学習パス管理モジュール
"""

def init_app(app):
    """アプリケーションにBaseBuilderを初期化"""
    try:
        # routes.pyファイルから直接インポート（本番環境）
        import basebuilder.routes as routes_module
        if hasattr(routes_module, 'register_all_blueprints'):
            routes_module.register_all_blueprints(app)
            print("✅ BaseBuilder initialized from routes.py")
            return True
    except Exception as e:
        print(f"❌ BaseBuilder routes.py import failed: {e}")
    
    print("❌ BaseBuilder initialization failed")
    return False

# エクスポート
__all__ = ['init_app']