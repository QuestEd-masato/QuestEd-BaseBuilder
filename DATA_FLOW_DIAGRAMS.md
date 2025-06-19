# QuestEd データフロー図

## 概要

QuestEd新機能の主要なユースケースにおけるデータフローを図解しています。

---

## 1. 音声入力フロー

### 1.1 基本音声入力フロー

```mermaid
sequenceDiagram
    participant User as 生徒
    participant Browser as ブラウザ
    participant WSA as Web Speech API
    participant Frontend as フロントエンド
    participant Backend as バックエンド
    participant DB as データベース
    participant NLP as NLP処理

    User->>Browser: 音声入力開始
    Browser->>WSA: startRecording()
    WSA->>WSA: 音声認識処理
    WSA->>Frontend: transcription結果
    
    Note right of Frontend: 信頼度スコア確認<br/>閾値チェック
    
    Frontend->>Backend: POST /api/speech/transcribe
    Note right of Backend: リクエスト内容:<br/>- original_text<br/>- confidence_score<br/>- context_id
    
    Backend->>NLP: テキストクリーニング
    NLP->>Backend: cleaned_text
    
    Backend->>DB: SpeechTranscription作成
    DB->>Backend: transcription_id
    
    Backend->>Backend: 統計情報更新
    Backend->>DB: SpeechStatistics更新
    
    Backend->>Frontend: レスポンス返却
    Frontend->>User: 結果表示
```

### 1.2 音声入力エラーハンドリング

```mermaid
flowchart TD
    A[音声入力開始] --> B{マイク権限確認}
    B -->|拒否| C[権限エラー表示]
    B -->|許可| D[音声認識開始]
    
    D --> E{認識結果確認}
    E -->|信頼度低| F[再録音提案]
    E -->|信頼度高| G[サーバー送信]
    
    G --> H{送信結果}
    H -->|エラー| I[ローカル保存]
    H -->|成功| J[正常処理完了]
    
    F --> D
    I --> K[リトライキューに追加]
    K --> L[後続処理で再送信]
```

---

## 2. 自由進度学習フロー

### 2.1 単元選択から学習完了まで

```mermaid
sequenceDiagram
    participant Student as 生徒
    participant Portal as 学習ポータル
    participant Backend as バックエンド
    participant AI as AI推薦エンジン
    participant DB as データベース

    Student->>Portal: ログイン
    Portal->>Backend: GET /api/units?class_id=7
    
    Backend->>DB: クラス教科確認
    Note right of DB: subjects.id = classes.subject_id
    
    Backend->>DB: 利用可能単元取得
    Note right of DB: curriculum_units<br/>WHERE subject_id = ?
    
    Backend->>DB: 生徒進捗確認
    Note right of DB: student_unit_selections<br/>JOIN curriculum_units
    
    Backend->>Backend: 前提条件チェック
    Backend->>Portal: 単元リスト返却
    
    Portal->>Student: 単元選択UI表示
    Student->>Portal: 単元選択（unit_id=1）
    
    Portal->>Backend: POST /api/units/1/select
    Backend->>DB: StudentUnitSelection作成
    
    Backend->>AI: 推薦キューに追加
    AI-->>Backend: 推薦処理（非同期）
    
    Backend->>Portal: 選択完了通知
    Portal->>Student: 学習開始画面表示
    
    Student->>Portal: 問題解答
    Portal->>Backend: PUT /api/units/1/progress
    
    Backend->>DB: 進捗更新
    Backend->>DB: 弱点分析更新
    Backend->>Portal: 進捗レスポンス
```

### 2.2 単元前提条件チェックフロー

```mermaid
flowchart TD
    A[単元選択要求] --> B[前提条件取得]
    B --> C{前提単元存在？}
    
    C -->|なし| D[選択可能]
    C -->|あり| E[前提単元チェック]
    
    E --> F[StudentUnitSelection確認]
    F --> G{全て完了？}
    
    G -->|完了| H[最低正解率チェック]
    G -->|未完了| I[未完了単元表示]
    
    H --> J{正解率80%以上？}
    J -->|以上| D
    J -->|未満| K[復習推奨]
    
    I --> L[前提単元学習案内]
    K --> M[前提単元復習案内]
```

