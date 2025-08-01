-- Phase1: レッスンシステム テストデータ作成スクリプト
-- 作成日: 2025-07-30
-- 目的: 既存カリキュラムID 13「Web開発基礎講座」にレッスンとタスクを追加

-- 使用するユーザーIDと既存データの確認
-- カリキュラムID: 13 (Web開発基礎講座)
-- 教師ID: カリキュラムのteacher_idを使用

-- レッスンデータ挿入（5レッスン）
INSERT INTO curriculum_lessons (
    curriculum_id, lesson_number, title, description, lesson_type, 
    duration_minutes, created_at, updated_at
) VALUES
-- レッスン1: HTML基礎
(13, 1, 'HTML基礎', 'HTMLの基本構造とタグについて学習します', 'lecture', 
 50, NOW(), NOW()),

-- レッスン2: CSS基礎
(13, 2, 'CSS基礎', 'CSSの基本とスタイリングについて学習します', 'practice', 
 50, NOW(), NOW()),

-- レッスン3: JavaScript入門
(13, 3, 'JavaScript入門', '動的なWebページ作成の基礎を学習します', 'practice', 
 50, NOW(), NOW()),

-- レッスン4: Webサイト制作演習
(13, 4, 'Webサイト制作演習', '学んだ知識を使って簡単なWebサイトを作成します', 'experiment', 
 50, NOW(), NOW()),

-- レッスン5: 発表とレビュー
(13, 5, '作品発表とコードレビュー', '制作したWebサイトを発表し、相互レビューを行います', 'presentation', 
 50, NOW(), NOW());

-- タスクデータ挿入
-- レッスン1のタスク
INSERT INTO lesson_tasks (
    lesson_id, task_number, title, description, instructions, 
    estimated_minutes, is_required
) VALUES
-- HTMLタスク
((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 1), 
 1, 'HTML文書の作成', '基本的なHTML文書を作成する', 
 '1. 新しいHTMLファイルを作成\n2. DOCTYPE宣言を記述\n3. html、head、bodyタグを正しく配置\n4. タイトルを設定', 
 15, 1),

((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 1), 
 2, '見出しと段落の練習', '様々な見出しレベルと段落を使った文書作成', 
 '1. h1からh6までの見出しを使用\n2. 段落タグで本文を作成\n3. 適切な階層構造を意識', 
 10, 1),

((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 1), 
 3, 'リンクとリストの実装', 'ハイパーリンクとリスト要素の実装', 
 '1. 外部サイトへのリンクを作成\n2. 順序付きリストと順序なしリストを作成\n3. ネストしたリストに挑戦', 
 10, 1),

-- レッスン2のタスク（CSS）
((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 2), 
 1, 'CSSファイルの作成と連携', '外部CSSファイルの作成とHTMLへの適用', 
 '1. style.cssファイルを作成\n2. HTMLファイルにlinkタグで読み込み\n3. 基本的なスタイルを適用', 
 10, 1),

((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 2), 
 2, 'セレクタの練習', '様々なセレクタを使ったスタイリング', 
 '1. 要素セレクタでスタイル適用\n2. クラスセレクタを使用\n3. IDセレクタを使用\n4. 複合セレクタに挑戦', 
 15, 1),

((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 2), 
 3, 'レイアウトの実装', 'FlexboxまたはGridを使ったレイアウト', 
 '1. Flexboxでヘッダーを作成\n2. メインコンテンツとサイドバーを配置\n3. レスポンシブ対応を考慮', 
 20, 0),

-- レッスン3のタスク（JavaScript）
((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 3), 
 1, '変数と関数の基礎', 'JavaScriptの基本構文を練習', 
 '1. 変数を宣言して値を代入\n2. 関数を定義\n3. 関数を呼び出して結果を確認', 
 10, 1),

((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 3), 
 2, 'DOM操作の実践', 'HTML要素をJavaScriptで操作', 
 '1. getElementByIdで要素を取得\n2. 要素の内容を変更\n3. スタイルを動的に変更', 
 15, 1),

((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 3), 
 3, 'イベント処理の実装', 'ユーザー操作に反応する機能を実装', 
 '1. ボタンクリックイベントを設定\n2. フォーム入力の値を取得\n3. 結果を画面に表示', 
 15, 1),

-- レッスン4のタスク（制作演習）
((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 4), 
 1, 'サイト設計', 'Webサイトの構成を設計', 
 '1. サイトマップを作成\n2. ワイヤーフレームを描く\n3. 必要なページをリストアップ', 
 20, 1),

((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 4), 
 2, 'コーディング実装', '設計に基づいてコーディング', 
 '1. HTMLで構造を作成\n2. CSSでデザインを適用\n3. JavaScriptで動きを追加', 
 25, 1),

-- レッスン5のタスク（発表）
((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 5), 
 1, 'プレゼン資料作成', '発表用の資料を準備', 
 '1. 作品の特徴をまとめる\n2. 工夫した点を説明\n3. デモの流れを計画', 
 15, 1),

((SELECT id FROM curriculum_lessons WHERE curriculum_id = 13 AND lesson_number = 5), 
 2, '相互レビュー', '他の生徒の作品をレビュー', 
 '1. 良い点を3つ見つける\n2. 改善提案を2つ考える\n3. 建設的なフィードバックを記述', 
 20, 1);

-- 動作確認用のSELECT文
-- SELECT * FROM curriculum_lessons WHERE curriculum_id = 13;
-- SELECT lt.* FROM lesson_tasks lt JOIN curriculum_lessons cl ON lt.lesson_id = cl.id WHERE cl.curriculum_id = 13;