# QuestEd 新機能API設計書

## API概要

QuestEd新機能追加に伴う包括的なREST API仕様書です。以下の4つの主要機能をカバーします：

1. **音声入力機能** - Web Speech APIによる音声認識
2. **自由進度学習ポータル** - 生徒主導の単元選択学習
3. **AI推薦システム** - GPT-4による学習コンテンツ推薦
4. **復習問題自動生成** - 弱点分析に基づく問題生成

## 認証・権限

### 認証方式
- **セッション認証**: Flask-Loginによるセッション管理
- **API キー認証**: 外部サービス連携用（オプション）
- **JWT トークン**: モバイルアプリ対応（将来拡張）

### 権限レベル
- **admin**: システム全体の管理権限
- **teacher**: 担当クラスの管理権限  
- **student**: 自分のデータのみアクセス可能

### 共通レスポンス形式

#### 成功レスポンス
```json
{
  "success": true,
  "data": {
    // 実際のデータ
  },
  "message": "操作が正常に完了しました",
  "timestamp": "2025-06-19T10:30:00Z"
}
```

#### エラーレスポンス
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "入力データに問題があります",
    "details": {
      "field": "student_id",
      "message": "必須フィールドです"
    }
  },
  "timestamp": "2025-06-19T10:30:00Z"
}
```

---

## 1. 音声入力API

### 1.1 音声テキスト変換記録

#### POST /api/speech/transcribe
音声認識結果をサーバーに記録

**リクエスト**
```json
{
  "session_id": "session_12345",
  "original_audio_text": "今日の授業では電流について学びました",
  "confidence_score": 0.92,
  "language_code": "ja-JP",
  "audio_duration": 5.2,
  "input_context": "activity_log",
  "context_id": 123
}
```

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "transcription_id": 456,
    "cleaned_text": "今日の授業では電流について学びました。",
    "is_processed": true,
    "suggestions": [
      "物理学", "電気回路", "オームの法則"
    ]
  }
}
```

**エラーケース**
- `400 Bad Request`: 音声データが不正
- `401 Unauthorized`: 認証エラー
- `429 Too Many Requests`: レート制限超過

---

### 1.2 音声入力履歴取得

#### GET /api/speech/history
生徒の音声入力履歴を取得

**クエリパラメータ**
```
?limit=20&offset=0&context=activity_log&start_date=2025-06-01&end_date=2025-06-19
```

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "transcriptions": [
      {
        "id": 456,
        "session_id": "session_12345",
        "original_audio_text": "今日の授業では電流について学びました",
        "cleaned_text": "今日の授業では電流について学びました。",
        "confidence_score": 0.92,
        "input_context": "activity_log",
        "created_at": "2025-06-19T10:30:00Z"
      }
    ],
    "pagination": {
      "total": 150,
      "limit": 20,
      "offset": 0,
      "has_next": true
    }
  }
}
```

---

### 1.3 音声設定管理

#### GET /api/speech/settings
音声入力設定を取得

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "is_enabled": true,
    "language_preference": "ja-JP",
    "auto_punctuation": true,
    "noise_reduction": true,
    "min_confidence": 0.50,
    "max_recording_time": 300
  }
}
```

#### PUT /api/speech/settings
音声入力設定を更新

**リクエスト**
```json
{
  "is_enabled": true,
  "language_preference": "ja-JP",
  "auto_punctuation": true,
  "min_confidence": 0.60
}
```

---

## 2. 自由進度学習API

### 2.1 学習単元管理

#### GET /api/units
利用可能な学習単元一覧を取得