---

## 3. AI推薦システムフロー

### 3.1 推薦生成プロセス

```mermaid
sequenceDiagram
    participant Trigger as トリガーイベント
    participant Queue as 推薦キュー
    participant Worker as AI Worker
    participant OpenAI as OpenAI API
    participant Analytics as 分析エンジン
    participant DB as データベース
    participant Student as 生徒

    Trigger->>Queue: 推薦要求
    Note right of Queue: login, problem_completed,<br/>unit_completed等
    
    Queue->>Worker: 非同期処理開始
    Worker->>DB: 学習履歴取得
    Worker->>DB: 弱点分析取得
    Worker->>DB: 学習パターン取得
    
    Worker->>Analytics: コンテキストデータ生成
    Analytics->>Analytics: パターン分析
    Analytics->>Worker: 分析結果
    
    Worker->>OpenAI: プロンプト生成＆送信
    Note right of OpenAI: GPT-4による推薦生成<br/>- 学習コンテンツ<br/>- 難易度調整<br/>- 個人化推薦
    
    OpenAI->>Worker: AI推薦結果
    Worker->>DB: AIRecommendation保存
    
    Worker->>DB: RecommendationQueue完了更新
    
    Note right of Student: 次回ログイン時に表示
    Student->>DB: 推薦取得
    DB->>Student: 推薦リスト
```

### 3.2 推薦効果測定フロー

```mermaid
flowchart TD
    A[推薦受け入れ] --> B[学習開始]
    B --> C[パフォーマンス記録]
    
    C --> D[一定期間経過]
    D --> E[効果測定トリガー]
    
    E --> F[推薦前データ取得]
    F --> G[推薦後データ取得]
    
    G --> H[改善率計算]
    H --> I[RecommendationEffectiveness更新]
    
    I --> J[推薦モデル調整]
    J --> K[アルゴリズム重み更新]
```

---

## 4. 復習問題生成フロー

### 4.1 AI復習セット生成フロー

```mermaid
sequenceDiagram
    participant Student as 生徒
    participant UI as UI
    participant Backend as バックエンド
    participant Analyzer as 弱点分析エンジン
    participant AI as AI生成エンジン
    participant DB as データベース

    Student->>UI: 復習開始要求
    UI->>Backend: POST /api/review/generate
    
    Backend->>DB: 弱点データ取得
    Note right of DB: student_weaknesses<br/>WHERE student_id = ?
    
    Backend->>Analyzer: 弱点分析実行
    Analyzer->>DB: 解答履歴分析
    Analyzer->>Analyzer: 重要度計算
    Analyzer->>Backend: 対象分野抽出
    
    Backend->>AI: 問題選択要求
    Note right of AI: アルゴリズム:<br/>- 弱点重み付け<br/>- 難易度調整<br/>- 学習効果予測
    
    AI->>DB: 候補問題検索
    AI->>AI: 最適化計算
    AI->>Backend: 選択問題リスト
    
    Backend->>DB: ReviewSet作成
    Backend->>DB: ReviewSetItem作成
    
    Backend->>UI: 復習セット返却
    UI->>Student: 復習問題表示
```

### 4.2 間隔反復学習スケジュール更新

```mermaid
flowchart TD
    A[問題解答完了] --> B[ReviewPerformance記録]
    B --> C[ReviewSchedule取得]
    
    C --> D{正解？}
    D -->|正解| E[連続正解数+1]
    D -->|不正解| F[連続正解数リセット]
    
    E --> G[容易度評価]
    G --> H{難易度判定}
    H -->|Easy| I[間隔延長+容易度因子↑]
    H -->|Good| J[標準間隔延長]
    H -->|Hard| K[間隔短縮+容易度因子↓]
    
    F --> L[間隔を1日にリセット]
    
    I --> M[次回復習日計算]
    J --> M
    K --> M
    L --> M
    
    M --> N[ReviewSchedule更新]
    N --> O[習得レベル判定]
    O --> P[完了]
```

---

## 5. 教科フィルタリングフロー

### 5.1 教科別データアクセス制御

