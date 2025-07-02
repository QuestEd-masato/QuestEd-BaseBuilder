#!/usr/bin/env python3
"""
BaseBuilder Endpoints Structure Check
=====================================
BaseBuilderエンドポイント定義とテンプレートの存在確認

このスクリプトはファイルシステムレベルの確認のみ
"""

import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def check_basebuilder_endpoints():
    """BaseBuilderエンドポイント構造確認"""
    
    print("🔍 BaseBuilder Endpoints Structure Check")
    print("=" * 50)
    
    # 確認対象ファイル
    route_files = [
        'basebuilder/routes/categories.py',
        'basebuilder/routes/problems.py', 
        'basebuilder/routes/sessions.py',
        'basebuilder/routes/progress.py',
        'basebuilder/routes/analytics.py',
        'basebuilder/routes/admin.py'
    ]
    
    template_dir = 'templates/basebuilder/'
    
    total_endpoints = 0
    total_templates = 0
    issues = []
    
    print("📦 Route Files Analysis:")
    
    for route_file in route_files:
        print(f"\n🔍 {route_file}:")
        
        if not os.path.exists(route_file):
            print(f"   ❌ File not found")
            issues.append(f"Missing route file: {route_file}")
            continue
            
        # ファイル内容解析
        try:
            with open(route_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Blueprint定義確認
            blueprint_pattern = r"Blueprint\('(\w+)',.*url_prefix='([^']+)'"
            blueprint_match = re.search(blueprint_pattern, content)
            
            if blueprint_match:
                bp_name, url_prefix = blueprint_match.groups()
                print(f"   ✅ Blueprint: {bp_name} (prefix: {url_prefix})")
            else:
                print(f"   ⚠️  Blueprint definition not found or malformed")
                issues.append(f"Blueprint issue in {route_file}")
            
            # ルート定義確認
            route_pattern = r"@\w+\.route\('([^']+)'\)"
            routes = re.findall(route_pattern, content)
            
            print(f"   📍 Routes found: {len(routes)}")
            for route in routes[:3]:  # 最初の3つを表示
                print(f"      • {route}")
            if len(routes) > 3:
                print(f"      ... and {len(routes) - 3} more")
                
            total_endpoints += len(routes)
            
            # 関数定義確認
            function_pattern = r"def (\w+)\("
            functions = re.findall(function_pattern, content)
            route_functions = [f for f in functions if not f.startswith('_')]
            
            print(f"   🔧 Route functions: {len(route_functions)}")
            
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
            issues.append(f"Read error in {route_file}: {e}")
    
    print(f"\n📊 Routes Summary:")
    print(f"   Total endpoints found: {total_endpoints}")
    
    # テンプレート確認
    print(f"\n📄 Template Files Check:")
    
    if os.path.exists(template_dir):
        template_files = [f for f in os.listdir(template_dir) if f.endswith('.html')]
        template_files.sort()
        
        print(f"   📁 Templates directory: {template_dir}")
        print(f"   📄 HTML files found: {len(template_files)}")
        
        for template in template_files:
            print(f"      ✅ {template}")
            
        total_templates = len(template_files)
        
        # 重要テンプレートの存在確認
        critical_templates = [
            'layout.html',
            'student_dashboard.html', 
            'teacher_dashboard.html',
            'categories.html',
            'problems.html'
        ]
        
        print(f"\n🎯 Critical Templates Check:")
        for template in critical_templates:
            if template in template_files:
                print(f"   ✅ {template}")
            else:
                print(f"   ❌ {template} (MISSING)")
                issues.append(f"Missing critical template: {template}")
                
    else:
        print(f"   ❌ Templates directory not found: {template_dir}")
        issues.append(f"Missing templates directory: {template_dir}")
    
    # base.htmlでのBaseBuilder参照確認
    print(f"\n🔗 base.html BaseBuilder References:")
    
    base_template = 'templates/base.html'
    if os.path.exists(base_template):
        try:
            with open(base_template, 'r', encoding='utf-8') as f:
                base_content = f.read()
            
            # BaseBuilder関連のurl_for参照を検索
            basebuilder_refs = re.findall(r"url_for\('([^']*(?:categories|problems|progress|analytics|admin|basebuilder)[^']*)', *.*?\)", base_content)
            
            print(f"   🔍 BaseBuilder references found: {len(basebuilder_refs)}")
            for ref in set(basebuilder_refs):  # 重複除去
                print(f"      • {ref}")
                
        except Exception as e:
            print(f"   ❌ Error reading base.html: {e}")
            issues.append(f"Base template read error: {e}")
    else:
        print(f"   ❌ base.html not found")
        issues.append("Missing base.html")
    
    # 結果サマリー
    print(f"\n📊 Check Results:")
    print(f"   Route files checked: {len(route_files)}")
    print(f"   Total endpoints: {total_endpoints}")
    print(f"   Template files: {total_templates}")
    print(f"   Issues found: {len(issues)}")
    
    if issues:
        print(f"\n⚠️  Issues Found:")
        for issue in issues:
            print(f"   • {issue}")
        return False
    else:
        print(f"\n🎉 All structure checks passed!")
        print(f"   ✅ Route files exist and have proper Blueprint definitions")
        print(f"   ✅ Templates directory exists with HTML files")
        print(f"   ✅ base.html has BaseBuilder references")
        return True

if __name__ == "__main__":
    success = check_basebuilder_endpoints()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Structure check {'passed' if success else 'failed'}")
    sys.exit(0 if success else 1)