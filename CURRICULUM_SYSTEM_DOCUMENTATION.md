# カリキュラムシステム統合ドキュメント

**最終更新**: 2025年8月25日  
**統合元**: 3つの関連ドキュメントから重要情報を統合

## 📊 カリキュラム二重管理問題と解決

### 問題の概要
- **データ二重管理**: curriculum_data（JSONカラム）+ curriculum_lessons（テーブル）
- **依存関係**: curriculum_data 31ファイル依存、curriculum_lessons 17ファイル使用
- **サービス重複**: 10個のカリキュラムサービス + 5個の同期サービス

### 解決状況（2025年8月7日完了）
- **Phase 4-7実装**: 移行アダプター基盤による段階的統一
- **成果**: 教師の保存が学生に即座反映される正常システム
- **パフォーマンス**: JSON解析不要により40%高速化

## 🎯 現在のシステム構成

### データ構造
```sql
-- メインテーブル（統一データソース）
curriculum_lessons        -- カリキュラムレッスン
lesson_tasks             -- レッスンタスク
student_lesson_progress  -- 学生進捗管理

-- 移行中（段階的削除予定）
curriculums.curriculum_data  -- JSONカラム（後方互換性のため保持）
```

### 移行アダプター（migration_adapter.py）
```python
class CurriculumMigrationAdapter:
    @classmethod
    def read_curriculum_content(cls, curriculum_id: int) -> Dict[str, Any]:
        """統一読み取り: curriculum_lessons優先、curriculum_dataフォールバック"""
        
    @classmethod
    def write_curriculum_content(cls, curriculum_id: int, content: Dict[str, Any]) -> bool:
        """統一書き込み: 設定に応じてcurriculum_lessonsメイン、curriculum_data補完"""
```

### 設定による制御
```python
# config.py
ENABLE_CURRICULUM_DATA_SYNC = False  # 同期無効化
PREFER_CURRICULUM_LESSONS = True     # テーブル優先
```

## 📈 期待効果と今後の計画

### 達成済み効果
- ✅ データ整合性: 教師・学生間の完全同期
- ✅ パフォーマンス: 40%の応答速度向上
- ✅ コード削減: 同期サービス5個の削除準備完了

### 今後の統一計画
1. **Phase 1**: curriculum_data完全削除準備（依存関係の段階的解消）
2. **Phase 2**: サービス統合（10個→4個への削減）
3. **Phase 3**: パフォーマンス最適化とインデックス調整

## ⚠️ 注意事項
- **後方互換性**: 現在も維持中、段階的移行を継続
- **データ移行**: 本番環境では慎重な実行が必要
- **ロールバック**: 各段階でのロールバック手順を準備済み

---

*詳細な技術仕様や移行手順は、必要に応じて参照可能*