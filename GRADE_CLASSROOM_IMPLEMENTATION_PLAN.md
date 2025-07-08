# 学年・学級フィールド実装計画書

*📅 作成日: 2025-01-08 | ステータス: 実装準備完了*

この文書は、QuestEdシステムに学年・学級フィールドを追加する包括的な実装計画です。既存データを保護しながら、段階的かつ安全に実装を進めます。

---

## 🎯 実装概要

### 目的
- 生徒・クラスに学年・学級フィールドを追加
- 学年・学級による検索・絞り込み機能を実装
- 教師がクラスに生徒を追加する際の利便性向上

### 実装方針
1. **データベース変更**: 新フィールド追加（users, classes テーブル）
2. **データ移行**: 既存クラス名から学年・学級情報を抽出
3. **UI更新**: 検索・絞り込み機能をテンプレートに追加
4. **機能拡張**: 学年・学級ベースの機能を段階的に追加

---

## 📊 現在のデータ状況分析

### データベース構造
```sql
-- 現在のテーブル構造
users: 46名（学生40名、教師5名、管理者1名）
classes: 複数クラス（具体的な数は要確認）
class_enrollments: 学生-クラス関係（1対多、29名が複数クラス所属）
```

### 既存クラス名パターン分析
```
確認済みパターン:
- "3年2組" (年組形式)
- "２年１組" (全角数字)
- "教科名 (科目)" (科目別クラス)
- "専門科目" (特別講座)
```

### 複数クラス所属の妥当性
- **問題なし**: 教科別クラス制のため自然な設計
- **29名が複数クラス所属**: 意図された機能
- **安全性**: 既存のapproval_statusシステムで品質管理済み

---

## 🏗️ 実装計画

### Phase 1: データベース準備 (即座実行可能)

#### 1.1 マイグレーション実行
```bash
# 1. マイグレーションファイル確認
cat /home/masat/claude-projects/QuestEd/migrations/versions/add_grade_classroom_fields.py

# 2. 現在のマイグレーション状況確認
cd /home/masat/claude-projects/QuestEd
python -c "from flask_migrate import current; from app import app; app.app_context().push(); print('Current revision:', current())"

# 3. マイグレーション実行
flask db upgrade

# 4. 結果確認
mysql -u QuestEd -p'QuestEd-03012025MySQL' -h localhost -P 3306 quested -e "DESCRIBE users;"
mysql -u QuestEd -p'QuestEd-03012025MySQL' -h localhost -P 3306 quested -e "DESCRIBE classes;"
```

#### 1.2 データ移行実行
```bash
# 1. データ移行スクリプト実行
cd /home/masat/claude-projects/QuestEd
python migrations/scripts/populate_grade_classroom.py

# 2. 結果確認
mysql -u QuestEd -p'QuestEd-03012025MySQL' -h localhost -P 3306 quested -e "
SELECT grade, classroom, COUNT(*) as count 
FROM users 
WHERE role='student' AND grade IS NOT NULL 
GROUP BY grade, classroom 
ORDER BY grade, classroom;
"
```

### Phase 2: UIテンプレート更新 (安全性: 🟢)

#### 2.1 生徒検索機能強化 (`templates/add_students.html`)

**現在の課題**:
- 生徒一覧が名前順のみ
- 大量の生徒から目的の生徒を見つけにくい

