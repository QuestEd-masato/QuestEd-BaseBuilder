#!/usr/bin/env python3
"""
QuestEd モデル動作確認スクリプト

RDSとの互換性とモデルクラスの基本動作を確認
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from app.models import *
from basebuilder.models import *

def test_basic_model_operations():
    """基本的なモデル操作のテスト"""
    app = create_app()
    
    with app.app_context():
        print("=== QuestEd モデル動作確認 ===")
        print()
        
        # 1. BasicKnowledgeItemの確認
        print("1. BasicKnowledgeItem 確認")
        try:
            items = BasicKnowledgeItem.query.limit(5).all()
            print(f"   - 件数: {BasicKnowledgeItem.query.count()}件")
            if items:
                item = items[0]
                print(f"   - 最初のアイテム: {item.title}")
                print(f"   - difficulty値: {item.difficulty}")  # difficulty_levelではない
                print(f"   - subject_id: {getattr(item, 'subject_id', 'フィールドなし')}")
        except Exception as e:
            print(f"   ❌ エラー: {e}")
        print()
        
        # 2. 新機能テーブルの確認
        print("2. 新機能テーブル 確認")
        
        # CurriculumUnit
        try:
            units = CurriculumUnit.query.all()
            print(f"   - CurriculumUnit件数: {len(units)}")
        except Exception as e:
            print(f"   ❌ CurriculumUnit エラー: {e}")
        
        # SpeechTranscription
        try:
            transcriptions = SpeechTranscription.query.all()
            print(f"   - SpeechTranscription件数: {len(transcriptions)}")
        except Exception as e:
            print(f"   ❌ SpeechTranscription エラー: {e}")
        
        # AIRecommendation
        try:
            recommendations = AIRecommendation.query.all()
            print(f"   - AIRecommendation件数: {len(recommendations)}")
        except Exception as e:
            print(f"   ❌ AIRecommendation エラー: {e}")
        
        print()
        
        # 3. 既存テーブルの確認
        print("3. 既存テーブル 確認")
        
        # ActivityLog
        try:
            logs = ActivityLog.query.all()
            print(f"   - ActivityLog件数: {len(logs)}")
            if logs:
                log = logs[0]
                print(f"   - 最初のログ: {log.title}")
        except Exception as e:
            print(f"   ❌ ActivityLog エラー: {e}")
        
        # AnswerRecord
        try:
            records = AnswerRecord.query.all()
            print(f"   - AnswerRecord件数: {len(records)}")
            if records:
                record = records[0]
                print(f"   - 最初のレコード: 生徒ID {record.student_id}, 正解: {record.is_correct}")
        except Exception as e:
            print(f"   ❌ AnswerRecord エラー: {e}")
        
        # Milestone
        try:
            milestones = Milestone.query.all()
            print(f"   - Milestone件数: {len(milestones)}")
            if milestones:
                milestone = milestones[0]
                print(f"   - 最初のマイルストーン: {milestone.title}")
        except Exception as e:
            print(f"   ❌ Milestone エラー: {e}")
        
        print()
        
        # 4. User・Class・Subject の確認
        print("4. 基本テーブル 確認")
        
        try:
            users = User.query.all()
            print(f"   - User件数: {len(users)}")
            if users:
                user = users[0]
                print(f"   - 最初のユーザー: {user.username}")
                print(f"   - is_active: {getattr(user, 'is_active', 'フィールドなし')}")
                print(f"   - class_id: {getattr(user, 'class_id', 'フィールドなし')}")
        except Exception as e:
            print(f"   ❌ User エラー: {e}")
        
        try:
            classes = Class.query.all()
            print(f"   - Class件数: {len(classes)}")
        except Exception as e:
            print(f"   ❌ Class エラー: {e}")
        
        try:
            subjects = Subject.query.all()
            print(f"   - Subject件数: {len(subjects)}")
        except Exception as e:
            print(f"   ❌ Subject エラー: {e}")
        
        print()
        
        # 5. 外部キー関係の確認
        print("5. リレーションシップ 確認")
        
        try:
            # BasicKnowledgeItemとAnswerRecordの関係
            if BasicKnowledgeItem.query.first() and AnswerRecord.query.first():
                problem = BasicKnowledgeItem.query.first()
                answer_records = AnswerRecord.query.filter_by(problem_id=problem.id).all()
                print(f"   - 問題「{problem.title}」の回答履歴: {len(answer_records)}件")
        except Exception as e:
            print(f"   ❌ リレーションシップ エラー: {e}")
        
        print()
        print("=== 動作確認完了 ===")

def test_model_creation():
    """新しいレコード作成のテスト"""
    app = create_app()
    
    with app.app_context():
        print("=== レコード作成テスト ===")
        
        try:
            # SpeechTranscriptionの作成テスト
            if User.query.first():
                user = User.query.first()
                
                transcription = SpeechTranscription(
                    user_id=user.id,
                    transcription="テスト音声認識",
                    usage_context="test",
                    duration=5.5,
                    confidence_score=0.95
                )
                
                # コミットはしない（テストのため）
                print("   ✅ SpeechTranscription作成テスト成功")
                print(f"   - user_id: {transcription.user_id}")
                print(f"   - transcription: {transcription.transcription}")
                print(f"   - confidence_score: {transcription.confidence_score}")
                
        except Exception as e:
            print(f"   ❌ SpeechTranscription作成エラー: {e}")
        
        try:
            # AIRecommendationの作成テスト
            if User.query.first():
                user = User.query.first()
                
                recommendation = AIRecommendation(
                    student_id=user.id,
                    recommendation_type="unit",
                    ai_model="gpt-4",
                    confidence_score=0.85,
                    reasoning="テスト推薦"
                )
                
                print("   ✅ AIRecommendation作成テスト成功")
                print(f"   - student_id: {recommendation.student_id}")
                print(f"   - recommendation_type: {recommendation.recommendation_type}")
                
        except Exception as e:
            print(f"   ❌ AIRecommendation作成エラー: {e}")
        
        print("=== レコード作成テスト完了 ===")

if __name__ == "__main__":
    print("QuestEd モデル動作確認を開始します...\n")
    
    # 基本動作確認
    test_basic_model_operations()
    
    print()
    
    # レコード作成テスト
    test_model_creation()
    
    print("\n全テスト完了！")