**クエリパラメータ**
```
?subject_id=1&difficulty_level=2&class_id=7&include_progress=true
```

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "units": [
      {
        "id": 1,
        "unit_code": "SCI_ELEC_001",
        "title": "電流と電圧",
        "description": "電流と電圧の基本概念を学習します",
        "difficulty_level": 2,
        "estimated_hours": 2.5,
        "prerequisites": [5, 6],
        "learning_objectives": "電流と電圧の関係を理解する",
        "tags": ["物理", "電気", "基礎"],
        "subject": {
          "id": 1,
          "name": "理科",
          "code": "science"
        },
        "progress": {
          "status": "in_progress",
          "progress_percentage": 45.0,
          "completed_items": 9,
          "total_items": 20,
          "accuracy_rate": 85.0
        },
        "can_start": true,
        "unlock_reason": null
      }
    ],
    "pagination": {
      "total": 15,
      "limit": 20,
      "offset": 0
    }
  }
}
```

---

#### GET /api/units/{unit_id}
特定単元の詳細情報を取得

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "unit": {
      "id": 1,
      "unit_code": "SCI_ELEC_001",
      "title": "電流と電圧",
      "description": "電流と電圧の基本概念を学習します",
      "difficulty_level": 2,
      "estimated_hours": 2.5,
      "prerequisites": [
        {
          "id": 5,
          "title": "電気の基礎",
          "status": "completed"
        }
      ],
      "learning_objectives": "電流と電圧の関係を理解する",
      "problems": [
        {
          "id": 101,
          "title": "オームの法則",
          "difficulty": 2,
          "is_required": true,
          "order_index": 1
        }
      ],
      "progress": {
        "status": "in_progress",
        "progress_percentage": 45.0,
        "study_time_minutes": 85,
        "started_at": "2025-06-15T09:00:00Z",
        "last_activity_at": "2025-06-19T10:30:00Z"
      }
    }
  }
}
```

---

### 2.2 単元選択・進捗管理

#### POST /api/units/{unit_id}/select
単元を選択して学習開始

**リクエスト**
```json
{
  "class_id": 7,
  "notes": "電気について詳しく学びたいです"
}
```

**レスポンス（201 Created）**
```json
{
  "success": true,
  "data": {
    "selection_id": 789,
    "unit_id": 1,
    "status": "not_started",
    "can_start": true,
    "next_steps": [
      "前提単元「電気の基礎」の復習",
      "基本概念の理解確認"
    ]
  }
}
```

---

#### PUT /api/units/{unit_id}/progress
学習進捗を更新

**リクエスト**
```json
{
  "completed_items": 10,
  "correct_items": 8,
  "study_time_minutes": 30,
  "notes": "オームの法則が少し難しかったです"
}
```

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "progress_percentage": 50.0,
    "status": "in_progress",
    "accuracy_rate": 80.0,
    "achievements": [
      "初回学習完了",
      "正解率80%達成"
    ]
  }
}
```

---

### 2.3 学習推薦

#### GET /api/units/recommendations
AI推薦単元を取得

**クエリパラメータ**
```
?recommendation_type=unit&context=current_performance&limit=5
```

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "recommendations": [
      {
        "id": 1,
        "recommendation_type": "unit",
        "confidence_score": 0.85,
        "reasoning": "現在の学習パターンから、電磁気学の基礎を学習することをお勧めします",
        "recommended_items": [
          {
            "unit_id": 12,
            "title": "電磁気学の基礎",
            "priority": "high",
            "estimated_completion_time": "3時間"
          }
        ],
        "expires_at": "2025-06-26T10:30:00Z"
      }
    ]
  }
}
```

---

## 3. AI推薦システムAPI

### 3.1 推薦生成・管理

#### POST /api/recommendations/generate
新しい推薦を生成

**リクエスト**
```json
{
  "recommendation_type": "review",
  "context_data": {
    "recent_performance": "declining",
    "weak_categories": ["電気回路", "磁場"],
    "learning_style": "visual"
  },
  "max_items": 5
}
```

**レスポンス（201 Created）**
```json
{
  "success": true,
  "data": {
    "recommendation_id": 456,
    "recommendation_type": "review",
    "recommended_items": [
      {
        "type": "problem",
        "id": 123,
        "title": "基本的な電気回路",
        "reason": "電気回路の理解が不足しているため"
      }
    ],
    "confidence_score": 0.78,
    "reasoning": "最近のパフォーマンス低下を受けて、基礎的な復習を推奨します",
    "session_id": "rec_session_789"
  }
}
```

