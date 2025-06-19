# QuestEd システム包括的ER図

## データベース設計図

```mermaid
erDiagram
    %% 既存システム - ユーザー管理
    schools ||--o{ school_years : "has"
    schools ||--o{ users : "belongs_to"
    schools ||--o{ curriculum_units : "school_specific"
    
    school_years ||--o{ class_groups : "contains"
    class_groups ||--o{ student_enrollments : "enrollments"
    
    users ||--o{ class_enrollments : "enrolled_in"
    users ||--o{ classes : "teaches (teacher)"
    users ||--o{ curriculum_units : "created_by"
    users ||--o{ chat_histories : "chats"
    users ||--o{ speech_transcriptions : "voice_inputs"
    users ||--o{ student_unit_selections : "studies"
    users ||--o{ ai_recommendations : "receives"
    users ||--o{ review_sets : "has_reviews"
    users ||--o{ student_weaknesses : "has_weaknesses"
    
    %% 教科とクラス管理
    subjects ||--o{ classes : "subject_classes"
    subjects ||--o{ curriculum_units : "curriculum_by_subject"
    subjects ||--o{ problem_categories : "categorized_by"
    subjects ||--o{ basic_knowledge_items : "problems_by_subject"
    subjects ||--o{ student_weaknesses : "weakness_by_subject"
    
    classes ||--o{ class_enrollments : "has_students"
    classes ||--o{ student_unit_selections : "class_context"
    classes ||--o{ class_learning_settings : "settings"
    classes ||--o{ learning_paths : "has_paths"
    classes ||--o{ chat_histories : "class_chats"
    
    %% カリキュラムシステム
    curriculum_units ||--o{ unit_item_mappings : "contains_problems"
    curriculum_units ||--o{ student_unit_selections : "selected_units"
    curriculum_units ||--o{ ai_recommendations : "recommended_units"
    curriculum_units ||--o{ learning_path_units : "path_units"
    curriculum_units }o--|| curriculum_units : "prerequisites"
    
    basic_knowledge_items ||--o{ unit_item_mappings : "mapped_to_units"
    basic_knowledge_items ||--o{ answer_records : "answered"
    basic_knowledge_items ||--o{ review_set_items : "review_problems"
    basic_knowledge_items ||--o{ review_schedules : "scheduled_reviews"
    basic_knowledge_items ||--o{ review_performance : "performance_data"
    
    problem_categories ||--o{ basic_knowledge_items : "categorizes"
    
    %% 音声入力システム
    speech_transcriptions }o--|| users : "student_voice"
    speech_settings }o--|| users : "voice_preferences"
    speech_statistics }o--|| users : "voice_stats"
    
    %% 自由進度学習システム
    student_unit_selections }o--|| curriculum_units : "selected_unit"
    student_unit_selections }o--|| classes : "class_context"
    
    class_learning_settings }o--|| classes : "class_settings"
    
    learning_paths }o--|| classes : "class_paths"
    learning_paths ||--o{ learning_path_units : "path_sequence"
    learning_path_units }o--|| curriculum_units : "unit_in_path"
    
    %% AI推薦システム
    ai_recommendations }o--|| users : "student_recommendations"
    
    learning_patterns }o--|| users : "student_patterns"
    recommendation_settings }o--|| users : "recommendation_prefs"
    recommendation_effectiveness }o--|| ai_recommendations : "measures_effectiveness"
    recommendation_queue }o--|| users : "queued_recommendations"
    
    %% 復習システム
    review_sets }o--|| users : "student_reviews"
    review_sets ||--o{ review_set_items : "contains_items"
    review_set_items }o--|| basic_knowledge_items : "review_problem"
    
    student_weaknesses }o--|| users : "student_analysis"
    student_weaknesses }o--|| subjects : "weakness_subject"
    
    review_schedules }o--|| users : "student_schedule"
    review_schedules }o--|| basic_knowledge_items : "scheduled_problem"
    
    review_performance }o--|| users : "student_performance"
    review_performance }o--|| review_sets : "performance_set"
    review_performance }o--|| basic_knowledge_items : "performance_problem"
    
    %% レガシーシステム連携
    curriculums ||--o{ curriculum_units : "legacy_curriculum_id"
    
    %% エンティティ定義
    schools {
        int id PK
        string name
        string code UK
        text description
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    school_years {
        int id PK
        int school_id FK
        string name
        date start_date
        date end_date
        boolean is_current
        datetime created_at
        datetime updated_at
    }
    
    class_groups {
        int id PK
        int school_year_id FK
        string name
        int grade_level
        int max_students
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    users {
        int id PK
        string username UK
        string email UK
        string password_hash
        enum role
        string full_name
        int school_id FK
        boolean is_active
        boolean email_verified
        datetime created_at
        datetime updated_at
    }
    
    subjects {
        int id PK
        string name
        string code UK
        text ai_system_prompt
        text learning_objectives
        text assessment_criteria
        string grade_level
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    classes {
        int id PK
        string name
        int teacher_id FK
        int subject_id FK
        text description
        int max_students
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    curriculum_units {
        int id PK
        int subject_id FK
        string unit_code UK
        string title
        text description
        int difficulty_level
        decimal estimated_hours
        json prerequisites
        text learning_objectives
        json tags
        int order_index
        boolean is_active
        int school_id FK
        int created_by FK
        int legacy_curriculum_id FK
        datetime created_at
        datetime updated_at
    }
    
    basic_knowledge_items {
        int id PK
        string item_code UK
        string title
        text question
        json answer_options
        string correct_answer
        text explanation
        int difficulty_level
        int subject_id FK
        int category_id FK
        json tags
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    problem_categories {
        int id PK
        string name
        int subject_id FK
        text description
        int parent_category_id FK
        int order_index
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    unit_item_mappings {
        int id PK
        int unit_id FK
        int item_id FK
        decimal weight
        int order_index
        boolean is_required
        datetime created_at
    }
    
    student_unit_selections {
        int id PK
        int student_id FK
        int unit_id FK
        int class_id FK
        enum status
        decimal progress_percentage
        int total_items
        int completed_items
        int correct_items
        datetime started_at
        datetime completed_at
        datetime last_activity_at
        int study_time_minutes
        text notes
        datetime created_at
        datetime updated_at
    }
    
    speech_transcriptions {
        int id PK
        int student_id FK
        string session_id
        text original_audio_text
        text cleaned_text
        decimal confidence_score
        string language_code
        decimal audio_duration
        string input_context
        int context_id
        boolean is_processed
        text error_message
        datetime created_at
        datetime updated_at
    }
    
    speech_settings {
        int id PK
        int student_id FK UK
        boolean is_enabled
        string language_preference
        boolean auto_punctuation
        boolean noise_reduction
        decimal min_confidence
        int max_recording_time
        datetime created_at
        datetime updated_at
    }
    
    speech_statistics {
        int id PK
        int student_id FK
        date date
        int total_inputs
        int successful_inputs
        decimal total_duration
        decimal average_confidence
        string most_used_context
        datetime created_at
        datetime updated_at
    }
    
    ai_recommendations {
        int id PK
        int student_id FK
        enum recommendation_type
        json context_data
        string ai_model
        text prompt_template
        text ai_response
        json recommended_items
        decimal confidence_score
        text reasoning
        boolean is_accepted
        boolean is_effective
        text feedback_text
        string session_id
        datetime created_at
        datetime updated_at
    }
    
    learning_patterns {
        int id PK
        int student_id FK
        enum pattern_type UK
        json pattern_data
        decimal confidence_level
        datetime last_analyzed_at
        int sample_size
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    recommendation_settings {
        int id PK
        int student_id FK UK
        boolean enable_ai_recommendations
        enum recommendation_frequency
        int max_recommendations_per_session
        decimal preferred_difficulty_adjustment
        boolean enable_challenge_problems
        boolean enable_review_recommendations
        enum privacy_level
        boolean feedback_required
        datetime created_at
        datetime updated_at
    }
    
    recommendation_effectiveness {
        int id PK
        int recommendation_id FK
        int student_id FK
        enum metric_type
        decimal before_value
        decimal after_value
        decimal improvement_rate
        int measurement_period_days
        datetime measured_at
    }
    
    recommendation_queue {
        int id PK
        int student_id FK
        enum trigger_event
        int priority
        json request_data
        enum status
        string assigned_worker
        text error_message
        int retry_count
        int max_retries
        datetime scheduled_at
        datetime started_at
        datetime completed_at
        datetime created_at
    }
    
    review_sets {
        int id PK
        int student_id FK
        string title
        text description
        enum generation_type
        json target_weakness_areas
        int difficulty_level
        int total_problems
        int estimated_time_minutes
        enum review_type
        enum status
        datetime expires_at
        boolean generated_by_ai
        json ai_generation_params
        datetime created_at
        datetime updated_at
    }
    
    review_set_items {
        int id PK
        int review_set_id FK
        int problem_id FK
        int order_index
        decimal weight
        decimal expected_difficulty
        string weakness_category
        text selection_reason
        boolean is_completed
        text student_answer
        boolean is_correct
        int time_spent_seconds
        int attempts_count
        datetime completed_at
    }
    
    student_weaknesses {
        int id PK
        int student_id FK
        int subject_id FK
        string category
        string subcategory
        enum weakness_type
        int severity_level
        decimal confidence_score
        int total_attempts
        int correct_attempts
        decimal accuracy_rate
        datetime last_attempt_at
        enum improvement_trend
        json recommended_actions
        json analysis_data
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    review_schedules {
        int id PK
        int student_id FK
        int problem_id FK
        int current_interval_days
        date next_review_date
        decimal easiness_factor
        int consecutive_correct
        int total_reviews
        date last_review_date
        enum last_performance
        enum mastery_level
        boolean is_suspended
        datetime created_at
        datetime updated_at
    }
    
    review_performance {
        int id PK
        int student_id FK
        int review_set_id FK
        int problem_id FK
        date review_date
        int response_time_seconds
        boolean is_correct
        enum difficulty_perceived
        enum confidence_level
        boolean hint_used
        int attempts_before_correct
        string study_session_id
        datetime created_at
    }
    
    class_learning_settings {
        int id PK
        int class_id FK UK
        boolean allow_free_progress
        boolean require_unit_order
        int max_concurrent_units
        decimal min_completion_rate
        boolean allow_unit_skip
        boolean show_difficulty_level
        boolean enable_peer_comparison
        int created_by FK
        datetime created_at
        datetime updated_at
    }
    
    learning_paths {
        int id PK
        int class_id FK
        string path_name
        text description
        boolean is_default
        boolean is_active
        int created_by FK
        datetime created_at
        datetime updated_at
    }
    
    learning_path_units {
        int id PK
        int path_id FK
        int unit_id FK
        int sequence_order
        boolean is_required
        json unlock_condition
    }
    
    curriculums {
        int id PK
        string title
        text description
        json data
        int class_id FK
        datetime created_at
        datetime updated_at
    }
    
    answer_records {
        int id PK
        int user_id FK
        int item_id FK
        text answer
        boolean is_correct
        int attempt_number
        datetime answered_at
    }
    
    chat_histories {
        int id PK
        int user_id FK
        int subject_id FK
        int class_id FK
        text message
        text ai_response
        datetime created_at
    }
    
    class_enrollments {
        int id PK
        int user_id FK
        int class_id FK
        datetime enrolled_at
    }
    
    student_enrollments {
        int id PK
        int student_id FK
        int class_group_id FK
        datetime enrolled_at
        boolean is_active
    }
```

