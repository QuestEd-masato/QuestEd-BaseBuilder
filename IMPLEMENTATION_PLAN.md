# QuestEd 最小限実装計画 - RDS互換版

## 🎯 緊急修正完了状況

### ✅ 完了した修正
1. **BasicKnowledgeItem.difficulty フィールド名修正**
   - `difficulty_level` → `difficulty` に変更
   - RDSの実際のカラム名に合わせて修正完了

2. **RDS非存在モデルのコメントアウト**
   - `SpeechSettings`、`SpeechStatistics` - 将来実装用に保留
   - `LearningPattern`、`RecommendationSettings` など AI関連5クラス
   - `StudentWeakness`、`ReviewSchedule` など復習関連4クラス
   - `LearningPathUnit` - 学習パス詳細テーブル

3. **既存テーブルモデルの確認**
   - `ActivityLog` (4件データ) - ✅ 既存モデル正常
   - `AnswerRecord` (3,712件データ) - ✅ 既存モデル正常  
   - `Milestone` (5件データ) - ✅ 既存モデル正常

4. **モデル構文チェック完了**
   - 全8ファイル ✅ 構文エラーなし
   - 44個のモデルクラス定義済み
   - RDS互換性確保

## 📋 実装可能な機能（RDS存在テーブルのみ）

### 1. 音声入力機能（基本版）
**利用テーブル**: `speech_transcriptions`
```python
# 実装済みモデル
class SpeechTranscription(db.Model):
    user_id, transcription, usage_context, duration, 
    confidence_score, session_id, created_at
```

**実装可能機能**:
- Web Speech API連携
- 音声認識結果の保存・表示
- 認識精度の記録
- 使用履歴の管理

### 2. 自由進度学習ポータル
**利用テーブル**: `curriculum_units`, `student_unit_selections`, `unit_item_mappings`
```python
# 実装済みモデル
class CurriculumUnit(db.Model):         # 学習単元マスタ
class StudentUnitSelection(db.Model):   # 生徒選択履歴
class UnitItemMapping(db.Model):        # 単元-問題紐付け
class ClassLearningSettings(db.Model):  # クラス別設定
```

**実装可能機能**:
- 単元ベースの学習進行管理
- 生徒の自由な単元選択
- 進捗率・正解率の追跡
- クラス別学習設定

### 3. AI推薦システム（基本版）
**利用テーブル**: `ai_recommendations`
```python
# 実装済みモデル  
class AIRecommendation(db.Model):
    student_id, recommendation_type, ai_response,
    confidence_score, is_accepted, reasoning
```

**実装可能機能**:
- OpenAI GPT-4による推薦生成
- 推薦の受諾・拒否追跡
- 推薦理由の表示
- 基本的な効果測定

### 4. 復習システム（基本版）
**利用テーブル**: `review_sets`, `review_set_items`
```python
# 実装済みモデル
class ReviewSet(db.Model):      # 復習セット
class ReviewSetItem(db.Model):  # 復習問題
```

**実装可能機能**:
- 復習問題セットの作成
- 問題の解答・採点
- 進捗追跡
- AI生成復習セット

### 5. 教科別フィルタリング
**利用フィールド**: 各テーブルの `subject_id`
```python
# 既存テーブルにsubject_id追加済み
BasicKnowledgeItem.subject_id
CurriculumUnit.subject_id  
ProblemCategory.subject_id
```

**実装可能機能**:
- 教科別の問題表示
- 教科別の単元管理
- 教科別の進捗表示

## 🚀 実装優先順位

### 第1段階（即座実装可能）
1. **音声入力API**
   - 最もシンプル、既存機能への影響なし
   - Web Speech API + SpeechTranscription モデル

2. **教科別フィルタリング**
   - 既存のBaseBuilderに大きな価値追加
   - subject_id活用で即座に実装可能

### 第2段階（データ投入後）
3. **自由進度学習**
   - curriculum_units テーブルにサンプルデータ投入が必要
   - 単元-問題の紐付けデータ作成

4. **基本AI推薦**
   - 学習履歴に基づく簡単な推薦

### 第3段階（機能拡張）
5. **復習システム**
   - 弱点分析なしの基本復習機能

## 📝 データ投入が必要なテーブル

### curriculum_units
```sql
-- サンプル単元データの投入例
INSERT INTO curriculum_units (subject_id, unit_code, title, description, difficulty_level) VALUES
(1, 'ENG_BASIC_01', '基本的な挨拶表現', '日常で使う基本的な挨拶を学習', 1),
(1, 'ENG_BASIC_02', '自己紹介', '名前、年齢、趣味の表現', 2);
```

### unit_item_mappings
```sql  
-- 単元-問題の紐付けデータ
INSERT INTO unit_item_mappings (unit_id, item_id, weight, order_index, is_required) VALUES
(1, 101, 1.0, 1, TRUE),  -- 単元1に問題101を紐付け
(1, 102, 1.0, 2, TRUE);  -- 単元1に問題102を紐付け
```

## 🔧 技術実装メモ

### 実装時の注意点
1. **フィールド名の一致確認**
   - RDS: `difficulty` ✅
   - RDS: `user_id` ✅  
   - RDS: `subject_id` ✅

2. **外部キー制約の確認**
   - speech_transcriptions.user_id → users.id
   - curriculum_units.subject_id → subjects.id
   - ai_recommendations.student_id → users.id

3. **新機能フラグの活用**
   - 既存機能への影響を最小化
   - 段階的な機能展開

### 次回実装時の作業手順
1. 音声入力API（JavaScript + Python Flask）
2. 教科別フィルタリング（既存BaseBuilder拡張）
3. 単元データ投入スクリプト作成
4. 自由進度学習画面開発
5. AI推薦エンジン統合

## 📊 実装効果の測定

### 成功指標
- **音声入力**: 利用率、認識精度
- **自由進度学習**: 単元完了率、学習時間
- **AI推薦**: 推薦受諾率、学習効果向上
- **教科別**: フィルタ利用率、学習効率

最小限の実装でも大きな価値を提供できる基盤が整いました！ 🎉