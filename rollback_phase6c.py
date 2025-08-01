#!/usr/bin/env python3
"""
Phase6-C ロールバックスクリプト
Unit Management refactoring後に問題が発生した場合の復旧用
"""

import sys
import os
import shutil
import glob
from datetime import datetime

def create_emergency_backup():
    """緊急バックアップ作成"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    emergency_backup_dir = f"/home/masat/claude-projects/QuestEd/backups/emergency_phase6c_{timestamp}"
    
    os.makedirs(emergency_backup_dir, exist_ok=True)
    
    # 現在のunit_management.pyをバックアップ
    if os.path.exists("/home/masat/claude-projects/QuestEd/app/api/unit_management.py"):
        shutil.copy2(
            "/home/masat/claude-projects/QuestEd/app/api/unit_management.py",
            f"{emergency_backup_dir}/unit_management_emergency.py"
        )
    
    # 新しいサービスファイルがあればバックアップ
    service_files = [
        "/home/masat/claude-projects/QuestEd/app/services/unit_selection_service.py",
        "/home/masat/claude-projects/QuestEd/app/services/unit_data_provider.py",
        "/home/masat/claude-projects/QuestEd/app/services/progress_calculator.py",
        "/home/masat/claude-projects/QuestEd/app/services/unit_statistics_service.py"
    ]
    
    for file_path in service_files:
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            shutil.copy2(file_path, f"{emergency_backup_dir}/{filename}")
    
    print(f"✅ Emergency backup created: {emergency_backup_dir}")
    return emergency_backup_dir

def find_latest_backup():
    """最新のPhase6-Cバックアップファイルを検索"""
    backup_pattern = "/home/masat/claude-projects/QuestEd/backups/phase6c_unit_management_backup_*.py"
    backup_files = glob.glob(backup_pattern)
    
    if not backup_files:
        print("❌ No Phase6-C backup files found")
        return None
    
    # 最新のファイルを取得
    latest_backup = max(backup_files, key=os.path.getctime)
    print(f"✅ Latest backup found: {latest_backup}")
    return latest_backup

def rollback_unit_management():
    """Unit Management関連ファイルをロールバック"""
    print("=== Unit Management Rollback ===")
    
    # 緊急バックアップ作成
    emergency_backup_dir = create_emergency_backup()
    
    # 最新バックアップを検索
    latest_backup = find_latest_backup()
    if not latest_backup:
        return False
    
    try:
        # unit_management.pyを復元
        target_path = "/home/masat/claude-projects/QuestEd/app/api/unit_management.py"
        shutil.copy2(latest_backup, target_path)
        print(f"✅ unit_management.py restored from: {latest_backup}")
        
        # 作成されたサービスファイルを削除
        service_files_to_remove = [
            "/home/masat/claude-projects/QuestEd/app/services/unit_selection_service.py",
            "/home/masat/claude-projects/QuestEd/app/services/unit_data_provider.py", 
            "/home/masat/claude-projects/QuestEd/app/services/progress_calculator.py",
            "/home/masat/claude-projects/QuestEd/app/services/unit_statistics_service.py"
        ]
        
        for file_path in service_files_to_remove:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"✅ Removed new service file: {file_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        return False

def verify_rollback():
    """ロールバック後の動作確認"""
    print("\n=== Rollback Verification ===")
    
    try:
        # 構文チェック
        import py_compile
        py_compile.compile('/home/masat/claude-projects/QuestEd/app/api/unit_management.py', doraise=True)
        print("✅ unit_management.py syntax check passed")
        
        # ファイルサイズ確認（1,763行程度であることを確認）
        with open('/home/masat/claude-projects/QuestEd/app/api/unit_management.py', 'r') as f:
            lines = len(f.readlines())
        
        if 1700 <= lines <= 1800:
            print(f"✅ unit_management.py line count normal: {lines} lines")
        else:
            print(f"⚠️  unit_management.py line count unexpected: {lines} lines")
        
        return True
        
    except Exception as e:
        print(f"❌ Rollback verification failed: {e}")
        return False

def main():
    """メインロールバック実行"""
    print("Phase6-C Emergency Rollback")
    print("=" * 50)
    
    print("⚠️  WARNING: This will restore unit_management.py to pre-Phase6-C state")
    print("⚠️  WARNING: Any Phase6-C changes will be lost")
    
    confirmation = input("Continue rollback? (yes/no): ").lower().strip()
    if confirmation != 'yes':
        print("❌ Rollback cancelled")
        return False
    
    # ロールバック実行
    if not rollback_unit_management():
        print("❌ Rollback failed")
        return False
    
    # 検証
    if not verify_rollback():
        print("❌ Rollback verification failed")
        return False
    
    print("\n" + "=" * 50)
    print("✅ Phase6-C Rollback COMPLETED")
    print("✅ unit_management.py restored to pre-Phase6-C state")
    print("✅ System should be functional")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)