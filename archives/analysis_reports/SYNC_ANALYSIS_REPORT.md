# 🔄 ローカルDB → RDS 同期分析レポート

**作成日時**: 2025年8月9日  
**方針**: 慎重かつ多角的な分析に基づく安全な同期計画

## 📊 差分分析結果

### **1. テーブル数の差異**
| 環境 | テーブル数 | 差分 |
|------|-----------|------|
| ローカル | 70 | ベース |
| RDS | 64 | -6テーブル |

### **2. 重要テーブルのデータ量比較**

| テーブル名 | ローカル | RDS | 差分 | 注意事項 |
|-----------|---------|-----|------|---------|
| users | 46 | 46 | 0 | ✅ 同一 |
| classes | 8 | 8 | 0 | ⚠️ データ内容に差異 |
| class_enrollments | 72 | 71 | -1 | 要確認 |
| curriculum_units | 0 | 8 | +8 | 🚨 RDSが多い |
| curriculums | 5 | 8 | +3 | 🚨 RDSが多い |
| student_unit_selections | 0 | 546 | +546 | 🚨 RDSが多い |

### **3. classesテーブルの詳細差分**

**共通項目**:
- id, teacher_id, name, created_at は同一
- subject_id, school_id も同一

**差分項目**:
| id | クラス名 | ローカル grade | RDS grade | ローカル classroom | RDS classroom |
|----|---------|---------------|-----------|-------------------|---------------|
| 2 | 3年2組 | 3 | NULL | 2組 | NULL |
| 4 | 2年３組 | 2 | NULL | 3組 | NULL |
| 6 | Test Class | NULL | NULL | NULL | NULL |
| 7 | ２年１組 | 2 | NULL | 1組 | NULL |
| 8 | ２年１組　理科 | 3 | NULL | 1組 | NULL |
| 9 | 2年３組 理科 | 2 | NULL | 3組 | NULL |
| 10 | 2年３組 (探究) | 2 | NULL | 3組 | NULL |
| 11 | １年１組 (理科) | 1 | NULL | 1組 | NULL |

## 🎯 同期戦略

### **優先度1: classesテーブルのgrade/classroom修復（安全）**
- **理由**: 明確な欠損データの補完
- **影響**: 表示改善のみ、機能影響なし
- **リスク**: 極小

### **優先度2: class_enrollmentsの差分調査（要調査）**
- **理由**: 1件の差分の原因特定が必要
- **対応**: 詳細調査後に判断

### **優先度3: カリキュラム関連データ（危険）**
- **理由**: RDSの方がデータ量が多い
- **懸念**: ローカルデータで上書きするとデータ損失
- **対応**: 同期対象外とする

## ⚠️ 重要な警告

### **同期してはいけないデータ**
1. **curriculum_units**: RDSに8件、ローカルに0件
2. **curriculums**: RDSに8件、ローカルに5件  
3. **student_unit_selections**: RDSに546件、ローカルに0件

これらはRDSで運用中に追加されたデータの可能性が高く、ローカルデータで上書きすると**重大なデータ損失**が発生します。

## 📝 推奨同期手順

### **Step 1: classesテーブルのgrade/classroom修復のみ**

```sql
-- 安全な部分同期（grade/classroomのみ更新）
UPDATE classes SET grade = 3, classroom = '2組' WHERE id = 2;
UPDATE classes SET grade = 2, classroom = '3組' WHERE id = 4;
-- id = 6 はNULLのまま（元々NULL）
UPDATE classes SET grade = 2, classroom = '1組' WHERE id = 7;
UPDATE classes SET grade = 3, classroom = '1組' WHERE id = 8;
UPDATE classes SET grade = 2, classroom = '3組' WHERE id = 9;
UPDATE classes SET grade = 2, classroom = '3組' WHERE id = 10;
UPDATE classes SET grade = 1, classroom = '1組' WHERE id = 11;
```

### **Step 2: class_enrollmentsの差分確認**

差分の1件を特定してから判断

### **Step 3: 新規テーブルの調査**

ローカルにあってRDSにない6テーブルの内容を確認してから判断

## 🛡️ 安全対策

1. **バックアップ済み**: `classes_backup_20250809`テーブル作成完了
2. **部分同期**: 全体同期ではなく、必要な部分のみ
3. **段階実行**: 一度に全て実行せず、段階的に確認
4. **ロールバック準備**: 問題時の復旧SQL準備

## 🎯 結論

**推奨アクション**: classesテーブルのgrade/classroomデータのみを同期し、他のテーブルは触らない

**理由**:
- 明確な欠損データの修復は安全
- RDSに多いデータは運用中の追加データの可能性大
- 全体同期は危険（データ損失リスク）