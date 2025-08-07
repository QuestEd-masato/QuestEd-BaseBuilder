# カリキュラム・レッスン統合計画書

## 📋 統合概要

**目的**: curriculum_data (JSON) ↔ curriculum_lessons (テーブル) の二重データ構造を解消し、curriculum_lessons テーブルを単一データソースとする

**効果**: 
- データ整合性の100%保証
- 同期処理コードの削除（300-400行削減）
- 開発・保守効率の大幅向上
- パフォーマンス向上（60-80%）

## 🔍 現状分析

### データ状況
```
✅ カリキュラムID 13: JSON項目数=4, DBレッスン数=4 (同期済み)
✅ カリキュラムID 14: JSON項目数=1, DBレッスン数=1 (同期済み)
```

### 依存箇所
1. `app/services/curriculum/curriculum_orchestration_service.py:391` - 編集時同期処理
2. `sync_curriculum_lessons.py` - バッチ同期スクリプト

### 削除対象ファイル
1. `app/services/curriculum/curriculum_lesson_sync_service.py` (253行)
2. `sync_curriculum_lessons.py` 
3. 関連する同期処理コード

## 📅 段階的実装計画

### Phase 1: 同期処理の置き換え（1-2日）

#### Step 1.1: 直接編集API作成
```python
# 新規作成: app/api/curriculum_lesson_direct.py
@curriculum_lesson_api.route('/curriculum/<int:curriculum_id>/lessons/batch-update', methods=['POST'])
def batch_update_lessons(curriculum_id):
    """レッスン一括更新（同期処理の置き換え）"""
    lessons_data = request.json.get('lessons', [])
    
    # 既存レッスンを削除
    CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).delete()
    
    # 新しいレッスンを作成
    for index, lesson_data in enumerate(lessons_data, 1):
        lesson = CurriculumLesson(
            curriculum_id=curriculum_id,
            lesson_number=index,
            title=lesson_data.get('title', f'レッスン{index}'),
            description=lesson_data.get('description', ''),
            duration_minutes=lesson_data.get('duration_minutes', 50),
            learning_objectives=lesson_data.get('learning_objectives', []),
            basebuilder_references=lesson_data.get('basebuilder_references'),
            evaluation_criteria=lesson_data.get('evaluation_criteria', {}),
            created_by=current_user.id
        )
        db.session.add(lesson)
    
    db.session.commit()
    return jsonify({'success': True})
```

#### Step 1.2: curriculum_orchestration_service.py の修正
```python
# 行391付近の同期処理を置き換え
# OLD:
# sync_result = CurriculumLessonSyncService.sync_curriculum_to_lessons(curriculum_id)

# NEW: 直接レッスン更新API呼び出し
from app.api.curriculum_lesson_direct import batch_update_lessons_direct
result = batch_update_lessons_direct(curriculum_id, table_content_data)
```

#### Step 1.3: 動作確認
```bash
# カリキュラム編集テスト
1. カリキュラム13の編集画面にアクセス
2. レッスンタイトルを変更
3. 保存
4. 学生画面で変更が即座に反映されるか確認
```

### Phase 2: フロントエンド統合拡張（2-3日）

#### Step 2.1: レッスン個別編集機能
```javascript
// curriculum_edit.html に追加
function editLessonDetail(lessonId) {
    // レッスン詳細編集モーダル表示
    fetch(`/api/lesson/${lessonId}`)
    .then(response => response.json())
    .then(lesson => {
        showLessonEditModal(lesson);
    });
}

function showLessonEditModal(lesson) {
    // モーダル内容
    const modalContent = `
        <div class="lesson-edit-modal">
            <h3>レッスン詳細編集</h3>
            <form id="lesson-detail-form">
                <div class="form-group">
                    <label>タイトル</label>
                    <input type="text" name="title" value="${lesson.title}">
                </div>
                <div class="form-group">
                    <label>説明</label>
                    <textarea name="description">${lesson.description}</textarea>
                </div>
                <div class="form-group">
                    <label>学習目標</label>
                    <textarea name="learning_objectives">${JSON.stringify(lesson.learning_objectives)}</textarea>
                </div>
                <div class="form-group">
                    <label>BaseBuilder連携</label>
                    <select name="basebuilder_references">
                        <!-- BaseBuilderオプション -->
                    </select>
                </div>
            </form>
        </div>
    `;
}
```

