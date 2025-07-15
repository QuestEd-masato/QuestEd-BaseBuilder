# レッスン状態管理システム設計書

## 概要
3つの状態でレッスンの進捗を管理し、却下時の再申請機能を提供する。

## 状態定義

### 1. 未完了状態
```sql
approval_status = 'none' OR approval_status IS NULL
completion_request_date IS NULL
```
**表示**: 「完了申請」ボタン
**機能**: 条件を満たした時点で完了申請可能

### 2. 却下（再申請）状態  
```sql
approval_status = 'rejected'
completion_request_date IS NULL  -- 再申請を可能にする
```
**表示**: 「再申請」ボタン（赤色または警告色）
**機能**: 却下理由表示 + 再申請可能

### 3. 完了状態
```sql
approval_status = 'approved'
completion_request_date IS NOT NULL
approval_date IS NOT NULL
```
**表示**: 「完了済み」マーク（緑色チェック）
**機能**: 申請・変更不可

## データベース設計

### student_unit_selections テーブル拡張
```sql
ALTER TABLE student_unit_selections 
ADD COLUMN rejection_reason TEXT COMMENT '却下理由',
ADD COLUMN rejection_date DATETIME COMMENT '却下日時',
ADD COLUMN resubmission_count INT DEFAULT 0 COMMENT '再申請回数';
```

## フロントエンド実装

### 生徒ダッシュボード表示ロジック
```javascript
function getUnitStatusDisplay(unit) {
    if (unit.approval_status === 'approved') {
        return {
            text: '完了済み',
            button: '<span class="badge bg-success">✅ 完了</span>',
            class: 'completed'
        };
    } else if (unit.approval_status === 'rejected') {
        return {
            text: '再申請可能',
            button: `<button onclick="resubmitCompletion(${unit.id})" class="btn btn-warning btn-sm">🔄 再申請</button>`,
            class: 'rejected',
            reason: unit.rejection_reason
        };
    } else {
        return {
            text: '未完了',
            button: `<button onclick="requestCompletion(${unit.id})" class="btn btn-success btn-sm">✅ 完了申請</button>`,
            class: 'pending'
        };
    }
}
```

### 再申請機能
```javascript
function resubmitCompletion(unitId) {
    const confirmed = confirm('この単元を再申請しますか？\n前回の却下理由を確認して改善してから申請してください。');
    if (!confirmed) return;
    
    fetch(`/api/unit/${unitId}/resubmit-completion`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('再申請を送信しました', 'success');
            location.reload();
        } else {
            showToast(data.message || '再申請に失敗しました', 'error');
        }
    });
}
```

## バックエンド実装

### 却下処理API改良
```python
@task_management_bp.route("/api/submission/<submission_id>/reject", methods=['POST'])
def reject_unit_submission(submission_id):
    # ... 既存の権限チェック ...
    
    data = request.get_json() or {}
    rejection_reason = data.get('reason', '')
    
    # 却下処理
    unit_selection.approval_status = 'rejected'
    unit_selection.approved_by = current_user.id
    unit_selection.approval_date = datetime.utcnow()
    unit_selection.rejection_reason = rejection_reason
    unit_selection.rejection_date = datetime.utcnow()
    unit_selection.completion_request_date = None  # 再申請を可能にする
    
    db.session.commit()
```

### 再申請API
```python
@api_bp.route("/unit/<int:unit_id>/resubmit-completion", methods=['POST'])
@login_required
def resubmit_unit_completion(unit_id):
    """単元完了の再申請"""
    unit_selection = StudentUnitSelection.query.filter_by(
        student_id=current_user.id,
        unit_id=unit_id,
        approval_status='rejected'
    ).first()
    
    if not unit_selection:
        return jsonify({'status': 'error', 'message': '再申請可能な申請が見つかりません'}), 404
    
    # 再申請処理
    unit_selection.completion_request_date = datetime.utcnow()
    unit_selection.resubmission_count += 1
    unit_selection.approval_status = 'none'  # 承認待ち状態に戻す
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': '再申請を送信しました。教師の承認をお待ちください。'
    })
```

## 教師側表示改良

### 却下歴表示
```python
def get_pending_submissions():
    # ... 既存の処理 ...
    
    for request in unit_requests:
        submission_data = {
            'id': f"unit_{request.id}",
            'resubmission_count': request.resubmission_count or 0,
            'previous_rejection_reason': request.rejection_reason,
            'rejection_history': request.rejection_date,
            # ... 既存フィールド ...
        }
```

## UI/UX設計

### カラーコード
- **未完了**: グレー/ブルー (#6c757d / #0d6efd)
- **却下（再申請）**: オレンジ/黄色 (#fd7e14 / #ffc107)  
- **完了**: グリーン (#198754)

### アイコン
- **未完了**: ⭕ または 📝
- **却下（再申請）**: 🔄 または ⚠️
- **完了**: ✅ または 🎉

## 利点

1. **明確な状態管理**: 3状態で進捗が一目瞭然
2. **再挑戦の促進**: 却下されても再申請可能で学習継続を支援
3. **教師の指導効率**: 却下理由の記録で的確な指導が可能
4. **データ分析**: 再申請回数などで学習困難度を把握
5. **モチベーション維持**: 却下≠終了 の思想で学習意欲を保持

## 実装優先度

1. **Phase 1**: 基本的な3状態表示（今回実装）
2. **Phase 2**: 再申請機能とUI改善
3. **Phase 3**: 却下理由表示と履歴機能
4. **Phase 4**: 統計・分析機能の強化