#!/bin/bash

# BaseBuilderエンドポイントの置換マッピング
declare -A replacements=(
    # カテゴリ関連
    ["basebuilder_module.categories"]="categories.categories"
    ["basebuilder_module.create_category"]="categories.create_category"
    ["basebuilder_module.edit_category"]="categories.edit_category"
    ["basebuilder_module.delete_category"]="categories.delete_category"
    ["basebuilder_module.category_texts"]="categories.category_texts"
    
    # 問題関連
    ["basebuilder_module.problems"]="problems.problems"
    ["basebuilder_module.create_problem"]="problems.create_problem"
    ["basebuilder_module.edit_problem"]="problems.edit_problem"
    ["basebuilder_module.delete_problem"]="problems.delete_problem"
    ["basebuilder_module.start_search_session"]="problems.start_search_session"
    
    # セッション関連
    ["basebuilder_module.solve_problem"]="sessions.solve_problem"
    ["basebuilder_module.start_category_session"]="sessions.start_category_session"
    ["basebuilder_module.submit_answer"]="sessions.submit_answer"
    ["basebuilder_module.session_summary"]="sessions.session_summary"
    ["basebuilder_module.solve_text_problem"]="sessions.solve_text_problem"
    
    # 進捗・分析関連
    ["basebuilder_module.proficiency"]="progress.proficiency"
    ["basebuilder_module.view_history"]="progress.view_history"
    ["basebuilder_module.analysis"]="analytics.analysis"
    ["basebuilder_module.student_analysis"]="analytics.student_analysis"
    
    # 管理機能関連
    ["basebuilder_module.text_sets"]="basebuilder_admin.text_sets"
    ["basebuilder_module.my_texts"]="basebuilder_admin.my_texts"
    ["basebuilder_module.deliver_text"]="basebuilder_admin.deliver_text"
    ["basebuilder_module.import_text_set"]="basebuilder_admin.import_text_set"
    ["basebuilder_module.create_learning_path"]="basebuilder_admin.create_learning_path"
    ["basebuilder_module.assign_learning_path"]="basebuilder_admin.assign_learning_path"
    ["basebuilder_module.learning_paths"]="basebuilder_admin.learning_paths"
    ["basebuilder_module.theme_relations"]="basebuilder_admin.theme_relations"
    
    # インデックス・基本ページ
    ["basebuilder_module.index"]="basebuilder.index"
)

echo "🔧 BaseBuilder エンドポイント修正開始..."
echo "対象: $(find templates/basebuilder/ -name "*.html" | wc -l) ファイル"

total_replacements=0

# 各置換を実行
for old in "${!replacements[@]}"; do
    new="${replacements[$old]}"
    echo "置換中: $old -> $new"
    
    # 実際の置換を実行し、変更数をカウント
    count=$(find templates/basebuilder/ -name "*.html" -exec grep -l "$old" {} \; | wc -l)
    if [ $count -gt 0 ]; then
        find templates/basebuilder/ -name "*.html" -exec sed -i "s|$old|$new|g" {} \;
        total_replacements=$((total_replacements + count))
        echo "  ✅ $count ファイルで修正"
    else
        echo "  ⏭ 該当なし"
    fi
done

echo ""
echo "🎯 BaseBuilder エンドポイント修正完了"
echo "総修正ファイル数: $total_replacements"

# 修正後の確認
remaining=$(grep -r "basebuilder_module\." templates/basebuilder/ --include="*.html" | wc -l)
echo "残存 basebuilder_module 参照: $remaining 件"

if [ $remaining -eq 0 ]; then
    echo "✅ 全ての basebuilder_module 参照を修正完了"
else
    echo "⚠ 未修正の参照が残存しています:"
    grep -r "basebuilder_module\." templates/basebuilder/ --include="*.html" | head -5
fi