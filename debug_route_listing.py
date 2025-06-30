#!/usr/bin/env python3
"""
QuestEd Debug Route Listing Tool
================================
Phase 3 デバッグ用ルート一覧表示コマンド

使用方法:
    python debug_route_listing.py

機能:
- 全アプリケーションルートの一覧表示
- Blueprint別の分類表示
- エンドポイント名とHTTPメソッドの表示
- エラー原因特定に必要な詳細情報提供
"""

import sys
import os

# アプリケーションパスの追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from app import create_app
import logging

def list_routes():
    """全ルートをBlueprint別に表示"""
    try:
        # アプリケーション作成
        app = create_app()
        
        with app.app_context():
            print("=" * 80)
            print("QuestEd Application Routes - Debug Information")
            print("=" * 80)
            print()
            
            # ルートを Blueprint 別に分類
            blueprint_routes = {}
            
            for rule in app.url_map.iter_rules():
                endpoint = rule.endpoint
                
                # Blueprint名を取得
                if '.' in endpoint:
                    blueprint_name = endpoint.split('.')[0]
                else:
                    blueprint_name = 'main'
                
                if blueprint_name not in blueprint_routes:
                    blueprint_routes[blueprint_name] = []
                
                blueprint_routes[blueprint_name].append({
                    'rule': rule.rule,
                    'endpoint': endpoint,
                    'methods': sorted(rule.methods - {'HEAD', 'OPTIONS'})
                })
            
            # Blueprint別に表示
            for blueprint_name in sorted(blueprint_routes.keys()):
                routes = blueprint_routes[blueprint_name]
                print(f"📁 Blueprint: {blueprint_name}")
                print("-" * 50)
                
                for route in sorted(routes, key=lambda x: x['rule']):
                    methods_str = ', '.join(route['methods'])
                    print(f"  {route['rule']:<40} → {route['endpoint']:<40} [{methods_str}]")
                
                print(f"  Total routes: {len(routes)}")
                print()
            
            # 統計情報
            total_routes = sum(len(routes) for routes in blueprint_routes.values())
            print("=" * 80)
            print(f"Total Blueprints: {len(blueprint_routes)}")
            print(f"Total Routes: {total_routes}")
            print("=" * 80)
            
            # Phase 3で修正されたエンドポイントの確認
            print("\n🔍 Phase 3 Modified Endpoints Check:")
            print("-" * 50)
            
            # 修正対象のエンドポイントを確認
            target_endpoints = [
                'teacher_class_management.create_class',
                'teacher_synchronization.integrated_management',
                'student_dashboard.dashboard',
                'student_activities.activities',
                'analytics.analysis',
                'problems.create_problem',
                'categories.categories',
            ]
            
            for endpoint in target_endpoints:
                found = False
                for blueprint_name, routes in blueprint_routes.items():
                    for route in routes:
                        if route['endpoint'] == endpoint:
                            print(f"  ✅ {endpoint} - Found")
                            found = True
                            break
                    if found:
                        break
                
                if not found:
                    print(f"  ❌ {endpoint} - NOT FOUND")
            
            print()
            
    except Exception as e:
        print(f"Error listing routes: {e}")
        print("Make sure you're running this from the QuestEd project directory")
        print("and that all dependencies are installed.")
        return False
    
    return True

def main():
    """メイン関数"""
    print("Loading QuestEd application routes...")
    
    # ログレベルを設定してノイズを削減
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    success = list_routes()
    
    if success:
        print("\n✅ Route listing completed successfully!")
        print("\nUsage for debugging endpoint errors:")
        print("1. Find the correct endpoint name in the list above")
        print("2. Check that templates use the exact endpoint name shown")
        print("3. Verify Blueprint registration in the respective __init__.py files")
    else:
        print("\n❌ Route listing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()