**改善内容**:
```html
<!-- 検索フィルター追加 -->
<div class="row mb-3">
    <div class="col-md-4">
        <label for="grade_filter" class="form-label">学年</label>
        <select id="grade_filter" class="form-select">
            <option value="">すべて</option>
            {% for grade in range(1, 13) %}
            <option value="{{ grade }}">{{ grade }}年</option>
            {% endfor %}
        </select>
    </div>
    <div class="col-md-4">
        <label for="classroom_filter" class="form-label">学級</label>
        <select id="classroom_filter" class="form-select">
            <option value="">すべて</option>
            {% for i in range(1, 7) %}
            <option value="{{ i }}組">{{ i }}組</option>
            {% endfor %}
            <option value="A組">A組</option>
            <option value="B組">B組</option>
            <option value="C組">C組</option>
        </select>
    </div>
    <div class="col-md-4">
        <label for="name_filter" class="form-label">名前</label>
        <input type="text" id="name_filter" class="form-control" placeholder="名前で検索">
    </div>
</div>

<!-- 強化された生徒リスト -->
<div id="students-list">
    {% for student in available_students %}
    <div class="student-item" data-grade="{{ student.grade }}" data-classroom="{{ student.classroom }}">
        <div class="form-check">
            <input class="form-check-input" type="checkbox" name="student_ids" value="{{ student.id }}" id="student_{{ student.id }}">
            <label class="form-check-label" for="student_{{ student.id }}">
                <div class="d-flex justify-content-between">
                    <div>
                        <strong>{{ student.username }}</strong>
                        <span class="text-muted">{{ student.full_name or student.username }}</span>
                    </div>
                    <div class="text-muted">
                        {% if student.grade %}{{ student.grade }}年{% endif %}
                        {% if student.classroom %}{{ student.classroom }}{% endif %}
                        {% if student.student_number %}<small>({{ student.student_number }})</small>{% endif %}
                    </div>
                </div>
            </label>
        </div>
    </div>
    {% endfor %}
</div>

<!-- JavaScript フィルター機能 -->
<script>
document.addEventListener('DOMContentLoaded', function() {
    const gradeFilter = document.getElementById('grade_filter');
    const classroomFilter = document.getElementById('classroom_filter');
    const nameFilter = document.getElementById('name_filter');
    const studentItems = document.querySelectorAll('.student-item');
    
    function filterStudents() {
        const gradeValue = gradeFilter.value;
        const classroomValue = classroomFilter.value;
        const nameValue = nameFilter.value.toLowerCase();
        
        studentItems.forEach(item => {
            const studentGrade = item.dataset.grade || '';
            const studentClassroom = item.dataset.classroom || '';
            const studentName = item.querySelector('strong').textContent.toLowerCase();
            
            const matchesGrade = !gradeValue || studentGrade === gradeValue;
            const matchesClassroom = !classroomValue || studentClassroom === classroomValue;
            const matchesName = !nameValue || studentName.includes(nameValue);
            
            item.style.display = (matchesGrade && matchesClassroom && matchesName) ? 'block' : 'none';
        });
    }
    
    gradeFilter.addEventListener('change', filterStudents);
    classroomFilter.addEventListener('change', filterStudents);
    nameFilter.addEventListener('input', filterStudents);
});
</script>
```

#### 2.2 クラス作成・編集フォーム更新

**対象ファイル**: `templates/create_class.html`, `templates/edit_class.html`

**追加内容**:
```html
<!-- 学年・学級フィールド追加 -->
<div class="row mb-3">
    <div class="col-md-6">
        <label for="grade" class="form-label">対象学年</label>
        <select class="form-select" id="grade" name="grade">
            <option value="">選択してください</option>
            {% for grade in range(1, 13) %}
            <option value="{{ grade }}" {% if class_obj and class_obj.grade == grade %}selected{% endif %}>
                {{ grade }}年
            </option>
            {% endfor %}
        </select>
    </div>
    <div class="col-md-6">
        <label for="classroom" class="form-label">学級</label>
        <select class="form-select" id="classroom" name="classroom">
            <option value="">選択してください</option>
            {% for i in range(1, 7) %}
            <option value="{{ i }}組" {% if class_obj and class_obj.classroom == i~'組' %}selected{% endif %}>
                {{ i }}組
            </option>
            {% endfor %}
            <option value="A組" {% if class_obj and class_obj.classroom == 'A組' %}selected{% endif %}>A組</option>
            <option value="B組" {% if class_obj and class_obj.classroom == 'B組' %}selected{% endif %}>B組</option>
            <option value="C組" {% if class_obj and class_obj.classroom == 'C組' %}selected{% endif %}>C組</option>
        </select>
    </div>
</div>
```

#### 2.3 クラス一覧表示強化

**対象ファイル**: `templates/teacher_classes.html`

**追加内容**:
```html
<!-- クラス一覧テーブル強化 -->
<div class="table-responsive">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>クラス名</th>
                <th>学年</th>
                <th>学級</th>
                <th>教科</th>
                <th>生徒数</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody>
            {% for class_obj in classes %}
            <tr>
                <td>{{ class_obj.name }}</td>
                <td>{% if class_obj.grade %}{{ class_obj.grade }}年{% endif %}</td>
                <td>{{ class_obj.classroom or '-' }}</td>
                <td>{{ class_obj.subject.name if class_obj.subject else '-' }}</td>
                <td>{{ class_obj.enrollments.count() }}名</td>
                <td>
                    <a href="{{ url_for('teacher_class_management.class_details', class_id=class_obj.id) }}" class="btn btn-sm btn-primary">詳細</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
```

### Phase 3: バックエンド機能拡張 (安全性: 🟡)

#### 3.1 クラス管理機能強化

**対象ファイル**: `app/teacher/modules/class_management.py`