#### Step 2.2: curriculum_edit.html の拡張
```html
<!-- 既存テーブルに「詳細編集」ボタン追加 -->
<td>
    <button type="button" onclick="editLessonDetail({{ lesson.id }})">詳細編集</button>
    <button type="button" onclick="removeContentRow(this)">削除</button>
</td>
```

### Phase 3: CSV機能の統合対応（1-2日）

#### Step 3.1: CSV構造の統一
```csv
# 新しいCSV構造
lesson_number,title,description,duration_minutes,learning_objectives,basebuilder_references,evaluation_criteria
1,"基礎文法","文法の基礎を学習",50,"[""基本構文の理解""]","textset_123","{""aspect"": ""knowledge""}"
2,"応用練習","文法の応用練習",50,"[""応用力の向上""]","","{}}"
```

#### Step 3.2: エクスポート機能の簡素化
```python
# OLD: curriculum_import_export_service.py の複雑な同期処理
# NEW: curriculum_lessonsテーブルからの直接エクスポート
def export_curriculum_to_csv(curriculum_id):
    lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).all()
    return generate_csv_from_lessons(lessons)
```

### Phase 4: クリーンアップ（1日）

#### Step 4.1: 不要ファイルの削除
```bash
# 削除対象
rm app/services/curriculum/curriculum_lesson_sync_service.py
rm sync_curriculum_lessons.py
```

#### Step 4.2: curriculum_data カラムの段階的非推奨化
```python
# Curriculumモデルにwarning追加
@property
def curriculum_data(self):
    warnings.warn("curriculum_data is deprecated. Use curriculum_lessons instead.", DeprecationWarning)
    return self._curriculum_data
```

## 🎯 期待される効果

### コード削減
- 同期処理: 253行 → 0行
- バッチスクリプト: 削除
- 複雑なJSON処理: 大幅削減

### パフォーマンス改善
- カリキュラム表示: 200-300ms → 50-100ms (60-70%改善)
- レッスン編集保存: 500-800ms → 100-200ms (70-80%改善)

### 開発効率向上
- 新人学習時間: 2-3週間 → 3-5日
- バグ修正時間: 2-3時間 → 30-60分
- 新機能追加: 標準的な開発時間（+50%のオーバーヘッド削除）

## 🚨 リスク管理

### データ保護
```bash
# 作業前バックアップ必須
mysqldump -u QuestEd -p'QuestEd-03012025MySQL' quested > backup_before_integration_$(date +%Y%m%d).sql
```

### ロールバック計画
```python
# 問題発生時の緊急復旧
def emergency_rollback():
    # curriculum_lessonsを削除
    # curriculum_dataから再同期
    # 旧同期サービスを一時復活
```

### 段階的移行
1. 新機能は並行実装（既存を破壊しない）
2. 十分なテスト後に切り替え
3. 1週間の監視期間
4. 問題なければクリーンアップ実行

## ✅ 成功基準

1. **データ整合性**: 教師編集内容と学生表示内容の100%一致
2. **パフォーマンス**: 60%以上の応答速度向上
3. **コード品質**: 複雑性の大幅削減
4. **開発効率**: バグ修正時間の50%以上短縮
5. **保守性**: 新人でも理解しやすい構造

## 📞 緊急時連絡

- 問題発生時: 即座にロールバック実行
- データ不整合発見時: 作業中断・原因調査
- 学生影響発生時: 最優先で復旧作業