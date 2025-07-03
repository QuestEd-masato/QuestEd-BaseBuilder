#!/usr/bin/env python3
"""
Routes Debug Script - Blueprint登録状況確認
===========================================

Flaskアプリの登録済みルートを確認します。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_routes():
    """登録済みルートを確認"""
    try:
        # Flaskアプリを作成
        from app import create_app
        app = create_app()
        
        print("🔍 Flask Routes Debug")
        print("=" * 80)
        
        with app.app_context():
            print(f"📊 Total registered routes: {len(list(app.url_map.iter_rules()))}")
            print()
            
            # BaseBuilder関連のルートを抽出
            basebuilder_routes = []
            other_routes = []
            
            for rule in app.url_map.iter_rules():
                route_info = {
                    'endpoint': rule.endpoint,
                    'rule': rule.rule,
                    'methods': list(rule.methods - {'HEAD', 'OPTIONS'})
                }
                
                if 'basebuilder' in rule.rule.lower() or 'categories' in rule.endpoint:
                    basebuilder_routes.append(route_info)
                else:
                    other_routes.append(route_info)
            
            # BaseBuilderルートの表示
            print("🏗️ BaseBuilder Routes:")
            print("-" * 50)
            if basebuilder_routes:
                for route in sorted(basebuilder_routes, key=lambda x: x['rule']):
                    methods_str = ', '.join(route['methods'])
                    print(f"  {route['rule']:<30} → {route['endpoint']:<25} [{methods_str}]")
            else:
                print("  ❌ No BaseBuilder routes found!")
            
            print()
            
            # 重要なルートのチェック
            print("🎯 Critical Route Check:")
            print("-" * 50)
            critical_routes = [
                '/basebuilder/',
                '/basebuilder/categories',
                '/basebuilder/problems',
                '/basebuilder/my_texts'
            ]
            
            for target_route in critical_routes:
                found = any(rule.rule == target_route for rule in app.url_map.iter_rules())
                status = "✅ Found" if found else "❌ Missing"
                print(f"  {target_route:<25} {status}")
            
            print()
            
            # Blueprintの登録状況
            print("📋 Registered Blueprints:")
            print("-" * 50)
            for name, blueprint in app.blueprints.items():
                url_prefix = getattr(blueprint, 'url_prefix', 'None')
                print(f"  {name:<20} → url_prefix: {url_prefix}")
            
            print()
            
            # 一般的なルートサンプル（確認用）
            print("📝 Other Routes Sample (first 10):")
            print("-" * 50)
            for route in sorted(other_routes, key=lambda x: x['rule'])[:10]:
                methods_str = ', '.join(route['methods'])
                print(f"  {route['rule']:<30} → {route['endpoint']:<25} [{methods_str}]")
            
            if len(other_routes) > 10:
                print(f"  ... and {len(other_routes) - 10} more routes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_routes()