"""
Documentation Generation System
===============================
Phase 6.3: ドキュメント生成システム

自動ドキュメント生成:
- API仕様書生成
- アーキテクチャ図生成
- ユーザーガイド生成
- 開発者ドキュメント生成
"""

import os
import ast
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import subprocess
import re

# Optional imports with fallbacks
try:
    import yaml
except ImportError:
    yaml = None

try:
    import markdown
except ImportError:
    markdown = None

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    Environment = None
    FileSystemLoader = None


@dataclass
class APIEndpoint:
    """APIエンドポイント情報"""
    path: str
    method: str
    function_name: str
    module: str
    description: str
    parameters: List[Dict[str, Any]]
    response_format: Dict[str, Any]
    auth_required: bool
    roles: List[str]


@dataclass
class Module:
    """モジュール情報"""
    name: str
    path: str
    description: str
    classes: List[str]
    functions: List[str]
    dependencies: List[str]
    line_count: int


@dataclass
class DatabaseModel:
    """データベースモデル情報"""
    name: str
    table_name: str
    fields: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    indexes: List[str]


class DocumentationGenerator:
    """包括的ドキュメント生成システム"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / "docs"
        self.output_dir.mkdir(exist_ok=True)
        
        # Jinja2環境設定（オプション）
        template_dir = self.output_dir / "templates"
        template_dir.mkdir(exist_ok=True)
        if Environment and FileSystemLoader:
            self.env = Environment(loader=FileSystemLoader(template_dir))
        else:
            self.env = None
        
        # 解析データ
        self.api_endpoints = []
        self.modules = []
        self.models = []
        self.architecture_data = {}
        
        # 除外パターン
        self.exclude_patterns = [
            '__pycache__',
            '.git',
            'venv',
            'env',
            'migrations',
            '*.pyc',
            '*.pyo',
            'test_*',
            '*_test.py'
        ]
    
    def generate_full_documentation(self) -> bool:
        """
        完全なドキュメント生成
        
        Returns:
            bool: 生成成功可否
        """
        print("📚 Starting comprehensive documentation generation...")
        
        try:
            # 1. プロジェクト分析
            self._analyze_project()
            
            # 2. API仕様書生成
            self._generate_api_documentation()
            
            # 3. アーキテクチャドキュメント生成
            self._generate_architecture_docs()
            
            # 4. ユーザーガイド生成
            self._generate_user_guides()
            
            # 5. 開発者ドキュメント生成
            self._generate_developer_docs()
            
            # 6. インデックスページ生成
            self._generate_index()
            
            # 7. 検索インデックス生成
            self._generate_search_index()
            
            print(f"✅ Documentation generated successfully in {self.output_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Documentation generation failed: {e}")
            return False
    
    def _analyze_project(self):
        """プロジェクト全体の分析"""
        print("\n🔍 Analyzing project structure...")
        
        # Python ファイル分析
        self._analyze_python_files()
        
        # APIエンドポイント分析
        self._analyze_api_endpoints()
        
        # データベースモデル分析
        self._analyze_database_models()
        
        # アーキテクチャ分析
        self._analyze_architecture()
    
    def _analyze_python_files(self):
        """Pythonファイルの分析"""
        for py_file in self._get_python_files():
            try:
                content = py_file.read_text(encoding='utf-8')
                tree = ast.parse(content)
                
                module_info = Module(
                    name=py_file.stem,
                    path=str(py_file.relative_to(self.project_root)),
                    description=self._extract_module_docstring(tree),
                    classes=self._extract_classes(tree),
                    functions=self._extract_functions(tree),
                    dependencies=self._extract_imports(tree),
                    line_count=len(content.split('\n'))
                )
                
                self.modules.append(module_info)
                
            except Exception as e:
                print(f"Warning: Could not analyze {py_file}: {e}")
    
    def _analyze_api_endpoints(self):
        """APIエンドポイントの分析"""
        # Flask ルート分析
        api_files = [
            self.project_root / "app" / "api" / "__init__.py",
            self.project_root / "app" / "teacher" / "__init__.py",
            self.project_root / "app" / "student" / "__init__.py",
            self.project_root / "basebuilder" / "routes.py"
        ]
        
        for api_file in api_files:
            if api_file.exists():
                self._extract_flask_routes(api_file)
    
    def _analyze_database_models(self):
        """データベースモデルの分析"""
        models_dir = self.project_root / "app" / "models"
        if models_dir.exists():
            for model_file in models_dir.glob("*.py"):
                if model_file.name != "__init__.py":
                    self._extract_sqlalchemy_models(model_file)
    
    def _analyze_architecture(self):
        """アーキテクチャの分析"""
        self.architecture_data = {
            'total_modules': len(self.modules),
            'total_endpoints': len(self.api_endpoints),
            'total_models': len(self.models),
            'largest_module': max(self.modules, key=lambda m: m.line_count, default=None),
            'module_dependencies': self._calculate_dependencies(),
            'service_layers': self._identify_service_layers(),
            'blueprints': self._identify_blueprints()
        }
    
    def _generate_api_documentation(self):
        """API仕様書生成"""
        print("\n📖 Generating API documentation...")
        
        # OpenAPI 仕様生成
        openapi_spec = self._generate_openapi_spec()
        
        # OpenAPI JSON保存
        with open(self.output_dir / "api-spec.json", 'w', encoding='utf-8') as f:
            json.dump(openapi_spec, f, indent=2, ensure_ascii=False)
        
        # APIドキュメントHTML生成
        api_html = self._generate_api_html()
        with open(self.output_dir / "api-documentation.html", 'w', encoding='utf-8') as f:
            f.write(api_html)
        
        # Postman コレクション生成
        postman_collection = self._generate_postman_collection()
        with open(self.output_dir / "postman-collection.json", 'w', encoding='utf-8') as f:
            json.dump(postman_collection, f, indent=2, ensure_ascii=False)
    
    def _generate_architecture_docs(self):
        """アーキテクチャドキュメント生成"""
        print("\n🏗️ Generating architecture documentation...")
        
        # アーキテクチャ概要
        arch_md = self._generate_architecture_markdown()
        with open(self.output_dir / "architecture.md", 'w', encoding='utf-8') as f:
            f.write(arch_md)
        
        # モジュール依存関係図
        self._generate_dependency_diagram()
        
        # データフロー図
        self._generate_data_flow_diagram()
        
        # システム構成図
        self._generate_system_diagram()
    
    def _generate_user_guides(self):
        """ユーザーガイド生成"""
        print("\n👥 Generating user guides...")
        
        user_types = ['admin', 'teacher', 'student']
        
        for user_type in user_types:
            guide_md = self._generate_user_guide(user_type)
            with open(self.output_dir / f"{user_type}-guide.md", 'w', encoding='utf-8') as f:
                f.write(guide_md)
            
            # HTML版も生成（markdownが利用可能な場合）
            if markdown:
                guide_html = markdown.markdown(guide_md, extensions=['tables', 'toc'])
                with open(self.output_dir / f"{user_type}-guide.html", 'w', encoding='utf-8') as f:
                    f.write(self._wrap_html(guide_html, f"{user_type.capitalize()} Guide"))
    
    def _generate_developer_docs(self):
        """開発者ドキュメント生成"""
        print("\n💻 Generating developer documentation...")
        
        # セットアップガイド
        setup_md = self._generate_setup_guide()
        with open(self.output_dir / "setup.md", 'w', encoding='utf-8') as f:
            f.write(setup_md)
        
        # コーディング規約
        coding_standards = self._generate_coding_standards()
        with open(self.output_dir / "coding-standards.md", 'w', encoding='utf-8') as f:
            f.write(coding_standards)
        
        # トラブルシューティング
        troubleshooting = self._generate_troubleshooting()
        with open(self.output_dir / "troubleshooting.md", 'w', encoding='utf-8') as f:
            f.write(troubleshooting)
        
        # デプロイメントガイド
        deployment = self._generate_deployment_guide()
        with open(self.output_dir / "deployment.md", 'w', encoding='utf-8') as f:
            f.write(deployment)
    
    def _generate_index(self):
        """インデックスページ生成"""
        print("\n🏠 Generating index page...")
        
        index_html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuestEd Documentation</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 50px; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .card h3 {{ margin-top: 0; color: #2c3e50; }}
        .card a {{ color: #3498db; text-decoration: none; }}
        .card a:hover {{ text-decoration: underline; }}
        .stats {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .stats h3 {{ margin-top: 0; }}
        .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .stat-item {{ text-align: center; }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #e74c3c; }}
        .stat-label {{ color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 QuestEd Documentation</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <h3>📊 Project Statistics</h3>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-number">{len(self.modules)}</div>
                    <div class="stat-label">Modules</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{len(self.api_endpoints)}</div>
                    <div class="stat-label">API Endpoints</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{len(self.models)}</div>
                    <div class="stat-label">Database Models</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{sum(m.line_count for m in self.modules):,}</div>
                    <div class="stat-label">Lines of Code</div>
                </div>
            </div>
        </div>
        
        <div class="cards">
            <div class="card">
                <h3>🔌 API Documentation</h3>
                <p>Complete API reference with endpoints, parameters, and examples.</p>
                <ul>
                    <li><a href="api-documentation.html">API Reference</a></li>
                    <li><a href="api-spec.json">OpenAPI Specification</a></li>
                    <li><a href="postman-collection.json">Postman Collection</a></li>
                </ul>
            </div>
            
            <div class="card">
                <h3>🏗️ Architecture</h3>
                <p>System architecture, module dependencies, and design patterns.</p>
                <ul>
                    <li><a href="architecture.md">Architecture Overview</a></li>
                    <li><a href="dependency-diagram.png">Dependency Diagram</a></li>
                    <li><a href="system-diagram.png">System Diagram</a></li>
                </ul>
            </div>
            
            <div class="card">
                <h3>👥 User Guides</h3>
                <p>Step-by-step guides for different user roles.</p>
                <ul>
                    <li><a href="admin-guide.html">Administrator Guide</a></li>
                    <li><a href="teacher-guide.html">Teacher Guide</a></li>
                    <li><a href="student-guide.html">Student Guide</a></li>
                </ul>
            </div>
            
            <div class="card">
                <h3>💻 Developer Docs</h3>
                <p>Technical documentation for developers and contributors.</p>
                <ul>
                    <li><a href="setup.md">Setup Guide</a></li>
                    <li><a href="coding-standards.md">Coding Standards</a></li>
                    <li><a href="troubleshooting.md">Troubleshooting</a></li>
                    <li><a href="deployment.md">Deployment Guide</a></li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        with open(self.output_dir / "index.html", 'w', encoding='utf-8') as f:
            f.write(index_html)
    
    def _generate_search_index(self):
        """検索インデックス生成"""
        print("\n🔍 Generating search index...")
        
        search_data = {
            'pages': [],
            'apis': [],
            'models': []
        }
        
        # ページ情報
        for doc_file in self.output_dir.glob("*.md"):
            content = doc_file.read_text(encoding='utf-8')
            search_data['pages'].append({
                'title': doc_file.stem.replace('-', ' ').title(),
                'url': doc_file.name,
                'content': content[:500] + "..." if len(content) > 500 else content
            })
        
        # API情報
        for endpoint in self.api_endpoints:
            search_data['apis'].append({
                'path': endpoint.path,
                'method': endpoint.method,
                'description': endpoint.description,
                'module': endpoint.module
            })
        
        # モデル情報
        for model in self.models:
            search_data['models'].append({
                'name': model.name,
                'table': model.table_name,
                'fields': [f['name'] for f in model.fields]
            })
        
        with open(self.output_dir / "search-index.json", 'w', encoding='utf-8') as f:
            json.dump(search_data, f, indent=2, ensure_ascii=False)
    
    def _get_python_files(self) -> List[Path]:
        """Pythonファイルのリスト取得"""
        python_files = []
        
        for pattern in ['**/*.py']:
            for file_path in self.project_root.glob(pattern):
                if not any(exclude in str(file_path) for exclude in self.exclude_patterns):
                    python_files.append(file_path)
        
        return python_files
    
    def _extract_module_docstring(self, tree: ast.AST) -> str:
        """モジュールのdocstring抽出"""
        return ast.get_docstring(tree) or "No description available"
    
    def _extract_classes(self, tree: ast.AST) -> List[str]:
        """クラス名の抽出"""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
        return classes
    
    def _extract_functions(self, tree: ast.AST) -> List[str]:
        """関数名の抽出"""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
        return functions
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """インポートの抽出"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports
    
    def _extract_flask_routes(self, file_path: Path):
        """Flask ルートの抽出"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # route デコレータのパターン
            route_pattern = r'@\w+\.route\([\'"]([^\'"]+)[\'"](?:,\s*methods=\[(.*?)\])?\)'
            function_pattern = r'def\s+(\w+)\s*\('
            
            routes = re.finditer(route_pattern, content)
            
            for match in routes:
                path = match.group(1)
                methods = match.group(2) if match.group(2) else 'GET'
                
                # 次の関数定義を探す
                start = match.end()
                func_match = re.search(function_pattern, content[start:])
                
                if func_match:
                    function_name = func_match.group(1)
                    
                    # 関数のdocstringを抽出
                    try:
                        tree = ast.parse(content)
                        description = self._find_function_docstring(tree, function_name)
                    except:
                        description = "No description available"
                    
                    endpoint = APIEndpoint(
                        path=path,
                        method=methods.replace("'", "").replace('"', ''),
                        function_name=function_name,
                        module=str(file_path.relative_to(self.project_root)),
                        description=description,
                        parameters=[],
                        response_format={},
                        auth_required=True,  # 仮定
                        roles=[]
                    )
                    
                    self.api_endpoints.append(endpoint)
        
        except Exception as e:
            print(f"Warning: Could not extract routes from {file_path}: {e}")
    
    def _find_function_docstring(self, tree: ast.AST, function_name: str) -> str:
        """指定された関数のdocstring取得"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                return ast.get_docstring(node) or "No description available"
        return "No description available"
    
    def _extract_sqlalchemy_models(self, file_path: Path):
        """SQLAlchemyモデルの抽出"""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # db.Model を継承しているかチェック
                    for base in node.bases:
                        if (isinstance(base, ast.Attribute) and 
                            isinstance(base.value, ast.Name) and 
                            base.value.id == 'db' and 
                            base.attr == 'Model'):
                            
                            model = DatabaseModel(
                                name=node.name,
                                table_name=self._extract_table_name(node),
                                fields=self._extract_model_fields(node),
                                relationships=self._extract_relationships(node),
                                indexes=[]
                            )
                            
                            self.models.append(model)
                            break
        
        except Exception as e:
            print(f"Warning: Could not extract models from {file_path}: {e}")
    
    def _extract_table_name(self, class_node: ast.ClassDef) -> str:
        """テーブル名の抽出"""
        for node in class_node.body:
            if (isinstance(node, ast.Assign) and 
                len(node.targets) == 1 and 
                isinstance(node.targets[0], ast.Name) and 
                node.targets[0].id == '__tablename__'):
                if isinstance(node.value, ast.Constant):
                    return node.value.value
        return class_node.name.lower()
    
    def _extract_model_fields(self, class_node: ast.ClassDef) -> List[Dict[str, Any]]:
        """モデルフィールドの抽出"""
        fields = []
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        field_info = {
                            'name': target.id,
                            'type': 'Unknown',
                            'nullable': True,
                            'primary_key': False
                        }
                        fields.append(field_info)
        return fields
    
    def _extract_relationships(self, class_node: ast.ClassDef) -> List[Dict[str, Any]]:
        """リレーションシップの抽出"""
        return []  # 簡易実装
    
    def _calculate_dependencies(self) -> Dict[str, List[str]]:
        """モジュール依存関係の計算"""
        dependencies = {}
        for module in self.modules:
            deps = [dep for dep in module.dependencies if dep.startswith('app.')]
            dependencies[module.name] = deps
        return dependencies
    
    def _identify_service_layers(self) -> List[str]:
        """サービス層の特定"""
        return [m.name for m in self.modules if 'service' in m.path.lower()]
    
    def _identify_blueprints(self) -> List[str]:
        """Blueprintの特定"""
        blueprints = []
        for module in self.modules:
            if any(cls.endswith('Blueprint') or 'blueprint' in cls.lower() 
                   for cls in module.classes):
                blueprints.append(module.name)
        return blueprints
    
    def _generate_openapi_spec(self) -> Dict[str, Any]:
        """OpenAPI仕様の生成"""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "QuestEd API",
                "version": "1.0.0",
                "description": "QuestEd educational platform API"
            },
            "servers": [
                {"url": "http://localhost:5000", "description": "Development server"}
            ],
            "paths": {}
        }
        
        for endpoint in self.api_endpoints:
            if endpoint.path not in spec["paths"]:
                spec["paths"][endpoint.path] = {}
            
            methods = endpoint.method.split(',') if ',' in endpoint.method else [endpoint.method]
            
            for method in methods:
                method = method.strip().lower()
                spec["paths"][endpoint.path][method] = {
                    "summary": endpoint.description,
                    "description": f"Implemented in {endpoint.module}:{endpoint.function_name}",
                    "responses": {
                        "200": {
                            "description": "Success"
                        },
                        "400": {
                            "description": "Bad Request"
                        },
                        "401": {
                            "description": "Unauthorized"
                        },
                        "500": {
                            "description": "Internal Server Error"
                        }
                    }
                }
        
        return spec
    
    def _generate_api_html(self) -> str:
        """API HTML ドキュメント生成"""
        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuestEd API Documentation</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .endpoint {{ border: 1px solid #ddd; margin-bottom: 20px; border-radius: 8px; }}
        .endpoint-header {{ background: #f8f9fa; padding: 15px; border-bottom: 1px solid #ddd; }}
        .endpoint-body {{ padding: 15px; }}
        .method {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; }}
        .get {{ background: #28a745; color: white; }}
        .post {{ background: #007bff; color: white; }}
        .put {{ background: #ffc107; color: black; }}
        .delete {{ background: #dc3545; color: white; }}
        .path {{ font-family: monospace; font-size: 1.1em; margin-left: 10px; }}
        .description {{ margin: 10px 0; }}
        .module {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔌 QuestEd API Documentation</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>📊 API Statistics</h2>
        <ul>
            <li>Total Endpoints: {len(self.api_endpoints)}</li>
            <li>Modules: {len(set(e.module for e in self.api_endpoints))}</li>
        </ul>
        
        <h2>🔗 Endpoints</h2>
        """
        
        # エンドポイントをパス順にソート
        sorted_endpoints = sorted(self.api_endpoints, key=lambda e: e.path)
        
        for endpoint in sorted_endpoints:
            methods = endpoint.method.split(',') if ',' in endpoint.method else [endpoint.method]
            
            html += f"""
        <div class="endpoint">
            <div class="endpoint-header">
                """
            
            for method in methods:
                method = method.strip().upper()
                html += f'<span class="method {method.lower()}">{method}</span>'
            
            html += f"""
                <span class="path">{endpoint.path}</span>
            </div>
            <div class="endpoint-body">
                <div class="description">{endpoint.description}</div>
                <div class="module">Module: {endpoint.module}</div>
                <div class="module">Function: {endpoint.function_name}</div>
            </div>
        </div>
            """
        
        html += """
    </div>
</body>
</html>
        """
        
        return html
    
    def _generate_postman_collection(self) -> Dict[str, Any]:
        """Postman コレクション生成"""
        collection = {
            "info": {
                "name": "QuestEd API",
                "description": "QuestEd educational platform API collection",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": []
        }
        
        for endpoint in self.api_endpoints:
            methods = endpoint.method.split(',') if ',' in endpoint.method else [endpoint.method]
            
            for method in methods:
                item = {
                    "name": f"{method.strip().upper()} {endpoint.path}",
                    "request": {
                        "method": method.strip().upper(),
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "url": {
                            "raw": f"{{{{base_url}}}}{endpoint.path}",
                            "host": ["{{base_url}}"],
                            "path": endpoint.path.strip('/').split('/')
                        },
                        "description": endpoint.description
                    }
                }
                
                collection["item"].append(item)
        
        return collection
    
    def _generate_architecture_markdown(self) -> str:
        """アーキテクチャMarkdown生成"""
        md = f"""# QuestEd System Architecture

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 System Overview

- **Total Modules**: {self.architecture_data['total_modules']}
- **API Endpoints**: {self.architecture_data['total_endpoints']}
- **Database Models**: {self.architecture_data['total_models']}
- **Lines of Code**: {sum(m.line_count for m in self.modules):,}

## 🏗️ Architecture Layers

### Presentation Layer
- Web UI (Flask Templates)
- REST API (Flask-RESTful)
- Static Assets (CSS, JavaScript)

### Business Logic Layer
- Services: {len(self.architecture_data['service_layers'])} modules
- Blueprints: {len(self.architecture_data['blueprints'])} modules
- Workflow Management

### Data Access Layer
- SQLAlchemy ORM
- Database Models: {len(self.models)} models
- Migration Management

### Infrastructure Layer
- Flask Application Factory
- Configuration Management
- Extension Integration

## 📦 Module Dependencies

"""
        
        for module, deps in self.architecture_data['module_dependencies'].items():
            if deps:
                md += f"- **{module}**: {', '.join(deps)}\n"
        
        md += f"""

## 🗃️ Database Models

"""
        
        for model in self.models:
            md += f"### {model.name}\n"
            md += f"- Table: `{model.table_name}`\n"
            md += f"- Fields: {len(model.fields)}\n"
            md += f"- Relationships: {len(model.relationships)}\n\n"
        
        return md
    
    def _generate_dependency_diagram(self):
        """依存関係図生成（PlantUML）"""
        uml = "@startuml\n"
        uml += "!theme plain\n"
        uml += "title QuestEd Module Dependencies\n\n"
        
        # モジュール定義
        for module in self.modules:
            uml += f"component {module.name}\n"
        
        uml += "\n"
        
        # 依存関係
        for module, deps in self.architecture_data['module_dependencies'].items():
            for dep in deps:
                dep_name = dep.split('.')[-1]
                uml += f"{module} --> {dep_name}\n"
        
        uml += "@enduml\n"
        
        with open(self.output_dir / "dependency-diagram.puml", 'w') as f:
            f.write(uml)
    
    def _generate_data_flow_diagram(self):
        """データフロー図生成"""
        # 簡易実装
        pass
    
    def _generate_system_diagram(self):
        """システム構成図生成"""
        # 簡易実装
        pass
    
    def _generate_user_guide(self, user_type: str) -> str:
        """ユーザーガイド生成"""
        guides = {
            'admin': self._generate_admin_guide(),
            'teacher': self._generate_teacher_guide(),
            'student': self._generate_student_guide()
        }
        
        return guides.get(user_type, "# User Guide\n\nNo guide available for this user type.")
    
    def _generate_admin_guide(self) -> str:
        """管理者ガイド生成"""
        return f"""# Administrator Guide

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📋 Overview

The QuestEd administrator interface provides comprehensive management capabilities for the educational platform.

## 🚀 Getting Started

### Initial Setup
1. Access the admin panel at `/admin`
2. Login with administrator credentials
3. Configure system settings

### User Management
- Create and manage user accounts
- Assign roles (teacher, student)
- Manage school enrollments

### System Configuration
- Configure application settings
- Manage database connections
- Monitor system performance

## 📊 Monitoring and Analytics

### System Health
- Monitor active users
- Track system performance
- Review error logs

### Usage Analytics
- View platform usage statistics
- Generate user activity reports
- Analyze learning patterns

## 🔧 Maintenance

### Database Management
- Backup and restore procedures
- Migration management
- Data integrity checks

### Security
- User access control
- Security audit procedures
- Incident response

## 📞 Support

For technical support, contact the development team.
"""
    
    def _generate_teacher_guide(self) -> str:
        """教師ガイド生成"""
        return f"""# Teacher Guide

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📋 Overview

QuestEd provides teachers with powerful tools for curriculum management, student evaluation, and learning analytics.

## 🚀 Getting Started

### Dashboard Overview
- View class summaries
- Monitor student progress
- Access quick actions

### Class Management
1. Create and configure classes
2. Enroll students
3. Assign learning materials

## 📚 Curriculum Management

### Creating Curriculums
1. Navigate to Curriculum section
2. Click "Create New Curriculum"
3. Define curriculum structure
4. Add learning objectives

### Unit Management
- Convert curriculums to units
- Manage unit sequences
- Track completion status

## 👥 Student Management

### Monitoring Progress
- View individual student progress
- Identify learning gaps
- Generate progress reports

### Approval Workflow
1. Review completion requests
2. Evaluate student work
3. Approve or request revisions

## 📊 Analytics and Reporting

### Learning Analytics
- View class performance metrics
- Analyze learning patterns
- Identify struggling students

### Report Generation
- Generate progress reports
- Export student data
- Create evaluation summaries

## 🔧 Advanced Features

### AI-Powered Features
- Curriculum generation assistance
- Automated evaluation support
- Personalized recommendations

### Integration Tools
- Real-time synchronization
- Bulk operations
- Import/export capabilities
"""
    
    def _generate_student_guide(self) -> str:
        """学生ガイド生成"""
        return f"""# Student Guide

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📋 Overview

Welcome to QuestEd! This guide will help you navigate the learning platform and make the most of your educational experience.

## 🚀 Getting Started

### First Login
1. Access QuestEd through your school's portal
2. Login with your credentials
3. Complete your profile setup

### Dashboard Overview
- View your progress
- Access assigned materials
- Check notifications

## 📚 Learning Activities

### Unit Selection
1. Browse available units
2. Select units matching your goals
3. Begin learning activities

### Progress Tracking
- Monitor completion status
- View performance metrics
- Track learning milestones

## ✅ Submitting Work

### Completion Requests
1. Complete unit requirements
2. Submit completion request
3. Await teacher approval

### Self-Assessment
- Regular progress reviews
- Identify areas for improvement
- Set learning goals

## 📊 Personal Analytics

### Progress Visualization
- View learning charts
- Track improvement over time
- Compare with class averages

### Goal Setting
- Set personal learning goals
- Track goal achievement
- Celebrate milestones

## 💬 Communication

### Teacher Interaction
- Submit questions and requests
- Receive feedback
- Schedule consultations

### Peer Collaboration
- Participate in class discussions
- Share learning experiences
- Support classmates

## 🎯 Tips for Success

### Effective Learning
- Set regular study schedules
- Use progress tracking features
- Seek help when needed

### Platform Features
- Explore all available tools
- Customize your learning experience
- Stay updated with new features
"""
    
    def _generate_setup_guide(self) -> str:
        """セットアップガイド生成"""
        return f"""# Development Setup Guide

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📋 Prerequisites

### Required Software
- Python 3.8+
- MySQL 8.0+
- Redis (for caching)
- Node.js (for frontend tools)

### Development Tools
- Git
- Virtual environment manager
- Code editor (VS Code recommended)

## 🚀 Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd quested
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\\Scripts\\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create `.env` file:
```env
SECRET_KEY=your-secret-key
DB_USERNAME=username
DB_PASSWORD=password
DB_HOST=localhost
DB_NAME=quested
OPENAI_API_KEY=your-openai-key
```

### 5. Database Setup
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 6. Run Application
```bash
python app.py
```

## 🔧 Development Workflow

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Write comprehensive docstrings

### Testing
```bash
pytest tests/
```

### Database Migrations
```bash
flask db migrate -m "Description"
flask db upgrade
```

## 📦 Project Structure

```
quested/
├── app/                 # Main application
├── basebuilder/         # Learning module
├── static/              # Static assets
├── templates/           # HTML templates
├── tests/               # Test suite
├── docs/                # Documentation
├── requirements.txt     # Dependencies
└── app.py              # Entry point
```

## 🚨 Troubleshooting

### Common Issues
- Database connection errors
- Import path problems
- Missing environment variables

### Debug Mode
Set `FLASK_DEBUG=1` for development debugging.
"""
    
    def _generate_coding_standards(self) -> str:
        """コーディング規約生成"""
        return f"""# Coding Standards

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📋 Python Standards

### PEP 8 Compliance
- Line length: 79 characters
- Indentation: 4 spaces
- Import ordering: standard, third-party, local

### Naming Conventions
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Variables: `snake_case`

### Documentation
```python
def example_function(param: str) -> bool:
    \"\"\"
    Brief description of function.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When parameter is invalid
    \"\"\"
    pass
```

## 🏗️ Architecture Standards

### Service Layer Pattern
- Separate business logic from controllers
- Use dependency injection
- Implement proper error handling

### Database Operations
```python
try:
    db.session.add(new_object)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    logger.error(f"Database error: {{e}}")
    raise
```

### API Design
- RESTful endpoints
- Consistent response formats
- Proper HTTP status codes
- Input validation

## 🧪 Testing Standards

### Test Coverage
- Minimum 80% code coverage
- Unit tests for all services
- Integration tests for APIs

### Test Structure
```python
class TestExample(unittest.TestCase):
    def setUp(self):
        # Test setup
        pass
    
    def test_example_functionality(self):
        # Arrange
        # Act
        # Assert
        pass
```

## 📱 Frontend Standards

### JavaScript
- Use ES6+ features
- Consistent error handling
- Modular code structure

### CSS
- Use utility classes
- Mobile-first responsive design
- Consistent naming conventions

## 🔒 Security Standards

### Input Validation
- Validate all user inputs
- Sanitize data before storage
- Use parameterized queries

### Authentication
- Secure password storage
- Session management
- CSRF protection

## 📝 Documentation Standards

### Code Documentation
- Comprehensive docstrings
- Inline comments for complex logic
- README files for modules

### API Documentation
- OpenAPI specifications
- Example requests/responses
- Error code documentation
"""
    
    def _generate_troubleshooting(self) -> str:
        """トラブルシューティングガイド生成"""
        return f"""# Troubleshooting Guide

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🚨 Common Issues

### Database Connection Errors

#### Error: "Access denied for user"
**Cause**: Incorrect database credentials
**Solution**:
1. Verify `.env` file settings
2. Check MySQL user permissions
3. Test connection manually

```bash
mysql -h $DB_HOST -u $DB_USERNAME -p$DB_PASSWORD $DB_NAME
```

#### Error: "Can't connect to MySQL server"
**Cause**: MySQL service not running
**Solution**:
```bash
sudo systemctl start mysql
sudo systemctl enable mysql
```

### Import Errors

#### Error: "ModuleNotFoundError"
**Cause**: Missing dependencies or incorrect Python path
**Solution**:
1. Activate virtual environment
2. Install missing packages
```bash
pip install -r requirements.txt
```

### Flask Application Errors

#### Error: "Template not found"
**Cause**: Incorrect template path
**Solution**:
1. Check template directory structure
2. Verify template file names
3. Review Flask configuration

#### Error: "500 Internal Server Error"
**Cause**: Various application errors
**Solution**:
1. Check application logs
2. Enable debug mode
3. Review recent code changes

## 🔧 Performance Issues

### Slow Page Loading
**Symptoms**: Pages take >5 seconds to load
**Solutions**:
1. Check database query performance
2. Review template complexity
3. Optimize static asset loading

### High Memory Usage
**Symptoms**: Application consuming >1GB RAM
**Solutions**:
1. Profile memory usage
2. Check for memory leaks
3. Optimize data structures

## 📊 Monitoring and Logging

### Application Logs
```bash
tail -f logs/quested.log
```

### Database Monitoring
```sql
SHOW PROCESSLIST;
SHOW STATUS LIKE 'Connections';
```

### System Resources
```bash
top -p $(pgrep -f python)
```

## 🛠️ Debug Tools

### Flask Debug Mode
```python
app.run(debug=True)
```

### Database Query Logging
```python
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Frontend Debugging
- Browser Developer Tools
- Console error messages
- Network request monitoring

## 📞 Getting Help

### Internal Resources
1. Check this documentation
2. Review code comments
3. Consult team members

### External Resources
1. Flask documentation
2. SQLAlchemy documentation
3. Stack Overflow

### Escalation Process
1. Document the issue
2. Gather relevant logs
3. Contact development team
4. Create issue ticket if needed
"""
    
    def _generate_deployment_guide(self) -> str:
        """デプロイメントガイド生成"""
        return f"""# Deployment Guide

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📋 Deployment Overview

QuestEd can be deployed in various environments using different strategies.

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DB_HOST=db
    depends_on:
      - db
      
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: quested
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

## ☁️ Cloud Deployment

### AWS Deployment
1. **EC2 Instance Setup**
   - Launch Ubuntu 20.04 instance
   - Configure security groups
   - Install required software

2. **RDS Database**
   - Create MySQL RDS instance
   - Configure security groups
   - Set up backup policies

3. **Load Balancer**
   - Configure Application Load Balancer
   - Set up health checks
   - Configure SSL certificates

### Deployment Script
```bash
#!/bin/bash
# Deploy script

# Update code
git pull origin main

# Install dependencies
pip install -r requirements.txt

# Run migrations
flask db upgrade

# Restart services
sudo systemctl restart quested
sudo systemctl restart nginx
```

## 🔒 Security Configuration

### SSL/TLS Setup
```nginx
server {{
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {{
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
```

### Environment Variables
```env
# Production settings
FLASK_ENV=production
SECRET_KEY=complex-production-secret
DB_HOST=production-db-host
REDIS_URL=redis://production-redis:6379/0
```

## 📊 Monitoring Setup

### Application Monitoring
- Set up log aggregation
- Configure error tracking
- Monitor performance metrics

### Infrastructure Monitoring
- CPU and memory usage
- Database performance
- Network connectivity

## 🔄 CI/CD Pipeline

### GitHub Actions
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to server
        run: |
          # Deployment commands
```

## 📋 Pre-deployment Checklist

### Code Quality
- [ ] All tests passing
- [ ] Code review completed
- [ ] Documentation updated

### Database
- [ ] Migrations ready
- [ ] Backup completed
- [ ] Schema validated

### Configuration
- [ ] Environment variables set
- [ ] SSL certificates configured
- [ ] Monitoring enabled

### Security
- [ ] Security scan completed
- [ ] Dependencies updated
- [ ] Access controls verified

## 🚨 Rollback Procedures

### Emergency Rollback
1. Identify issue
2. Stop current deployment
3. Restore previous version
4. Verify functionality

### Database Rollback
1. Stop application
2. Restore database backup
3. Rollback migrations if needed
4. Restart application

## 📞 Post-deployment

### Verification Steps
1. Check application status
2. Verify database connectivity
3. Test critical functionality
4. Monitor error logs

### Performance Monitoring
1. Monitor response times
2. Check resource usage
3. Verify user experience
4. Review metrics dashboard
"""
    
    def _wrap_html(self, content: str, title: str) -> str:
        """HTML ラッパー"""
        return f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - QuestEd Documentation</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    {content}
</body>
</html>
        """


def main():
    """メイン実行関数"""
    generator = DocumentationGenerator()
    success = generator.generate_full_documentation()
    
    if success:
        print(f"\n🎉 Documentation generation completed successfully!")
        print(f"📂 Output directory: {generator.output_dir}")
        print(f"🌐 Open {generator.output_dir}/index.html to view the documentation")
    else:
        print("\n❌ Documentation generation failed")


if __name__ == '__main__':
    main()