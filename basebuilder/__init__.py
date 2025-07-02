"""
BaseBuilder Module - 問題管理・学習パス管理モジュール
"""

def init_app(app):
    """アプリケーションにBaseBuilderを初期化"""
    # routes.pyからすべてのBlueprintをインポートして登録
    from .routes import register_all_blueprints
    register_all_blueprints(app)
    
    print("✅ BaseBuilder initialized successfully")
    return True

# エクスポート
__all__ = ['init_app']