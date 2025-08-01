"""
Quality Check Tool
==================
Phase 6.2: 自動品質チェックツール

統合品質チェック:
- コード規約チェック
- セキュリティ脆弱性スキャン
- パフォーマンス分析
- 重複コード検出
- テストカバレッジ測定
"""

import os
import sys
import json
import ast
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class QualityReport:
    """品質レポートデータクラス"""
    timestamp: str
    total_files: int
    total_lines: int
    code_style_issues: int
    security_vulnerabilities: int
    duplicate_code_blocks: int
    test_coverage: float
    performance_issues: int
    overall_score: float
    details: Dict[str, Any]


class QualityChecker:
    """統合品質チェッカー"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.results = {}
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
    
    def run_full_check(self) -> QualityReport:
        """
        完全な品質チェックを実行
        
        Returns:
            QualityReport: 品質レポート
        """
        print("🔍 Starting comprehensive quality check...")
        
        # 各種チェック実行
        self.results['code_style'] = self._check_code_style()
        self.results['security'] = self._check_security()
        self.results['duplicates'] = self._check_duplicates()
        self.results['complexity'] = self._check_complexity()
        self.results['imports'] = self._check_imports()
        self.results['docstrings'] = self._check_docstrings()
        self.results['test_coverage'] = self._check_test_coverage()
        
        # レポート生成
        report = self._generate_report()
        
        # レポート保存
        self._save_report(report)
        
        # サマリー表示
        self._display_summary(report)
        
        return report
    
    def _check_code_style(self) -> Dict[str, Any]:
        """コードスタイルチェック（PEP8準拠）"""
        print("\n📏 Checking code style...")
        
        issues = []
        total_files = 0
        
        for py_file in self._get_python_files():
            total_files += 1
            file_issues = self._analyze_file_style(py_file)
            if file_issues:
                issues.extend(file_issues)
        
        return {
            'total_files': total_files,
            'total_issues': len(issues),
            'issues': issues[:50]  # 最初の50件のみ
        }
    
    def _check_security(self) -> Dict[str, Any]:
        """セキュリティ脆弱性チェック"""
        print("\n🔒 Checking security vulnerabilities...")
        
        vulnerabilities = []
        
        # 一般的なセキュリティパターンチェック
        security_patterns = [
            ('eval(', 'Dangerous use of eval()'),
            ('exec(', 'Dangerous use of exec()'),
            ('__import__', 'Dynamic import detected'),
            ('pickle.loads', 'Unsafe deserialization'),
            ('yaml.load(', 'Unsafe YAML loading'),
            ('shell=True', 'Shell injection risk'),
            ('verify=False', 'SSL verification disabled'),
            ('debug=True', 'Debug mode enabled in production')
        ]
        
        for py_file in self._get_python_files():
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            
            for pattern, description in security_patterns:
                if pattern in content:
                    vulnerabilities.append({
                        'file': str(py_file.relative_to(self.project_root)),
                        'pattern': pattern,
                        'description': description,
                        'severity': 'high' if pattern in ['eval(', 'exec('] else 'medium'
                    })
        
        return {
            'total_vulnerabilities': len(vulnerabilities),
            'high_severity': len([v for v in vulnerabilities if v['severity'] == 'high']),
            'vulnerabilities': vulnerabilities
        }
    
    def _check_duplicates(self) -> Dict[str, Any]:
        """重複コード検出"""
        print("\n🔄 Checking code duplication...")
        
        # 簡易的な重複検出（実際はより高度なアルゴリズムを使用）
        function_signatures = {}
        duplicates = []
        
        for py_file in self._get_python_files():
            try:
                tree = ast.parse(py_file.read_text())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        signature = f"{node.name}({len(node.args.args)})"
                        
                        if signature in function_signatures:
                            duplicates.append({
                                'function': node.name,
                                'file1': function_signatures[signature],
                                'file2': str(py_file.relative_to(self.project_root)),
                                'type': 'possible_duplicate_function'
                            })
                        else:
                            function_signatures[signature] = str(py_file.relative_to(self.project_root))
                            
            except Exception:
                pass
        
        return {
            'total_duplicates': len(duplicates),
            'duplicates': duplicates
        }
    
    def _check_complexity(self) -> Dict[str, Any]:
        """循環的複雑度チェック"""
        print("\n🧩 Checking code complexity...")
        
        complex_functions = []
        
        for py_file in self._get_python_files():
            try:
                tree = ast.parse(py_file.read_text())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        complexity = self._calculate_complexity(node)
                        
                        if complexity > 10:  # McCabe複雑度の閾値
                            complex_functions.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'function': node.name,
                                'complexity': complexity,
                                'recommendation': 'Consider refactoring this function'
                            })
                            
            except Exception:
                pass
        
        return {
            'total_complex_functions': len(complex_functions),
            'functions': sorted(complex_functions, key=lambda x: x['complexity'], reverse=True)[:20]
        }
    
    def _check_imports(self) -> Dict[str, Any]:
        """インポート整合性チェック"""
        print("\n📦 Checking imports...")
        
        import_issues = []
        circular_imports = []
        
        # 簡易的なインポートチェック
        for py_file in self._get_python_files():
            try:
                content = py_file.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    # 未使用インポートの検出（簡易版）
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        module_name = self._extract_module_name(line)
                        if module_name and module_name not in content[i+1:]:
                            import_issues.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': i + 1,
                                'issue': f'Possibly unused import: {module_name}'
                            })
                            
            except Exception:
                pass
        
        return {
            'total_issues': len(import_issues),
            'circular_imports': len(circular_imports),
            'issues': import_issues[:30]
        }
    
    def _check_docstrings(self) -> Dict[str, Any]:
        """ドキュメント文字列チェック"""
        print("\n📝 Checking documentation...")
        
        missing_docstrings = []
        total_functions = 0
        documented_functions = 0
        
        for py_file in self._get_python_files():
            try:
                tree = ast.parse(py_file.read_text())
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        total_functions += 1
                        
                        # ドキュメント文字列の存在チェック
                        if ast.get_docstring(node):
                            documented_functions += 1
                        else:
                            missing_docstrings.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'name': node.name,
                                'type': 'function' if isinstance(node, ast.FunctionDef) else 'class'
                            })
                            
            except Exception:
                pass
        
        coverage = (documented_functions / total_functions * 100) if total_functions > 0 else 0
        
        return {
            'total_items': total_functions,
            'documented_items': documented_functions,
            'documentation_coverage': coverage,
            'missing_docstrings': missing_docstrings[:30]
        }
    
    def _check_test_coverage(self) -> Dict[str, Any]:
        """テストカバレッジ測定"""
        print("\n🧪 Checking test coverage...")
        
        # pytest-covがインストールされている場合は実行
        try:
            result = subprocess.run(
                ['pytest', '--cov=app', '--cov-report=json', '--quiet'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and os.path.exists('coverage.json'):
                with open('coverage.json', 'r') as f:
                    coverage_data = json.load(f)
                
                return {
                    'overall_coverage': coverage_data.get('totals', {}).get('percent_covered', 0),
                    'files_tested': coverage_data.get('totals', {}).get('num_statements', 0),
                    'status': 'success'
                }
        except:
            pass
        
        return {
            'overall_coverage': 0,
            'files_tested': 0,
            'status': 'not_available'
        }
    
    def _get_python_files(self) -> List[Path]:
        """Pythonファイルのリストを取得"""
        python_files = []
        
        for pattern in ['**/*.py']:
            for file_path in self.project_root.glob(pattern):
                # 除外パターンチェック
                if not any(exclude in str(file_path) for exclude in self.exclude_patterns):
                    python_files.append(file_path)
        
        return python_files
    
    def _analyze_file_style(self, file_path: Path) -> List[Dict]:
        """ファイルのスタイル分析"""
        issues = []
        
        try:
            content = file_path.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                # 行の長さチェック（PEP8: 79文字）
                if len(line) > 79:
                    issues.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'line': i + 1,
                        'issue': f'Line too long ({len(line)} > 79 characters)',
                        'severity': 'low'
                    })
                
                # タブ文字チェック
                if '\t' in line:
                    issues.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'line': i + 1,
                        'issue': 'Tab character found (use spaces)',
                        'severity': 'medium'
                    })
                    
        except Exception:
            pass
        
        return issues
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """McCabe循環的複雑度の計算"""
        complexity = 1  # 基本複雑度
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
                
        return complexity
    
    def _extract_module_name(self, import_line: str) -> Optional[str]:
        """インポート文からモジュール名を抽出"""
        parts = import_line.strip().split()
        
        if parts[0] == 'import' and len(parts) > 1:
            return parts[1].split('.')[0]
        elif parts[0] == 'from' and len(parts) > 2:
            return parts[1].split('.')[0]
        
        return None
    
    def _generate_report(self) -> QualityReport:
        """品質レポート生成"""
        # スコア計算
        style_score = max(0, 100 - self.results['code_style']['total_issues'])
        security_score = max(0, 100 - self.results['security']['total_vulnerabilities'] * 10)
        duplicate_score = max(0, 100 - self.results['duplicates']['total_duplicates'] * 5)
        complexity_score = max(0, 100 - self.results['complexity']['total_complex_functions'] * 2)
        doc_score = self.results['docstrings']['documentation_coverage']
        
        overall_score = (style_score + security_score + duplicate_score + complexity_score + doc_score) / 5
        
        # 総行数計算
        total_lines = sum(
            len(f.read_text().split('\n')) 
            for f in self._get_python_files()
        )
        
        return QualityReport(
            timestamp=datetime.now().isoformat(),
            total_files=self.results['code_style']['total_files'],
            total_lines=total_lines,
            code_style_issues=self.results['code_style']['total_issues'],
            security_vulnerabilities=self.results['security']['total_vulnerabilities'],
            duplicate_code_blocks=self.results['duplicates']['total_duplicates'],
            test_coverage=self.results['test_coverage']['overall_coverage'],
            performance_issues=self.results['complexity']['total_complex_functions'],
            overall_score=overall_score,
            details=self.results
        )
    
    def _save_report(self, report: QualityReport):
        """レポートをファイルに保存"""
        report_dir = Path('quality_reports')
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = report_dir / f'quality_report_{timestamp}.json'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Report saved to: {report_file}")
    
    def _display_summary(self, report: QualityReport):
        """サマリー表示"""
        print("\n" + "="*60)
        print("📊 QUALITY CHECK SUMMARY")
        print("="*60)
        print(f"📁 Total Files: {report.total_files}")
        print(f"📝 Total Lines: {report.total_lines:,}")
        print(f"🎯 Overall Score: {report.overall_score:.1f}/100")
        print("\n📈 Metrics:")
        print(f"  • Code Style Issues: {report.code_style_issues}")
        print(f"  • Security Vulnerabilities: {report.security_vulnerabilities}")
        print(f"  • Duplicate Code Blocks: {report.duplicate_code_blocks}")
        print(f"  • Complex Functions: {report.performance_issues}")
        print(f"  • Test Coverage: {report.test_coverage:.1f}%")
        print(f"  • Documentation Coverage: {self.results['docstrings']['documentation_coverage']:.1f}%")
        
        # 推奨事項
        print("\n💡 Recommendations:")
        if report.security_vulnerabilities > 0:
            print("  ⚠️  Address security vulnerabilities immediately")
        if report.duplicate_code_blocks > 10:
            print("  🔄 Consider refactoring duplicate code")
        if report.test_coverage < 80:
            print("  🧪 Improve test coverage to at least 80%")
        if report.overall_score < 70:
            print("  📈 Overall quality needs improvement")
        
        print("="*60)


def main():
    """メイン実行関数"""
    checker = QualityChecker()
    report = checker.run_full_check()
    
    # 品質基準を満たさない場合は終了コード1
    if report.overall_score < 70:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()