```mermaid
flowchart TD
    A[API要求] --> B[ユーザー認証]
    B --> C[クラス所属確認]
    
    C --> D{生徒？}
    D -->|Yes| E[生徒のクラス取得]
    D -->|No| F{教師？}
    
    F -->|Yes| G[担当クラス取得]
    F -->|No| H[管理者権限]
    
    E --> I[クラス教科確認]
    G --> I
    H --> J[全教科アクセス可]
    
    I --> K[教科別フィルタ適用]
    K --> L[データ取得]
    
    L --> M{結果存在？}
    M -->|Yes| N[レスポンス返却]
    M -->|No| O[空の結果返却]
```

---

## 6. パフォーマンス最適化フロー

### 6.1 AI推薦キャッシュ戦略

```mermaid
sequenceDiagram
    participant Client as クライアント
    participant Cache as Redis Cache
    participant Backend as バックエンド
    participant AI as AI Engine

    Client->>Backend: 推薦要求
    Backend->>Cache: キャッシュ確認
    
    Cache->>Backend: キャッシュ結果
    
    alt キャッシュHit
        Backend->>Client: キャッシュから返却
    else キャッシュMiss
        Backend->>AI: AI推薦生成
        AI->>Backend: 推薦結果
        Backend->>Cache: 結果をキャッシュ(5分)
        Backend->>Client: 推薦結果返却
    end
```

### 6.2 大量データページネーション

```mermaid
flowchart TD
    A[リスト要求] --> B[パラメータ検証]
    B --> C[インデックス利用可能？]
    
    C -->|Yes| D[効率的クエリ実行]
    C -->|No| E[フルスキャン警告]
    
    D --> F[ページング計算]
    E --> F
    
    F --> G[LIMIT/OFFSET適用]
    G --> H[結果取得]
    
    H --> I[総件数計算]
    I --> J[メタデータ付与]
    J --> K[レスポンス生成]
```

---

## 7. エラーハンドリングフロー

### 7.1 音声入力エラー処理

```mermaid
flowchart TD
    A[音声入力エラー] --> B{エラー種別判定}
    
    B -->|マイク権限なし| C[権限要求UI表示]
    B -->|ネットワークエラー| D[ローカル保存]
    B -->|認識精度低| E[再録音提案]
    B -->|サーバーエラー| F[リトライキュー]
    
    D --> G[バックグラウンド再送信]
    F --> H[指数バックオフ]
    
    C --> I[ユーザー対応待ち]
    E --> J[ユーザー選択待ち]
    G --> K[成功時キュー削除]
    H --> L[最大リトライ後放棄]
```

### 7.2 AI推薦エラー処理

```mermaid
flowchart TD
    A[AI推薦エラー] --> B{エラー種別}
    
    B -->|OpenAI API限界| C[フォールバック推薦]
    B -->|データ不足| D[基本推薦算出]
    B -->|タイムアウト| E[キュー再登録]
    
    C --> F[ルールベース推薦]
    D --> G[人気度ベース推薦]
    E --> H[優先度下げて再実行]
    
    F --> I[推薦結果生成]
    G --> I
    H --> J[エラーカウント増加]
    
    J --> K{最大リトライ？}
    K -->|Yes| L[推薦失敗記録]
    K -->|No| M[再キュー登録]
```

---

## まとめ

これらのデータフロー図により、QuestEd新機能の各システム間でのデータの流れと処理の詳細が明確になります。実装時には以下の点に注意してください：

### 重要な設計原則

1. **非同期処理**: AI推薦や重い分析処理は非同期で実行
2. **フォールバック**: 外部API失敗時の代替処理
3. **キャッシュ**: 頻繁にアクセスされるデータの効率化
4. **セキュリティ**: 教科別アクセス制御の徹底
5. **エラーハンドリング**: ユーザビリティを損なわない例外処理

### パフォーマンス考慮事項

1. **データベースインデックス**: 頻繁な検索条件への最適化
2. **ページネーション**: 大量データの効率的な取得
3. **並列処理**: 独立した処理の同時実行
4. **監視**: ボトルネックの早期発見

これらのフローに基づいて、実際の実装を進めることができます。