**修正内容**:
```python
# create_class関数の拡張
@class_management_bp.route('/create_class', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_class():
    """クラス作成"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        subject_id = request.form.get('subject_id')
        schedule = request.form.get('schedule')
        location = request.form.get('location')
        
        # 新フィールド追加
        grade = request.form.get('grade')
        classroom = request.form.get('classroom')
        
        # 既存バリデーション...
        
        # 新しいクラスを作成
        new_class = Class(
            teacher_id=current_user.id,
            school_id=current_user.school_id,
            subject_id=subject_id,
            name=full_name,
            description=description,
            schedule=schedule,
            location=location,
            grade=int(grade) if grade else None,  # 新フィールド
            classroom=classroom if classroom else None  # 新フィールド
        )
        
        # 既存の保存処理...

# add_students関数の拡張
@class_management_bp.route('/class/<int:class_id>/add_students', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_students(class_id):
    """クラスに生徒を追加（学年・学級フィルター対応）"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック...
    
    if request.method == 'POST':
        # 既存の処理...
        pass
    
    # 学年・学級フィルターパラメータ
    grade_filter = request.args.get('grade')
    classroom_filter = request.args.get('classroom')
    name_filter = request.args.get('name')
    
    # まだクラスに追加されていない生徒を取得
    enrolled_student_ids = [e.student_id for e in ClassEnrollment.query.filter_by(class_id=class_id).all()]
    
    query = User.query.filter(
        User.role == 'student',
        User.school_id == current_user.school_id,
        User.is_approved == True,
        ~User.id.in_(enrolled_student_ids)
    )
    
    # フィルター適用
    if grade_filter:
        query = query.filter(User.grade == int(grade_filter))
    if classroom_filter:
        query = query.filter(User.classroom == classroom_filter)
    if name_filter:
        query = query.filter(User.username.contains(name_filter))
    
    available_students = query.order_by(User.grade, User.classroom, User.username).all()
    
    return render_template('add_students.html', 
                         class_obj=class_obj, 
                         available_students=available_students)
```

#### 3.2 生徒管理機能強化

**新機能**: 生徒プロフィール編集での学年・学級設定

**対象ファイル**: `app/admin/modules/user_management.py` (既存ファイル確認後)

### Phase 4: 高度な機能実装 (安全性: 🟠)

#### 4.1 学年・学級ベースの分析機能

**機能概要**:
- 学年別進捗分析
- 学級別成績比較
- 学年推移レポート

#### 4.2 一括操作機能

**機能概要**:
- 学年・学級一括でのカリキュラム配信
- 学級単位でのクラス作成
- 進級処理（学年更新）

---

## 🔄 実装スケジュール

### 第1週: データベース基盤
- **1日目**: マイグレーション実行
- **2日目**: データ移行実行・検証
- **3日目**: バックアップ・ロールバック手順確認

### 第2週: UI基本機能
- **1-2日目**: 生徒検索機能実装
- **3-4日目**: クラス作成・編集フォーム更新
- **5日目**: 基本機能テスト

### 第3週: バックエンド機能
- **1-3日目**: クラス管理機能拡張
- **4-5日目**: 生徒管理機能拡張

### 第4週: 統合テスト・調整
- **1-3日目**: 全機能統合テスト
- **4-5日目**: 不具合修正・調整

---

## ⚠️ リスク管理

### 高リスク項目
1. **データベーススキーマ変更**: 本番運用中のテーブル変更
2. **大量データ移行**: 既存データの整合性確保
3. **複雑なクエリ**: 性能への影響

### 対策
1. **段階的実装**: 小さな変更を積み重ね
2. **完全バックアップ**: 各段階でのデータ保護
3. **ロールバック準備**: 問題発生時の迅速な復旧

### 緊急時手順
```bash
# 1. アプリケーション停止
sudo systemctl stop quested

# 2. データベースバックアップから復旧
mysql -u QuestEd -p'QuestEd-03012025MySQL' -h localhost -P 3306 quested < backup_before_migration.sql

# 3. マイグレーション巻き戻し
flask db downgrade

# 4. アプリケーション再起動
sudo systemctl start quested
```

---

## 📊 成功指標

### Phase 1 成功指標
- [ ] マイグレーション正常完了
- [ ] データ移行90%以上成功
- [ ] 既存機能への影響なし

### Phase 2 成功指標
- [ ] 生徒検索機能正常動作
- [ ] フィルター機能レスポンス1秒以内
- [ ] モバイル対応確認

### Phase 3 成功指標
- [ ] 新機能エラー率0.1%以下
- [ ] 既存機能性能劣化なし
- [ ] 全テストケースパス

### 全体成功指標
- [ ] 教師の作業効率30%改善
- [ ] 生徒検索時間50%短縮
- [ ] システム安定性維持

---

## 📋 チェックリスト

### 実装前チェック
- [ ] データベース完全バックアップ
- [ ] 現在のマイグレーション状態確認
- [ ] 開発環境でのテスト完了
- [ ] ロールバック手順確認

### 実装中チェック
- [ ] 各段階でのバックアップ
- [ ] 動作確認・テスト実施
- [ ] ログ監視・エラー確認
- [ ] 性能測定・記録

### 実装後チェック
- [ ] 全機能動作確認
- [ ] 性能問題なし確認
- [ ] ユーザビリティテスト
- [ ] ドキュメント更新

---

**この実装計画書は、既存システムの安定性を保ちながら、学年・学級機能を段階的に追加する包括的なロードマップです。各段階での慎重な検証により、安全で効果的な機能拡張を実現します。**