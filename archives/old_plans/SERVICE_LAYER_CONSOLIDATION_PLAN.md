# 🔧 サービス層統合計画 - QuestEd Ver.1.4

## 📋 現在の問題状況（2025年8月10日確認）

### **🔴 発見された根本的問題**

#### **問題1: 過度なサービス分割による複雑性増加**
- **総サービス数**: 62個（適正値の約2倍）
- **カリキュラム関連**: 9ファイル、3,360行（重複機能多数）
- **同期処理関連**: 5ファイル、約1,474行（責任分散過剰）
- **結果**: サービス間調整コストが分割効果を相殺

#### **問題2: 責任境界の不明確化**
```
現在の問題例：
curriculum_orchestration_service.py (495行) ← 統合制御
  ↓ 依存
curriculum_data_service.py (458行) ← データアクセス
  ↓ 依存  
curriculum_validation_service.py (297行) ← 検証処理
```
**問題**: 単純な処理でも3-4サービスを経由、デバッグ困難

#### **問題3: 同期処理の重複**
```
重複する同期サービス群：
├── sync_executor_service.py (320行)
├── sync_scheduler_service.py (200行) 
├── conflict_resolver_service.py (435行)
├── sync_validator_service.py (519行)
└── auto_sync_service.py (推定値)
```
**問題**: 類似機能の重複実装、保守コスト増大

#### **問題4: アーキテクチャの方向性**
- **現状**: 複雑さ増加方向（分割 = 改善の誤認）
- **必要**: シンプル化・統合による保守性向上

---

## 🎯 統合計画：複雑さ削減方向への転換

### **基本方針**
1. **適切な粒度への統合**: 300-800行の管理可能サイズ
2. **機能凝集性の重視**: 密接に関連する機能の統合
3. **段階的移行**: リスク最小化の慎重な実施
4. **後方互換性維持**: 既存API・機能の完全保持

---

## 📊 Phase 統合-1: カリキュラムコア統合

### **統合対象**
```
統合前（3ファイル、1,350行）:
├── curriculum_orchestration_service.py (495行) ← 統合制御
├── curriculum_data_service.py (458行) ← データアクセス
└── curriculum_validation_service.py (297行) ← 検証処理

統合後（1ファイル、約800行）:
└── curriculum_core_service.py
   ├── データアクセス機能（CRUD操作）
   ├── 基本検証機能（権限・データ検証）
   └── 統合制御機能（ワークフロー制御）
```

### **期間**: 2週間（ローカル環境での慎重実施）

#### **Week 1: 準備・設計フェーズ**
```python
# curriculum_core_service.py の設計
class CurriculumCoreService:
    """統合カリキュラムサービス - データ・検証・制御統合"""
    
    # === データアクセス層（旧curriculum_data_service） ===
    def get_curriculum_data(self, curriculum_id: int) -> dict
    def create_curriculum(self, class_id: int, data: dict) -> dict
    def update_curriculum(self, curriculum_id: int, data: dict) -> dict
    def delete_curriculum(self, curriculum_id: int) -> dict
    
    # === 検証層（旧curriculum_validation_service） ===
    def validate_curriculum_data(self, data: dict) -> dict
    def validate_teacher_permission(self, class_id: int) -> dict
    def validate_curriculum_access(self, curriculum_id: int) -> dict
    
    # === 統合制御層（旧orchestration_service の単純化） ===
    def process_curriculum_creation(self, class_id: int, form_data: dict) -> dict
    def process_curriculum_update(self, curriculum_id: int, form_data: dict) -> dict
    def get_curriculum_view_data(self, curriculum_id: int) -> dict
```

#### **Week 2: 実装・テストフェーズ**
1. **Day 1-3**: `curriculum_core_service.py` 実装
2. **Day 4-5**: ユニットテスト作成・実行
3. **Day 6-7**: 統合テスト・既存機能確認

#### **移行手順**
```python
# Step 1: 新サービス作成（並行動作）
# Step 2: 参照元の段階的切り替え（9箇所）
from app.services.curriculum.curriculum_orchestration_service import CurriculumOrchestrationService
↓ 変更
from app.services.curriculum.curriculum_core_service import CurriculumCoreService

# Step 3: 動作確認後、旧ファイル削除
```

---

## 📊 Phase 統合-2: 同期システム統合

### **統合対象**
```
統合前（5ファイル、約1,474行）:
├── sync_executor_service.py (320行) ← 実行制御
├── sync_scheduler_service.py (200行) ← スケジューリング
├── conflict_resolver_service.py (435行) ← 競合解決
├── sync_validator_service.py (519行) ← 検証処理
└── auto_sync_service.py (推定値) ← メイン制御

統合後（1ファイル、約600行）:
└── curriculum_sync_service.py
   ├── スケジューリング機能
   ├── 実行制御機能
   ├── 競合解決機能
   └── 検証機能
```

