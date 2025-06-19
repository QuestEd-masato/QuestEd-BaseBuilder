# QuestEd モデル定義・RDS構造 不整合分析レポート

## 分析結果サマリー

### 🔍 発見された問題
1. **重複モデル定義**: `__init__.py`と個別ファイルでモデルが重複定義されている
2. **フィールド名の不一致**: RDSの実際のフィールド名とモデル定義が異なる
3. **欠落しているフィールド**: RDSに存在するがモデルに定義されていないフィールド
4. **インデックス・制約の不一致**: RDSの制約がモデルに反映されていない
5. **新機能テーブルの部分実装**: 一部のテーブルがRDSに存在するがモデル定義が不完全

---

## 詳細分析

### 1. 重複モデル定義の問題

#### 問題のあるモデル
| モデル名 | `__init__.py` | 個別ファイル | 状態 |
|---------|---------------|------------|------|
| `CurriculumUnit` | ✅ 行359-380 | ✅ curriculum_unit.py | **重複** |
| `StudentUnitSelection` | ✅ 行382-408 | ✅ curriculum_unit.py | **重複** |
| `SpeechTranscription` | ✅ 行410-424 | ✅ speech_transcription.py | **重複** |
| `UnitItemMapping` | ✅ 行426-442 | ✅ curriculum_unit.py | **重複** |
| `ClassLearningSettings` | ✅ 行444-466 | ✅ curriculum_unit.py | **重複** |

#### 影響
- インポートエラーの原因
- モデル定義の不整合
- マイグレーション時の問題

---

### 2. RDS vs モデル フィールド差分

#### A. Users テーブル
| RDS フィールド | モデル フィールド | 状態 | 必要なアクション |
|-------------|-------------|------|-------------|
| `is_active` | ❌ 欠落 | **追加必要** | フィールド追加 |
| `class_id` | ❌ 欠落 | **追加必要** | フィールド追加 |

#### B. Classes テーブル
| RDS フィールド | モデル フィールド | 状態 | 必要なアクション |
|-------------|-------------|------|-------------|
| `subject_id` | ✅ 存在 | **OK** | - |

#### C. Basic_knowledge_items テーブル  
| RDS フィールド | モデル フィールド | 状態 | 必要なアクション |
|-------------|-------------|------|-------------|
| `subject_id` | ❌ 欠落 | **追加必要** | フィールド追加 |
| `difficulty_level` | `difficulty` | **名前不一致** | 名前変更 |

#### D. Problem_categories テーブル
| RDS フィールド | モデル フィールド | 状態 | 必要なアクション |
|-------------|-------------|------|-------------|
| `subject_id` | ❌ 欠落 | **追加必要** | フィールド追加 |

#### E. Curriculums テーブル
| RDS フィールド | モデル フィールド | 状態 | 必要なアクション |
|-------------|-------------|------|-------------|
| `subject_id` | ❌ 欠落 | **追加必要** | フィールド追加 |

---

### 3. Speech_transcriptions テーブルの不整合

#### RDS構造 vs モデル定義
| RDS フィールド | 既存モデル | 新モデル | 状態 |
|-------------|----------|--------|------|
| `user_id` | ✅ | `student_id` | **名前変更必要** |
| `transcription` | ✅ | `original_audio_text` | **分割必要** |
| `usage_context` | ✅ | `input_context` | **名前変更必要** |
| `duration` | ❌ | `audio_duration` | **追加必要** |
| `session_id` | ❌ | ✅ | **追加必要** |
| `cleaned_text` | ❌ | ✅ | **追加必要** |
| `confidence_score` | ❌ | ✅ | **追加必要** |

---

### 4. 新機能テーブルの実装状況

#### 完全に欠落しているテーブル
1. **speech_settings** - 音声入力設定
2. **speech_statistics** - 音声入力統計  
3. **learning_patterns** - 学習パターン分析
4. **recommendation_settings** - 推薦設定
5. **recommendation_effectiveness** - 推薦効果測定
6. **recommendation_algorithms** - 推薦アルゴリズム
7. **recommendation_queue** - 推薦キュー
8. **review_sets** - 復習セット
9. **review_set_items** - 復習セット問題
10. **student_weaknesses** - 生徒弱点分析
11. **review_schedules** - 復習スケジュール
12. **review_performance** - 復習パフォーマンス
13. **review_generation_rules** - 復習生成ルール
14. **learning_paths** (新) - 学習パス（BaseBuilderと名前衝突）
15. **learning_path_units** - 学習パス詳細
16. **email_logs** - メール送信ログ

#### 部分実装されているテーブル
1. **curriculum_units** - 基本フィールドは存在、RDS追加フィールドが欠落
2. **student_unit_selections** - 基本フィールドは存在、RDS追加フィールドが欠落
3. **unit_item_mappings** - 基本フィールドは存在、RDS追加フィールドが欠落

---

### 5. インデックス・制約の欠落

#### 必要な複合インデックス
```sql
-- speech_transcriptions
INDEX idx_student_id (student_id)
INDEX idx_session_id (session_id)  
INDEX idx_input_context (input_context, context_id)

-- curriculum_units
INDEX idx_subject_id (subject_id)
INDEX idx_difficulty_level (difficulty_level)
INDEX idx_school_id (school_id)

-- student_unit_selections  
INDEX idx_student_id (student_id)
INDEX idx_unit_id (unit_id)
INDEX idx_class_id (class_id)
INDEX idx_status (status)
```

#### 必要なユニーク制約
```sql
-- speech_settings
UNIQUE KEY uk_student_speech_settings (student_id)

-- class_learning_settings  
UNIQUE KEY uk_class_learning_settings (class_id)

-- unit_item_mappings
UNIQUE KEY uk_unit_item (unit_id, item_id)
```

---

## 推奨リファクタリング戦略

### Phase 1: 重複解消 (高優先度)
1. `__init__.py`から重複モデル定義を削除
2. 個別ファイルからのインポートのみ残す
3. 循環インポートエラーの解決

### Phase 2: 既存モデル更新 (高優先度)  
1. **User モデル**に`is_active`, `class_id`追加
2. **BasicKnowledgeItem モデル**に`subject_id`追加、`difficulty`→`difficulty_level`変更
3. **ProblemCategory モデル**に`subject_id`追加
4. **Curriculum モデル**に`subject_id`追加

### Phase 3: 新機能モデル追加 (中優先度)
1. 欠落している16個のテーブルモデルを作成
2. 適切なリレーションシップ定義
3. インデックス・制約の実装

### Phase 4: マイグレーション作成 (中優先度)
1. Alembicマイグレーションスクリプト生成
2. データ移行スクリプト作成
3. ロールバック対応

---

## 即座に対応が必要な問題

### 🚨 Critical Issues
1. **重複モデル定義** → アプリケーション起動時エラーの原因
2. **Subject関連の外部キー制約** → データ整合性の問題
3. **speech_transcriptionsフィールド不一致** → 既存データとの互換性問題

### ⚠️ High Priority  
1. **新機能テーブルの欠落** → 新機能が使用不可
2. **インデックス不足** → パフォーマンス問題

### 📋 Medium Priority
1. **マイグレーションスクリプト** → デプロイ時の問題
2. **統合テスト** → 品質保証

---

## 次のステップ

1. **即座実行**: 重複モデル定義の削除
2. **24時間以内**: 既存モデルのフィールド追加  
3. **1週間以内**: 新機能モデルの完全実装
4. **2週間以内**: マイグレーション・テスト完了

このレポートに基づいて、段階的なリファクタリングを実施します。