---

#### POST /api/recommendations/{recommendation_id}/feedback
推薦に対するフィードバック

**リクエスト**
```json
{
  "is_accepted": true,
  "feedback_text": "とても役立ちました",
  "perceived_difficulty": "appropriate"
}
```

---

### 3.2 学習パターン分析

#### GET /api/learning-patterns
生徒の学習パターンを取得

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "patterns": [
      {
        "pattern_type": "time_preference",
        "pattern_data": {
          "preferred_hours": [14, 15, 16],
          "peak_performance_time": "afternoon",
          "study_duration_optimal": 45
        },
        "confidence_level": 0.82,
        "sample_size": 67
      },
      {
        "pattern_type": "difficulty_preference",
        "pattern_data": {
          "preferred_difficulty": 2.3,
          "challenge_tolerance": "medium",
          "improvement_rate": 0.15
        },
        "confidence_level": 0.75,
        "sample_size": 120
      }
    ]
  }
}
```

---

## 4. 復習問題生成API

### 4.1 復習セット管理

#### POST /api/review/generate
復習問題セットを生成

**リクエスト**
```json
{
  "generation_type": "ai_generated",
  "target_weakness_areas": ["電気回路", "磁場"],
  "difficulty_level": 2,
  "total_problems": 10,
  "review_type": "weakness_focused",
  "estimated_time_minutes": 30
}
```

**レスポンス（201 Created）**
```json
{
  "success": true,
  "data": {
    "review_set_id": 789,
    "title": "電気回路・磁場 復習セット",
    "total_problems": 10,
    "estimated_time_minutes": 30,
    "status": "active",
    "expires_at": "2025-06-26T10:30:00Z",
    "problems_preview": [
      {
        "id": 101,
        "title": "オームの法則の応用",
        "difficulty_level": 2,
        "selection_reason": "電気回路の理解確認のため"
      }
    ]
  }
}
```

---

#### GET /api/review/sets
復習セット一覧を取得

**クエリパラメータ**
```
?status=active&review_type=weakness_focused&limit=10&offset=0
```

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "review_sets": [
      {
        "id": 789,
        "title": "電気回路・磁場 復習セット",
        "description": "弱点克服のための復習セット",
        "total_problems": 10,
        "completed_problems": 6,
        "progress_percentage": 60.0,
        "accuracy_rate": 75.0,
        "status": "active",
        "estimated_time_minutes": 30,
        "created_at": "2025-06-19T10:00:00Z",
        "expires_at": "2025-06-26T10:30:00Z"
      }
    ],
    "pagination": {
      "total": 5,
      "limit": 10,
      "offset": 0
    }
  }
}
```

---

#### GET /api/review/sets/{set_id}
復習セット詳細を取得

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "review_set": {
      "id": 789,
      "title": "電気回路・磁場 復習セット",
      "description": "弱点克服のための復習セット",
      "total_problems": 10,
      "status": "active",
      "items": [
        {
          "id": 1,
          "problem_id": 101,
          "order_index": 1,
          "title": "オームの法則の応用",
          "is_completed": true,
          "is_correct": true,
          "time_spent_seconds": 120,
          "weakness_category": "電気回路"
        }
      ],
      "performance_summary": {
        "completed_items": 6,
        "correct_items": 5,
        "accuracy_rate": 83.3,
        "average_time_per_problem": 140,
        "total_study_time": 840
      }
    }
  }
}
```

---

#### POST /api/review/sets/{set_id}/complete
復習セット完了処理

**リクエスト**
```json
{
  "completion_time_minutes": 25,
  "self_assessment": "medium",
  "feedback": "少し難しかったですが勉強になりました"
}
```

---

### 4.2 弱点分析

#### GET /api/weaknesses
生徒の弱点分析データを取得

**クエリパラメータ**
```
?subject_id=1&severity_level=3&is_active=true
```

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "weaknesses": [
      {
        "id": 123,
        "category": "電気回路",
        "subcategory": "直流回路",
        "weakness_type": "concept",
        "severity_level": 4,
        "confidence_score": 0.85,
        "accuracy_rate": 45.0,
        "total_attempts": 20,
        "correct_attempts": 9,
        "improvement_trend": "stable",
        "recommended_actions": [
          "基本概念の復習",
          "実習での理解確認",
          "類似問題の反復練習"
        ],
        "last_attempt_at": "2025-06-19T10:30:00Z"
      }
    ]
  }
}
```