## 重要な関係性の説明

### 1. 教科別管理
- `subjects` → `classes` → `users`: 教科別クラスでの生徒管理
- `subjects` → `curriculum_units`: 教科別の学習単元
- `subjects` → `basic_knowledge_items`: 教科別の問題

### 2. 自由進度学習フロー
- `users` → `student_unit_selections` → `curriculum_units`: 生徒の単元選択
- `curriculum_units` → `unit_item_mappings` → `basic_knowledge_items`: 単元と問題の紐付け
- `classes` → `class_learning_settings`: クラス別学習設定

### 3. AI推薦システム
- `users` → `learning_patterns`: 学習パターン分析
- `users` → `ai_recommendations`: AI推薦履歴
- `ai_recommendations` → `recommendation_effectiveness`: 効果測定

### 4. 復習システム
- `users` → `student_weaknesses`: 弱点分析
- `users` → `review_sets` → `review_set_items`: 復習問題セット
- `users` → `review_schedules`: 間隔反復学習スケジュール

### 5. 音声入力システム
- `users` → `speech_transcriptions`: 音声入力履歴
- `users` → `speech_settings`: 個人設定
- `users` → `speech_statistics`: 使用統計

### 6. レガシー連携
- `curriculum_units.legacy_curriculum_id` → `curriculums.id`: 既存カリキュラムとの連携

## データベース制約とインデックス

### 主要な制約
- **外部キー制約**: すべての関連テーブル間で適切な参照整合性
- **ユニーク制約**: 重複防止（student-unit-class組み合わせなど）
- **カスケード削除**: 生徒削除時の関連データ自動削除

### パフォーマンス最適化
- **複合インデックス**: 頻繁な検索条件に対応
- **部分インデックス**: 有効フラグによる絞り込み
- **JSON インデックス**: JSON フィールドの検索最適化

## スケーラビリティ考慮事項

### データ量予測
- **生徒数**: 1,000名規模
- **問題数**: 10,000問規模
- **音声入力**: 日次1,000件
- **AI推薦**: 日次500件

### パーティショニング戦略
- **時系列テーブル**: 月次パーティション（transcriptions, performance）
- **学校別テーブル**: school_id による水平分割

### キャッシュ戦略
- **Redis**: AI推薦結果、学習進捗
- **メモリキャッシュ**: 教科・単元マスタデータ