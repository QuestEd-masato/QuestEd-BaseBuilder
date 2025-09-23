"""
Configuration package for QuestEd
多角的調査による config/ ディレクトリの Python パッケージ化

Phase 1 緊急修正: Import error解決
循環インポート回避のため、ルートconfig.pyのコードを直接実行
"""

import os
import importlib.util
import sys

def get_config():
    """ルートconfig.pyのget_config関数をプロキシ"""
    # ルートディレクトリのconfig.pyを直接ロード
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
    spec = importlib.util.spec_from_file_location("root_config", config_path)
    root_config = importlib.util.module_from_spec(spec)

    # モジュールを実行
    spec.loader.exec_module(root_config)

    # get_config関数を返す
    return root_config.get_config()

# 互換性のため、直接Config classesも提供
def Config():
    """Config base class proxy"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
    spec = importlib.util.spec_from_file_location("root_config", config_path)
    root_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(root_config)
    return root_config.Config

def DevelopmentConfig():
    """DevelopmentConfig proxy"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
    spec = importlib.util.spec_from_file_location("root_config", config_path)
    root_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(root_config)
    return root_config.DevelopmentConfig

def ProductionConfig():
    """ProductionConfig proxy"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
    spec = importlib.util.spec_from_file_location("root_config", config_path)
    root_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(root_config)
    return root_config.ProductionConfig

def TestingConfig():
    """TestingConfig proxy"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
    spec = importlib.util.spec_from_file_location("root_config", config_path)
    root_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(root_config)
    return root_config.TestingConfig