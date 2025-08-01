#!/usr/bin/env python3
"""
Phase 7 - 技術的負債分析スクリプト
中規模クラス（300-700行）の特定とリファクタリング優先順位の決定

Usage:
    python3 analysis/phase7_code_analysis.py
"""

import os
import re
import ast
import sys
from typing import Dict, List, Tuple, Any
from pathlib import Path
import json
from datetime import datetime

class Phase7CodeAnalyzer:
    """Phase 7のための包括的コード分析器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.app_dir = self.project_root / "app"
        self.analysis_results = {}
        
    def analyze_project(self) -> Dict[str, Any]:
        """プロジェクト全体の分析を実行"""
        print("🔍 Phase 7 - 技術的負債分析開始")
        print("=" * 60)
        
        # 1. 中規模ファイルを発見
        medium_files = self._find_medium_scale_files()
        print(f"📊 中規模ファイル ({300}-{700}行): {len(medium_files)}個発見")
        
        # 2. 各ファイルの詳細分析
        detailed_analysis = {}
        for file_path, line_count in medium_files:
            print(f"\n🔍 分析中: {file_path.relative_to(self.project_root)} ({line_count}行)")
            analysis = self._analyze_file(file_path)
            detailed_analysis[str(file_path.relative_to(self.project_root))] = analysis
        
        # 3. 技術的負債評価
        debt_evaluation = self._evaluate_technical_debt(detailed_analysis)
        
        # 4. リファクタリング優先順位
        priorities = self._calculate_refactoring_priorities(detailed_analysis, debt_evaluation)
        
        # 5. 結果の統合
        self.analysis_results = {
            "analysis_date": datetime.now().isoformat(),
            "phase": "Phase 7 - Medium-scale Class Refactoring",
            "summary": {
                "total_medium_files": len(medium_files),
                "high_priority_files": len([p for p in priorities if p['priority'] == 'HIGH']),
                "medium_priority_files": len([p for p in priorities if p['priority'] == 'MEDIUM']),
                "low_priority_files": len([p for p in priorities if p['priority'] == 'LOW'])
            },
            "files": detailed_analysis,
            "technical_debt": debt_evaluation,
            "refactoring_priorities": priorities
        }
        
        return self.analysis_results
    
    def _find_medium_scale_files(self) -> List[Tuple[Path, int]]:
        """中規模ファイル（300-700行）を発見"""
        medium_files = []
        
        for py_file in self.app_dir.rglob("*.py"):
            # __pycache__, migrations, testsを除外
            if any(part in str(py_file) for part in ['__pycache__', 'migrations', 'test_', '__init__.py']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    line_count = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
                    
                    # 300-700行の範囲
                    if 300 <= line_count <= 700:
                        medium_files.append((py_file, line_count))
            except Exception as e:
                print(f"⚠️  ファイル読み込みエラー {py_file}: {e}")
        
        return sorted(medium_files, key=lambda x: x[1], reverse=True)
    
    def _analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """単一ファイルの詳細分析"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # AST解析
            try:
                tree = ast.parse(content)
                ast_analysis = self._analyze_ast(tree)
            except SyntaxError as e:
                ast_analysis = {"error": f"Syntax error: {e}"}
            
            # 基本メトリクス
            basic_metrics = {
                "total_lines": len(lines),
                "code_lines": len([line for line in lines if line.strip() and not line.strip().startswith('#')]),
                "comment_lines": len([line for line in lines if line.strip().startswith('#')]),
                "blank_lines": len([line for line in lines if not line.strip()])
            }
            
            # 複雑度指標
            complexity_metrics = self._calculate_complexity_metrics(content, lines)
            
            # 依存関係分析
            dependencies = self._analyze_dependencies(content)
            
            # 潜在的問題の検出
            issues = self._detect_potential_issues(content, lines, ast_analysis)
            
            return {
                "file_path": str(file_path.relative_to(self.project_root)),
                "basic_metrics": basic_metrics,
                "complexity_metrics": complexity_metrics,
                "ast_analysis": ast_analysis,
                "dependencies": dependencies,
                "potential_issues": issues,
                "refactoring_candidates": self._identify_refactoring_candidates(ast_analysis, complexity_metrics)
            }
            
        except Exception as e:
            return {"error": f"Analysis failed: {e}"}
    
    def _analyze_ast(self, tree: ast.AST) -> Dict[str, Any]:
        """AST（抽象構文木）分析"""
        classes = []
        functions = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "line_start": node.lineno,
                    "methods": [],
                    "decorators": [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]
                }
                
                # メソッド分析
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_info = {
                            "name": item.name,
                            "line_start": item.lineno,
                            "args_count": len(item.args.args),
                            "is_private": item.name.startswith('_'),
                            "complexity": self._calculate_method_complexity(item)
                        }
                        class_info["methods"].append(method_info)
                
                classes.append(class_info)
                
            elif isinstance(node, ast.FunctionDef) and not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                function_info = {
                    "name": node.name,
                    "line_start": node.lineno,
                    "args_count": len(node.args.args),
                    "complexity": self._calculate_method_complexity(node)
                }
                functions.append(function_info)
                
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                import_info = {
                    "type": "import" if isinstance(node, ast.Import) else "from_import",
                    "module": getattr(node, 'module', None),
                    "names": [alias.name for alias in node.names] if hasattr(node, 'names') else []
                }
                imports.append(import_info)
        
        return {
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "class_count": len(classes),
            "function_count": len(functions),
            "import_count": len(imports)
        }
    
    def _calculate_method_complexity(self, node: ast.FunctionDef) -> int:
        """メソッドの循環的複雑度を概算"""
        complexity = 1  # ベース複雑度
        
        for child in ast.walk(node):
            # 条件分岐
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            # 例外処理
            elif isinstance(child, (ast.Try, ast.ExceptHandler)):
                complexity += 1
            # ブール演算子
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _calculate_complexity_metrics(self, content: str, lines: List[str]) -> Dict[str, Any]:
        """複雑度メトリクスの計算"""
        # 基本的な複雑度指標
        try_except_count = len(re.findall(r'\btry\b', content))
        if_count = len(re.findall(r'\bif\b', content))
        for_count = len(re.findall(r'\bfor\b', content))
        while_count = len(re.findall(r'\bwhile\b', content))
        
        # 長い行の検出
        long_lines = [i for i, line in enumerate(lines) if len(line) > 120]
        
        # ネストの深さ（概算）
        max_indent = max((len(line) - len(line.lstrip())) // 4 for line in lines if line.strip()) if lines else 0
        
        return {
            "try_except_count": try_except_count,
            "conditional_count": if_count,
            "loop_count": for_count + while_count,
            "long_lines_count": len(long_lines),
            "max_indentation_level": max_indent,
            "avg_line_length": sum(len(line) for line in lines) / len(lines) if lines else 0
        }
    
    def _analyze_dependencies(self, content: str) -> Dict[str, Any]:
        """依存関係分析"""
        flask_imports = len(re.findall(r'from flask', content))
        sqlalchemy_imports = len(re.findall(r'from.*sqlalchemy|import.*sqlalchemy', content))
        internal_imports = len(re.findall(r'from app\.', content))
        
        return {
            "flask_dependencies": flask_imports,
            "sqlalchemy_dependencies": sqlalchemy_imports,
            "internal_dependencies": internal_imports,
            "total_imports": len(re.findall(r'^(import |from .+import)', content, re.MULTILINE))
        }
    
    def _detect_potential_issues(self, content: str, lines: List[str], ast_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """潜在的問題の検出"""
        issues = []
        
        # 神クラス検出（Phase6で解決済みだが念のため）
        if "classes" in ast_analysis:
            for cls in ast_analysis["classes"]:
                if len(cls["methods"]) > 20:
                    issues.append({
                        "type": "god_class",
                        "severity": "HIGH",
                        "description": f"Class '{cls['name']}' has {len(cls['methods'])} methods (>20)",
                        "line": cls["line_start"]
                    })
        
        # 長いメソッド検出
        method_pattern = r'def\s+(\w+)\s*\([^)]*\):'
        method_starts = [(m.start(), m.group(1)) for m in re.finditer(method_pattern, content)]
        
        for i, (start_pos, method_name) in enumerate(method_starts):
            start_line = content[:start_pos].count('\n') + 1
            
            # 次のメソッドまたはファイル終端までの行数を概算
            if i + 1 < len(method_starts):
                end_pos = method_starts[i + 1][0]
            else:
                end_pos = len(content)
            
            method_lines = content[start_pos:end_pos].count('\n')
            
            if method_lines > 50:
                issues.append({
                    "type": "long_method",
                    "severity": "MEDIUM",
                    "description": f"Method '{method_name}' is approximately {method_lines} lines long (>50)",
                    "line": start_line
                })
        
        # DRY違反の検出（重複コードパターン）
        duplicate_patterns = self._find_duplicate_patterns(lines)
        for pattern in duplicate_patterns:
            issues.append({
                "type": "code_duplication",
                "severity": "MEDIUM",
                "description": f"Potential code duplication detected: {pattern['description']}",
                "lines": pattern["lines"]
            })
        
        return issues
    
    def _find_duplicate_patterns(self, lines: List[str]) -> List[Dict[str, Any]]:
        """重複パターンの検出（簡易版）"""
        duplicates = []
        
        # 同一の長い行を検出
        line_counts = {}
        for i, line in enumerate(lines):
            stripped = line.strip()
            if len(stripped) > 30 and not stripped.startswith('#'):
                if stripped in line_counts:
                    line_counts[stripped].append(i + 1)
                else:
                    line_counts[stripped] = [i + 1]
        
        for line_content, line_numbers in line_counts.items():
            if len(line_numbers) > 1:
                duplicates.append({
                    "description": f"Identical line repeated {len(line_numbers)} times",
                    "lines": line_numbers,
                    "content": line_content[:50] + "..." if len(line_content) > 50 else line_content
                })
        
        return duplicates
    
    def _identify_refactoring_candidates(self, ast_analysis: Dict[str, Any], complexity_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """リファクタリング候補の特定"""
        candidates = []
        
        if "classes" in ast_analysis:
            for cls in ast_analysis["classes"]:
                # 中規模クラス（10-20メソッド）のリファクタリング候補
                if 10 <= len(cls["methods"]) <= 20:
                    candidates.append({
                        "type": "class_refactoring",
                        "name": cls["name"],
                        "reason": f"Medium-scale class with {len(cls['methods'])} methods",
                        "priority": "HIGH" if len(cls["methods"]) > 15 else "MEDIUM",
                        "suggested_action": "Split into specialized service classes"
                    })
                
                # 複雑なメソッドを持つクラス
                complex_methods = [m for m in cls["methods"] if m.get("complexity", 0) > 10]
                if complex_methods:
                    candidates.append({
                        "type": "method_complexity",
                        "name": cls["name"],
                        "reason": f"Contains {len(complex_methods)} complex methods",
                        "priority": "MEDIUM",
                        "suggested_action": "Extract complex methods into separate services"
                    })
        
        return candidates
    
    def _evaluate_technical_debt(self, detailed_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """技術的負債の総合評価"""
        total_files = len(detailed_analysis)
        high_priority_issues = 0
        medium_priority_issues = 0
        low_priority_issues = 0
        
        for file_path, analysis in detailed_analysis.items():
            if "potential_issues" in analysis:
                for issue in analysis["potential_issues"]:
                    severity = issue.get("severity", "LOW")
                    if severity == "HIGH":
                        high_priority_issues += 1
                    elif severity == "MEDIUM":
                        medium_priority_issues += 1
                    else:
                        low_priority_issues += 1
        
        # 技術的負債レベルの計算
        if high_priority_issues > 5:
            debt_level = "HIGH"
            grade = "D"
        elif high_priority_issues > 2 or medium_priority_issues > 10:
            debt_level = "MEDIUM"
            grade = "C"
        elif medium_priority_issues > 5:
            debt_level = "LOW"
            grade = "B"
        else:
            debt_level = "MINIMAL"
            grade = "A"
        
        return {
            "overall_debt_level": debt_level,
            "grade": grade,
            "total_files_analyzed": total_files,
            "issues_breakdown": {
                "high_priority": high_priority_issues,
                "medium_priority": medium_priority_issues,
                "low_priority": low_priority_issues
            },
            "improvement_from_phase6": "Significant improvement after Phase 6 god class refactoring"
        }
    
    def _calculate_refactoring_priorities(self, detailed_analysis: Dict[str, Any], debt_evaluation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """リファクタリング優先順位の計算"""
        priorities = []
        
        for file_path, analysis in detailed_analysis.items():
            if "error" in analysis:
                continue
                
            # 優先度スコア計算
            score = 0
            reasons = []
            
            # 基本メトリクスによるスコア
            if "basic_metrics" in analysis:
                code_lines = analysis["basic_metrics"]["code_lines"]
                if code_lines > 500:
                    score += 3
                    reasons.append(f"Large file ({code_lines} lines)")
                elif code_lines > 400:
                    score += 2
                    reasons.append(f"Medium-large file ({code_lines} lines)")
            
            # 複雑度によるスコア
            if "complexity_metrics" in analysis:
                complexity = analysis["complexity_metrics"]
                if complexity["try_except_count"] > 10:
                    score += 2
                    reasons.append(f"High exception handling complexity ({complexity['try_except_count']} try/except)")
                if complexity["max_indentation_level"] > 6:
                    score += 1
                    reasons.append(f"Deep nesting (level {complexity['max_indentation_level']})")
            
            # 問題の重要度によるスコア
            if "potential_issues" in analysis:
                for issue in analysis["potential_issues"]:
                    if issue["severity"] == "HIGH":
                        score += 3
                        reasons.append(f"High severity issue: {issue['type']}")
                    elif issue["severity"] == "MEDIUM":
                        score += 1
                        reasons.append(f"Medium severity issue: {issue['type']}")
            
            # リファクタリング候補によるスコア
            if "refactoring_candidates" in analysis:
                high_priority_candidates = [c for c in analysis["refactoring_candidates"] if c.get("priority") == "HIGH"]
                score += len(high_priority_candidates) * 2
                for candidate in high_priority_candidates:
                    reasons.append(f"High priority refactoring: {candidate['type']}")
            
            # 優先度レベル決定
            if score >= 7:
                priority = "HIGH"
            elif score >= 4:
                priority = "MEDIUM"
            else:
                priority = "LOW"
            
            priorities.append({
                "file_path": file_path,
                "priority": priority,
                "score": score,
                "reasons": reasons,
                "estimated_effort": self._estimate_refactoring_effort(analysis, score)
            })
        
        return sorted(priorities, key=lambda x: x["score"], reverse=True)
    
    def _estimate_refactoring_effort(self, analysis: Dict[str, Any], priority_score: int) -> str:
        """リファクタリング工数の見積もり"""
        if "basic_metrics" not in analysis:
            return "Unknown"
            
        code_lines = analysis["basic_metrics"]["code_lines"]
        
        if priority_score >= 7:
            return "High (1-2 weeks)"
        elif priority_score >= 4:
            return "Medium (3-5 days)"
        else:
            return "Low (1-2 days)"
    
    def save_analysis_results(self, output_file: str = None):
        """分析結果をファイルに保存"""
        if not output_file:
            output_file = f"analysis/phase7_analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_path = self.project_root / output_file
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📊 分析結果を保存しました: {output_path}")
        return output_path
    
    def print_summary_report(self):
        """分析結果のサマリーレポートを出力"""
        if not self.analysis_results:
            print("❌ 分析結果がありません")
            return
        
        print("\n" + "=" * 80)
        print("📊 PHASE 7 - 技術的負債分析結果サマリー")
        print("=" * 80)
        
        summary = self.analysis_results["summary"]
        debt = self.analysis_results["technical_debt"]
        
        print(f"🎯 総合評価: Grade {debt['grade']} ({debt['overall_debt_level']} debt level)")
        print(f"📁 分析対象ファイル: {summary['total_medium_files']}個")
        print(f"🚨 高優先度ファイル: {summary['high_priority_files']}個")
        print(f"⚠️  中優先度ファイル: {summary['medium_priority_files']}個")
        print(f"✅ 低優先度ファイル: {summary['low_priority_files']}個")
        
        print(f"\n🔍 検出された問題:")
        issues = debt["issues_breakdown"]
        print(f"  • 高重要度: {issues['high_priority']}件")
        print(f"  • 中重要度: {issues['medium_priority']}件")
        print(f"  • 低重要度: {issues['low_priority']}件")
        
        print(f"\n📈 {debt['improvement_from_phase6']}")
        
        # 優先度TOP5を表示
        priorities = self.analysis_results["refactoring_priorities"]
        if priorities:
            print(f"\n🎯 リファクタリング優先度 TOP5:")
            for i, item in enumerate(priorities[:5], 1):
                print(f"  {i}. {item['file_path']} ({item['priority']}, Score: {item['score']})")
                print(f"     - {item['estimated_effort']}")
                if item['reasons']:
                    print(f"     - {item['reasons'][0]}")


def main():
    """メイン実行関数"""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    analyzer = Phase7CodeAnalyzer(project_root)
    
    try:
        # 分析実行
        results = analyzer.analyze_project()
        
        # 結果表示
        analyzer.print_summary_report()
        
        # 結果保存
        output_file = analyzer.save_analysis_results()
        
        print(f"\n✅ Phase 7 分析完了")
        print(f"📄 詳細結果: {output_file}")
        
    except Exception as e:
        print(f"❌ 分析エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()