### **期間**: 2週間（Phase統合-1完了後）

#### **Week 1: 分析・設計フェーズ**
```python
# curriculum_sync_service.py の設計
class CurriculumSyncService:
    """カリキュラム同期統合サービス"""
    
    # スケジューリング（旧sync_scheduler_service）
    def schedule_sync(self, curriculum_id: int, sync_type: str) -> dict
    def get_sync_schedule(self, curriculum_id: int) -> dict
    
    # 実行制御（旧sync_executor_service）
    def execute_sync(self, sync_task: dict) -> dict
    def monitor_sync_progress(self, sync_id: str) -> dict
    
    # 競合解決（旧conflict_resolver_service）
    def detect_conflicts(self, sync_data: dict) -> list
    def resolve_conflicts(self, conflicts: list) -> dict
    
    # 検証（旧sync_validator_service）
    def validate_sync_data(self, data: dict) -> dict
    def validate_sync_result(self, result: dict) -> dict
```

#### **Week 2: 実装・テストフェーズ**
1. **Day 1-4**: 統合サービス実装
2. **Day 5-6**: 機能移植・テスト
3. **Day 7**: 完全切り替え・動作確認

---

## 📊 保持するサービス群

### **専門性・独立性の高いサービス（統合対象外）**
```
維持対象（5ファイル）:
├── curriculum_ai_service.py (306行) - AI機能、外部API依存
├── curriculum_import_export_service.py (488行) - ファイル処理専門
├── teacher_curriculum_unit_service.py (434行) - 教師UI専用
├── theme_management_service.py (420行) - テーマ管理専門
└── basebuilder_content_service.py (95行) - BaseBuilder連携
```

**保持理由**: 専門性が高く、独立性を保つことで保守性向上

---

## 📈 期待される改善効果

### **定量的改善**
| 項目 | 統合前 | 統合後 | 改善率 |
|------|--------|---------|--------|
| **カリキュラムサービス** | 9ファイル | 6ファイル | 33%削減 |
| **同期サービス** | 5ファイル | 1ファイル | 80%削減 |
| **総行数** | 4,834行 | 2,800行 | 42%削減 |
| **参照箇所** | 複雑な多重依存 | 単純な依存関係 | 大幅簡素化 |

### **定性的改善**
1. **デバッグ容易性**: 処理フローの追跡が1ファイル内で完結
2. **テスト簡素化**: モック・依存関係の大幅削減
3. **新人理解性**: 機能境界が明確で学習コストが低減
4. **保守効率**: 関連機能の変更が1箇所で完結

---

## ⚠️ リスク管理・注意事項

### **実施時の注意点**

#### **1. 段階的移行の厳守**
```bash
# 必須手順
1. ローカル環境での完全テスト
2. 既存ファイルとの並行動作期間（1週間）
3. 段階的な参照先切り替え
4. 完全動作確認後の旧ファイル削除
```

#### **2. テスト戦略**
```python
# 必須テスト項目
- 機能同等性テスト（Before/After）
- エラーケーステスト
- パフォーマンステスト
- 統合テスト（他サービスとの連携）
```

#### **3. ロールバック計画**
```bash
# 緊急時対応
git checkout HEAD~1 -- app/services/curriculum/
systemctl restart quested
# 動作確認・問題切り分け
```

### **成功指標**
- ✅ 既存機能100%動作（後方互換性維持）
- ✅ サービス間調整コストの削減
- ✅ デバッグ効率の向上
- ✅ 新規機能追加の容易性向上

---

## 📅 実施スケジュール

### **Phase 統合-1: カリキュラムコア統合**
- **期間**: 2025年8月12日 - 8月25日（2週間）
- **環境**: ローカル環境での慎重実施
- **成功基準**: 既存機能100%動作、参照元9箇所の正常動作

### **Phase 統合-2: 同期システム統合**  
- **期間**: 2025年8月26日 - 9月8日（2週間）
- **前提**: Phase統合-1の完全成功
- **成功基準**: 同期機能の正常動作、パフォーマンス維持

### **本番環境適用**
- **時期**: ローカル環境での完全検証後
- **条件**: 全機能の動作確認、十分なテスト期間
- **方針**: 慎重かつ段階的な本番適用

---

## 🎯 最終目標

### **アーキテクチャの方向性転換**
- **Before**: 分割による複雑性増加
- **After**: 適切な統合による保守性向上

### **技術的負債レベルの改善**
- **現在**: Grade B+（過度分割による複雑性）
- **目標**: Grade A-（適切な統合による保守性）

この計画により、QuestEdは真の意味での保守性・拡張性に優れたシステムに進化します。