-- MySQL dump 10.13  Distrib 8.0.42, for Linux (x86_64)
--
-- Host: localhost    Database: quested
-- ------------------------------------------------------
-- Server version	8.0.42-0ubuntu0.24.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `curriculums`
--

DROP TABLE IF EXISTS `curriculums`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `curriculums` (
  `id` int NOT NULL AUTO_INCREMENT,
  `class_id` int NOT NULL,
  `subject_id` int DEFAULT NULL,
  `teacher_id` int NOT NULL,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `total_hours` int DEFAULT NULL,
  `has_fieldwork` tinyint(1) DEFAULT NULL,
  `fieldwork_count` int DEFAULT NULL,
  `has_presentation` tinyint(1) DEFAULT NULL,
  `presentation_format` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `group_work_level` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `external_collaboration` tinyint(1) DEFAULT NULL,
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `format` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'json' COMMENT 'データ形式: json(レガシー) | table(新形式)',
  `is_converted_to_units` tinyint(1) DEFAULT '0' COMMENT 'カリキュラムが単元に変換済みかどうか',
  `units_conversion_date` datetime DEFAULT NULL COMMENT '単元への変換日時',
  `curriculum_data` json DEFAULT NULL COMMENT 'カリキュラムの詳細データ',
  `created_by` int DEFAULT NULL COMMENT '作成者ID',
  PRIMARY KEY (`id`),
  KEY `class_id` (`class_id`),
  KEY `teacher_id` (`teacher_id`),
  KEY `subject_id` (`subject_id`),
  KEY `idx_is_converted` (`is_converted_to_units`),
  KEY `fk_curriculums_created_by` (`created_by`),
  CONSTRAINT `curriculums_ibfk_1` FOREIGN KEY (`class_id`) REFERENCES `classes` (`id`),
  CONSTRAINT `curriculums_ibfk_2` FOREIGN KEY (`teacher_id`) REFERENCES `users` (`id`),
  CONSTRAINT `curriculums_ibfk_3` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_curriculums_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `curriculums`
--

LOCK TABLES `curriculums` WRITE;
/*!40000 ALTER TABLE `curriculums` DISABLE KEYS */;
INSERT INTO `curriculums` VALUES (1,2,NULL,5,'北陸製菓のお菓子の魅力を発信しよう！','',20,1,1,1,'プレゼンテーション','ハイブリッド',1,'{\"phases\": [{\"phase\": \"準備期\", \"weeks\": [{\"week\": \"第1週\", \"hours\": 2, \"theme\": \"大テーマの理解と問いの設定\", \"activities\": \"大テーマの説明と理解、グループ分け、問いの設定についての議論\", \"teacher_support\": \"大テーマの詳細説明、問い設定のガイダンス\", \"evaluation\": \"問い設定のクオリティ、グループ内のコミュニケーション\"}]}, {\"phase\": \"探究前半\", \"weeks\": [{\"week\": \"第2-4週\", \"hours\": 6, \"theme\": \"情報収集と初期分析\", \"activities\": \"北陸製菓のお菓子についての情報収集、分析の試み、フィールドワークの計画\", \"teacher_support\": \"情報収集と分析の方法の指導、フィールドワークの計画の確認\", \"evaluation\": \"情報収集と分析の進捗、フィールドワークの計画の具体性\"}]}, {\"phase\": \"フィールドワーク\", \"weeks\": [{\"week\": \"第5週\", \"hours\": 2, \"theme\": \"フィールドワーク\", \"activities\": \"北陸製菓のお菓子を製造する工場訪問、インタビュー\", \"teacher_support\": \"フィールドワークの実施と観察のガイダンス\", \"evaluation\": \"フィールドワークの成果（情報収集の具体性、新たな発見）\"}]}, {\"phase\": \"探究後半\", \"weeks\": [{\"week\": \"第6-8週\", \"hours\": 6, \"theme\": \"情報の整理・分析と発表の準備\", \"activities\": \"フィールドワークの結果を含む情報の整理・分析、発表の準備\", \"teacher_support\": \"情報の整理・分析の方法の指導、発表の準備のガイダンス\", \"evaluation\": \"情報の整理・分析の進捗、発表の準備の具体性\"}]}, {\"phase\": \"まとめ\", \"weeks\": [{\"week\": \"第9-10週\", \"hours\": 4, \"theme\": \"発表会と反省\", \"activities\": \"発表会の実施、反省会\", \"teacher_support\": \"発表会の進行と評価、反省会の進行\", \"evaluation\": \"発表のクオリティ、反省の深さ\"}]}], \"rubric_suggestion\": [{\"category\": \"問いの設定\", \"description\": \"探究の出発点となる問いの設定の質を評価します。\", \"levels\": [{\"level\": \"S\", \"description\": \"自分たちの興味・関心を踏まえ、具体的で深い問いを設定している。\"}, {\"level\": \"A\", \"description\": \"具体的な問いを設定しているが、深さはまだ足りない。\"}, {\"level\": \"B\", \"description\": \"問いを設定しているが、具体性や深さに欠ける。\"}, {\"level\": \"C\", \"description\": \"問いの設定が不十分で、改善が必要。\"}]}, {\"category\": \"情報収集\", \"description\": \"情報収集の過程と結果を評価します。\", \"levels\": [{\"level\": \"S\", \"description\": \"多角的に情報を収集し、その信憑性を確認している。\"}, {\"level\": \"A\", \"description\": \"情報を収集しているが、その信憑性の確認が不十分。\"}, {\"level\": \"B\", \"description\": \"情報を収集しているが、多角的な視点が欠ける。\"}, {\"level\": \"C\", \"description\": \"情報の収集が不十分で、改善が必要。\"}]}, {\"category\": \"分析力\", \"description\": \"情報を整理し、分析・解釈できる力を評価します。\", \"levels\": [{\"level\": \"S\", \"description\": \"情報を的確に整理し、深い分析・解釈を行っている。\"}, {\"level\": \"A\", \"description\": \"情報を整理し、分析・解釈は行っているが、深さに欠ける。\"}, {\"level\": \"B\", \"description\": \"情報の整理や分析・解釈が不十分。\"}, {\"level\": \"C\", \"description\": \"情報の整理や分析・解釈がほとんど行われていない。\"}]}, {\"category\": \"発表力\", \"description\": \"自分たちの探究結果を他者に伝える力を評価します。\", \"levels\": [{\"level\": \"S\", \"description\": \"自分たちの探究結果を明確かつ魅力的に伝えている。\"}, {\"level\": \"A\", \"description\": \"自分たちの探究結果を伝えているが、明確さや魅力に欠ける。\"}, {\"level\": \"B\", \"description\": \"自分たちの探究結果を伝えているが、理解しやすさに欠ける。\"}, {\"level\": \"C\", \"description\": \"自分たちの探究結果の発表が不十分で、改善が必要。\"}]}]}','2025-04-14 14:28:41','2025-04-14 14:28:41','json',0,NULL,NULL,NULL),(2,2,NULL,5,'hokkaプロジェクト','',20,1,1,1,'プレゼンテーション','ハイブリッド',1,'{\"phases\": [{\"phase\": \"準備期\", \"weeks\": [{\"week\": \"第1週\", \"hours\": 2, \"theme\": \"大テーマの理解と問いの設定\", \"activities\": \"北陸製菓のお菓子についての情報共有、問いや課題の設定\", \"teacher_support\": \"テーマの深堀りのための質問、問い設定のサポート\", \"evaluation\": \"活動記録と問いの設定のルーブリック評価\"}]}, {\"phase\": \"探究前半\", \"weeks\": [{\"week\": \"第2～3週\", \"hours\": 4, \"theme\": \"情報収集\", \"activities\": \"北陸のお菓子についての情報収集（文献調査、ウェブリサーチ等）\", \"teacher_support\": \"情報収集方法の指導、情報源の信頼性の確認\", \"evaluation\": \"活動記録と情報収集のルーブリック評価\"}]}, {\"phase\": \"フィールドワーク\", \"weeks\": [{\"week\": \"第4週\", \"hours\": 3, \"theme\": \"現地調査\", \"activities\": \"製菓工場見学、製品試食、製菓職人へのインタビュー\", \"teacher_support\": \"現地での行動マナーの指導、インタビューの準備\", \"evaluation\": \"活動記録とフィールドワークのルーブリック評価\"}]}, {\"phase\": \"探究後半\", \"weeks\": [{\"week\": \"第5～7週\", \"hours\": 7, \"theme\": \"情報整理・分析\", \"activities\": \"収集した情報の整理、分析、お菓子の魅力の抽出\", \"teacher_support\": \"情報の整理・分析方法の指導\", \"evaluation\": \"活動記録と情報整理・分析のルーブリック評価\"}]}, {\"phase\": \"まとめ\", \"weeks\": [{\"week\": \"第8週\", \"hours\": 2, \"theme\": \"プレゼンテーションの準備\", \"activities\": \"プレゼンテーションの準備（資料作成、リハーサル等）\", \"teacher_support\": \"プレゼンテーションの構成・表現方法の指導\", \"evaluation\": \"活動記録とプレゼンテーション準備のルーブリック評価\"}, {\"week\": \"第9週\", \"hours\": 2, \"theme\": \"プレゼンテーション\", \"activities\": \"最終プレゼンテーションの実施\", \"teacher_support\": \"プレゼンテーションの進行管理\", \"evaluation\": \"活動記録とプレゼンテーションのルーブリック評価\"}]}], \"rubric_suggestion\": [{\"category\": \"問いの設定\", \"description\": \"北陸製菓のお菓子の魅力についての問いを設定する能力\", \"levels\": [{\"level\": \"S\", \"description\": \"具体的で深い問いを自立して設定し、その重要性を説明できる\"}, {\"level\": \"A\", \"description\": \"具体的な問いを設定し、その重要性を説明できる\"}, {\"level\": \"B\", \"description\": \"問いを設定できるが、その重要性を十分に説明できない\"}, {\"level\": \"C\", \"description\": \"問いの設定が難しく、その重要性を説明できない\"}]}, {\"category\": \"情報収集\", \"description\": \"北陸製菓のお菓子に関する情報を多角的に収集する能力\", \"levels\": [{\"level\": \"S\", \"description\": \"多角的に情報を収集し、その情報源の信頼性を評価できる\"}, {\"level\": \"A\", \"description\": \"多角的に情報を収集できるが、その情報源の信頼性の評価が不十分\"}, {\"level\": \"B\", \"description\": \"情報を収集できるが、その範囲や深さが不十分\"}, {\"level\": \"C\", \"description\": \"情報収集が難しく、その範囲や深さが不十分\"}]}, {\"category\": \"情報整理・分析\", \"description\": \"収集した情報を整理・分析し、製菓の魅力を抽出する能力\", \"levels\": [{\"level\": \"S\", \"description\": \"収集した情報を的確に整理・分析し、魅力を明確に抽出できる\"}, {\"level\": \"A\", \"description\": \"収集した情報を整理・分析し、魅力を抽出できる\"}, {\"level\": \"B\", \"description\": \"収集した情報の整理・分析が不十分で、魅力の抽出が難しい\"}, {\"level\": \"C\", \"description\": \"情報の整理・分析が難しく、魅力の抽出が難しい\"}]}, {\"category\": \"プレゼンテーション\", \"description\": \"分析結果をもとに、製菓の魅力を発信するプレゼンテーション能力\", \"levels\": [{\"level\": \"S\", \"description\": \"分析結果をもとに、魅力を効果的に発信するプレゼンテーションを行える\"}, {\"level\": \"A\", \"description\": \"分析結果をもとに、魅力を発信するプレゼンテーションを行える\"}, {\"level\": \"B\", \"description\": \"分析結果をもとに、魅力を発信するプレゼンテーションが一部不十分\"}, {\"level\": \"C\", \"description\": \"プレゼンテーションが難しく、魅力の発信が不十分\"}]}]}','2025-04-14 14:34:42','2025-04-14 14:34:42','json',0,NULL,NULL,NULL),(3,2,NULL,5,'hokkaプロジェクト','',20,1,1,1,'プレゼンテーション','ハイブリッド',1,'{\"phases\": [{\"phase\": \"準備期\", \"weeks\": [{\"week\": \"第1週\", \"hours\": 2, \"theme\": \"プロジェクトの理解と問いの設定\", \"activities\": \"大テーマについての理解を深め、自分たちが解き明かしたい問いを設定する。\", \"teacher_support\": \"大テーマの背景や意義を説明し、問い設定の方法を指導する。\", \"evaluation\": \"活動記録と問いの設定の適切さをルーブリック評価で確認する。\"}]}, {\"phase\": \"探究前半\", \"weeks\": [{\"week\": \"第2週\", \"hours\": 2, \"theme\": \"情報収集\", \"activities\": \"設定した問いに対する情報収集を行う。インターネットや図書館を利用し、北陸地方の製菓業の歴史や特徴などを調査する。\", \"teacher_support\": \"情報収集の方法を指導し、必要に応じて情報の信頼性などを確認する。\", \"evaluation\": \"活動記録と情報収集の質や深さをルーブリック評価で確認する。\"}, {\"week\": \"第3週\", \"hours\": 2, \"theme\": \"フィールドワーク\", \"activities\": \"製菓工場や店舗を訪れ、現地の情報収集およびインタビューを行う。\", \"teacher_support\": \"フィールドワークの実施計画を確認し、現地での行動マナーやインタビューの進め方を指導する。\", \"evaluation\": \"活動記録とフィールドワークでの収集情報の質や深さをルーブリック評価で確認する。\"}]}, {\"phase\": \"探究後半\", \"weeks\": [{\"week\": \"第4週\", \"hours\": 3, \"theme\": \"情報の整理・分析\", \"activities\": \"収集した情報を整理し、分析を行う。その結果をもとに、北陸製菓のお菓子の魅力をどう発信するかの方法を考える。\", \"teacher_support\": \"情報の整理・分析方法を指導し、発信方法の提案をサポートする。\", \"evaluation\": \"活動記録と情報の整理・分析の質や深さ、発信方法の提案の適切さをルーブリック評価で確認する。\"}, {\"week\": \"第5週\", \"hours\": 3, \"theme\": \"プレゼンテーションの準備\", \"activities\": \"考えた発信方法をもとに、プレゼンテーションの準備を行う。スライド作成や発表練習などを行う。\", \"teacher_support\": \"プレゼンテーションの作成方法や発表のポインツを指導する。\", \"evaluation\": \"活動記録とプレゼンテーションの準備の進行状況をルーブリック評価で確認する。\"}]}, {\"phase\": \"まとめ\", \"weeks\": [{\"week\": \"第6週\", \"hours\": 2, \"theme\": \"プレゼンテーション\", \"activities\": \"プレゼンテーションを実施し、自分たちが考えた北陸製菓のお菓子の魅力とその発信方法を発表する。\", \"teacher_support\": \"プレゼンテーションの進行をサポートし、質疑応答の時間を設ける。\", \"evaluation\": \"活動記録とプレゼンテーションの質や内容の適切さをルーブリック評価で確認する。\"}]}], \"rubric_suggestion\": [{\"category\": \"問いの設定\", \"description\": \"自分たちが解き明かしたい問いを明確に設定できるか\", \"levels\": [{\"level\": \"A\", \"description\": \"大テーマに対する深い理解に基づく、具体的で答えが出るような問いを設定できる。\"}, {\"level\": \"B\", \"description\": \"大テーマに対する理解に基づき、問いを設定できる。ただし、具体性や答えやすさに若干の課題がある。\"}, {\"level\": \"C\", \"description\": \"大テーマに対する理解が浅く、問いの設定に課題がある。\"}]}, {\"category\": \"情報収集\", \"description\": \"設定した問いに対する情報収集が適切に行えるか\", \"levels\": [{\"level\": \"A\", \"description\": \"問いに対して幅広く深く情報を収集できる。情報の信頼性を確認し、必要な情報を選別する能力がある。\"}, {\"level\": \"B\", \"description\": \"問いに対して一定の情報を収集できる。ただし、情報の幅や深さ、信頼性の確認に若干の課題がある。\"}, {\"level\": \"C\", \"description\": \"問いに対する情報収集が十分でない、または情報の信頼性の確認が不十分である。\"}]}, {\"category\": \"情報の整理・分析\", \"description\": \"収集した情報を適切に整理・分析し、その結果をもとに具体的な行動計画を立てられるか\", \"levels\": [{\"level\": \"A\", \"description\": \"情報を適切に整理・分析し、その結果をもとに具体的で実現可能な行動計画を立てることができる。\"}, {\"level\": \"B\", \"description\": \"情報を一定の基準で整理・分析し、行動計画を立てることができる。ただし、その具体性や実現可能性に若干の課題がある。\"}, {\"level\": \"C\", \"description\": \"情報の整理・分析や行動計画の立案に課題がある。\"}]}, {\"category\": \"表現力\", \"description\": \"プレゼンテーションを通じて、自分たちの考えを適切に表現・発信できるか\", \"levels\": [{\"level\": \"A\", \"description\": \"自分たちの考えを明確に表現し、聞き手に理解されやすい形で発信することができる。スライドや資料の作成も適切に行える。\"}, {\"level\": \"B\", \"description\": \"自分たちの考えを一定の形で表現・発信することができる。ただし、その明確さや聞き手への配慮、資料作成に若干の課題がある。\"}, {\"level\": \"C\", \"description\": \"自分たちの考えの表現・発信や資料作成に課題がある。\"}]}]}','2025-04-14 14:40:28','2025-04-14 14:40:28','json',0,NULL,NULL,NULL),(4,2,NULL,5,'hokkaプロジェクト','',5,0,0,0,'プレゼンテーション','ハイブリッド',0,'{\"phases\": [{\"phase\": \"準備期\", \"weeks\": [{\"week\": \"第1週\", \"hours\": 1, \"theme\": \"大テーマの理解と問いの設定\", \"activities\": \"クラス全体で北陸製菓のお菓子についての基本情報を学び、各自が興味を持ったトピックについて問いを設定する。\", \"teacher_support\": \"北陸製菓のお菓子についての基本情報の提供、問い設定の方法についての指導。\", \"evaluation\": \"問い設定のクオリティと具体性を活動記録とルーブリック評価で評価する。\"}]}, {\"phase\": \"探究期\", \"weeks\": [{\"week\": \"第2週\", \"hours\": 2, \"theme\": \"情報収集と整理\", \"activities\": \"各自の問いについてインターネットや図書館で情報を収集し、その情報を整理する。また、グループ内で情報を共有し、互いの理解を深める。\", \"teacher_support\": \"情報収集の方法や信頼性の確認方法、情報の整理方法についての指導。必要に応じて個別のサポート。\", \"evaluation\": \"情報収集の広さと深さ、整理の方法を活動記録とルーブリック評価で評価する。\"}]}, {\"phase\": \"まとめ期\", \"weeks\": [{\"week\": \"第3週\", \"hours\": 2, \"theme\": \"分析と発信\", \"activities\": \"収集した情報を基に問いに答え、その結果をクラス全体で共有する。また、北陸製菓のお菓子を魅力的に発信する方法を考え、それを実行する。\", \"teacher_support\": \"分析の方法や結果の解釈、発信方法についての指導。必要に応じて個別のサポート。\", \"evaluation\": \"分析の深さと広さ、発信の方法と効果を活動記録とルーブリック評価で評価する。\"}]}], \"rubric_suggestion\": [{\"category\": \"問いの設定\", \"description\": \"自分の興味に基づいて探究の問いを設定し、その問いが探究の方向性を示していること。\", \"levels\": [{\"level\": \"S\", \"description\": \"設定した問いが深い洞察力を示し、探究の方向性を明確に示している。\"}, {\"level\": \"A\", \"description\": \"設定した問いが一定の洞察力を示し、探究の方向性を示している。\"}, {\"level\": \"B\", \"description\": \"設定した問いが一部分についての洞察力を示し、一部の探究の方向性を示している。\"}, {\"level\": \"C\", \"description\": \"設定した問いが浅い洞察力を示し、あいまいな探究の方向性を示している。\"}]}, {\"category\": \"情報収集\", \"description\": \"自分の問いに答えるための情報を適切な手段で収集し、その情報が問いに対する理解を深めるためのものであること。\", \"levels\": [{\"level\": \"S\", \"description\": \"多様な手段で豊かな情報を収集し、その情報が問いに対する深い理解を可能にしている。\"}, {\"level\": \"A\", \"description\": \"複数の手段で一定の情報を収集し、その情報が問いに対する理解を深めている。\"}, {\"level\": \"B\", \"description\": \"一部の手段で限定的な情報を収集し、その情報が問いに対する一部の理解を深めている。\"}, {\"level\": \"C\", \"description\": \"限定的な手段で浅い情報を収集し、その情報が問いに対する浅い理解を可能にしている。\"}]}, {\"category\": \"分析力\", \"description\": \"収集した情報を分析し、その結果を自分の問いに関連付ける能力。\", \"levels\": [{\"level\": \"S\", \"description\": \"収集した情報を深く分析し、その結果を自分の問いと密接に関連付けている。\"}, {\"level\": \"A\", \"description\": \"収集した情報を一定の深さで分析し、その結果を自分の問いと関連付けている。\"}, {\"level\": \"B\", \"description\": \"収集した情報を一部分について分析し、その結果を自分の問いと一部分に関連付けている。\"}, {\"level\": \"C\", \"description\": \"収集した情報を浅く分析し、その結果を自分の問いとあいまいに関連付けている。\"}]}, {\"category\": \"発信力\", \"description\": \"自分の探究の結果を他者に対して魅力的に発信する能力。\", \"levels\": [{\"level\": \"S\", \"description\": \"深い洞察力と豊かな表現力で、自分の探究の結果を他者に対して魅力的に発信している。\"}, {\"level\": \"A\", \"description\": \"一定の洞察力と表現力で、自分の探究の結果を他者に対して発信している。\"}, {\"level\": \"B\", \"description\": \"一部分の洞察力と表現力で、自分の探究の結果を他者に対して部分的に発信している。\"}, {\"level\": \"C\", \"description\": \"浅い洞察力と表現力で、自分の探究の結果を他者に対してあいまいに発信している。\"}]}]}','2025-04-14 14:40:45','2025-04-14 14:40:45','json',0,NULL,NULL,NULL),(6,7,6,18,'a','',35,0,0,1,'プレゼンテーション','ハイブリッド',0,'		aaa	aaaaa	aaaa\r\n		bbbb	bbbbb	bbbb','2025-06-16 22:57:50','2025-07-10 02:04:30','table',0,NULL,NULL,NULL),(7,8,1,18,'磁界と電流','',35,0,0,1,'プレゼンテーション','ハイブリッド',0,'','2025-06-18 03:32:28','2025-06-19 05:55:08','table',0,NULL,NULL,NULL);
/*!40000 ALTER TABLE `curriculums` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `curriculum_units`
--

DROP TABLE IF EXISTS `curriculum_units`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `curriculum_units` (
  `id` int NOT NULL AUTO_INCREMENT,
  `unit_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '単元コード',
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `subject_id` int DEFAULT NULL,
  `parent_id` int DEFAULT NULL,
  `order_index` int DEFAULT NULL,
  `estimated_minutes` int DEFAULT NULL,
  `difficulty_level` int DEFAULT NULL,
  `prerequisites` json DEFAULT NULL,
  `legacy_curriculum_id` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `created_by` int NOT NULL DEFAULT '1' COMMENT '作成者ID',
  `school_id` int DEFAULT NULL COMMENT '学校ID（NULL=全校共通）',
  `is_active` tinyint(1) NOT NULL DEFAULT '1' COMMENT '有効フラグ',
  `learning_objectives` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '学習目標',
  `tags` json DEFAULT NULL COMMENT 'タグ配列',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_unit_code` (`unit_code`),
  KEY `legacy_curriculum_id` (`legacy_curriculum_id`),
  KEY `parent_id` (`parent_id`),
  KEY `subject_id` (`subject_id`),
  KEY `idx_curriculum_units_school_id` (`school_id`),
  KEY `idx_curriculum_units_is_active` (`is_active`),
  KEY `idx_curriculum_units_created_by` (`created_by`),
  CONSTRAINT `curriculum_units_ibfk_1` FOREIGN KEY (`legacy_curriculum_id`) REFERENCES `curriculums` (`id`),
  CONSTRAINT `curriculum_units_ibfk_2` FOREIGN KEY (`parent_id`) REFERENCES `curriculum_units` (`id`),
  CONSTRAINT `curriculum_units_ibfk_3` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_curriculum_units_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_curriculum_units_school_id` FOREIGN KEY (`school_id`) REFERENCES `schools` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `curriculum_units`
--

LOCK TABLES `curriculum_units` WRITE;
/*!40000 ALTER TABLE `curriculum_units` DISABLE KEYS */;
INSERT INTO `curriculum_units` VALUES (1,'UNIT_001','北陸製菓のお菓子の魅力を発信しよう！','',6,NULL,NULL,NULL,NULL,NULL,1,'2025-06-19 10:45:14',NULL,5,1,1,'【北陸製菓のお菓子の魅力を発信しよう！】の基本的な概念を理解し、実践的に活用できるようになる','[\"基礎\", \"必修\"]'),(2,'UNIT_002','hokkaプロジェクト','',6,NULL,NULL,NULL,NULL,NULL,2,'2025-06-19 10:45:14',NULL,5,1,1,'地域の特産品を通じて、マーケティングと情報発信の基礎を学ぶ','[\"基礎\", \"必修\"]'),(3,'UNIT_003','hokkaプロジェクト','',6,NULL,NULL,NULL,NULL,NULL,3,'2025-06-19 10:45:14',NULL,5,1,1,'地域の特産品を通じて、マーケティングと情報発信の基礎を学ぶ','[\"基礎\", \"必修\"]'),(4,'UNIT_004','hokkaプロジェクト','',6,NULL,NULL,NULL,NULL,NULL,4,'2025-06-19 10:45:14',NULL,5,1,1,'地域の特産品を通じて、マーケティングと情報発信の基礎を学ぶ','[\"基礎\", \"必修\"]'),(5,'UNIT_005','a','',6,NULL,NULL,NULL,NULL,NULL,6,'2025-06-19 10:45:14',NULL,18,3,1,'【a】の基本的な概念を理解し、実践的に活用できるようになる','[\"探究\", \"選択\", \"プロジェクト\"]'),(6,'UNIT_006','磁界と電流','',1,NULL,NULL,NULL,NULL,NULL,7,'2025-06-19 10:45:14',NULL,18,3,1,'磁界と電流の関係を理解し、電磁誘導の原理を説明できるようになる','[\"理科\", \"必修\", \"実験\"]'),(8,'UNIT_007','物質の性質と変化','物質の三態変化や化学変化について学習します',1,NULL,NULL,45,2,NULL,NULL,'2025-06-19 10:50:39',NULL,4,NULL,1,'物質の性質と変化について、化学的な視点から理解し説明できるようになる','[\"理科\", \"必修\", \"実験\"]'),(9,'UNIT_008','生物の体のつくりと働き','動物や植物の体の構造と機能について学習します',1,NULL,NULL,60,2,NULL,NULL,'2025-06-19 10:50:39',NULL,4,NULL,1,'生物の体のつくりと働きを理解し、生命現象を科学的に説明できるようになる','[\"理科\", \"必修\", \"実験\"]');
/*!40000 ALTER TABLE `curriculum_units` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-07-10 17:48:49