---

## 5. 教科別管理API

### 5.1 教科情報取得

#### GET /api/subjects
教科一覧を取得

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "subjects": [
      {
        "id": 1,
        "name": "理科",
        "code": "science",
        "grade_level": "中学校",
        "is_active": true,
        "unit_count": 25,
        "problem_count": 150
      }
    ]
  }
}
```

---

#### GET /api/subjects/{subject_id}/categories
教科別問題カテゴリを取得

#### GET /api/subjects/{subject_id}/units
教科別学習単元を取得

#### GET /api/subjects/{subject_id}/problems
教科別問題一覧を取得

---

## 6. 共通機能API

### 6.1 統計情報

#### GET /api/stats/dashboard
生徒用ダッシュボード統計

**レスポンス（200 OK）**
```json
{
  "success": true,
  "data": {
    "learning_summary": {
      "active_units": 3,
      "completed_units": 12,
      "total_study_time_hours": 45.5,
      "accuracy_rate": 78.5
    },
    "recent_activity": {
      "speech_inputs_today": 8,
      "problems_solved_today": 15,
      "review_sets_completed": 2
    },
    "recommendations": {
      "pending_count": 2,
      "accepted_rate": 85.0
    },
    "weakness_analysis": {
      "critical_weaknesses": 1,
      "improving_areas": 3,
      "stable_areas": 5
    }
  }
}
```

---

### 6.2 設定管理

#### GET /api/settings/class/{class_id}
クラス設定を取得

#### PUT /api/settings/class/{class_id}
クラス設定を更新（教師のみ）

---

## エラーコード一覧

| コード | HTTPステータス | 説明 |
|--------|---------------|------|
| VALIDATION_ERROR | 400 | 入力データ検証エラー |
| UNAUTHORIZED | 401 | 認証エラー |
| FORBIDDEN | 403 | 権限エラー |
| NOT_FOUND | 404 | リソースが見つからない |
| CONFLICT | 409 | データ競合エラー |
| RATE_LIMIT_EXCEEDED | 429 | レート制限超過 |
| INTERNAL_ERROR | 500 | サーバー内部エラー |
| AI_SERVICE_ERROR | 503 | AI推薦サービスエラー |

## レート制限

- **一般API**: 100回/時間、1000回/日
- **音声入力API**: 50回/時間、300回/日  
- **AI推薦API**: 20回/時間、100回/日
- **復習生成API**: 10回/時間、50回/日

## セキュリティ考慮事項

1. **入力検証**: すべての入力データのサニタイゼーション
2. **認証**: セッションベース認証とCSRF保護
3. **認可**: ロールベースアクセス制御
4. **データ保護**: 音声データは保存せず、テキストのみ保存
5. **監査ログ**: 重要な操作のログ記録
6. **レート制限**: API濫用防止

## 拡張性考慮事項

1. **バージョニング**: APIバージョンの下位互換性維持
2. **ページネーション**: 大量データの効率的な取得
3. **キャッシュ**: AI推薦結果の5分間キャッシュ
4. **非同期処理**: 重い処理のキュー化
5. **モニタリング**: API使用状況の監視

このAPI仕様書に基づいて、実際のエンドポイント実装を進めることができます。