#!/usr/bin/env python3
"""
本番環境データベース バックアップスクリプト
"""
import subprocess
import sys
from datetime import datetime
import os

# 本番環境データベース接続情報
DB_CONFIG = {
    'host': 'localhost',
    'user': 'QuestEd',
    'password': 'QuestEd-03012025MySQL',
    'database': 'quested',
}

def create_backup():
    """データベースの完全バックアップを作成"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = '/home/masat/claude-projects/QuestEd/backups'
    
    # バックアップディレクトリ作成
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_file = f"{backup_dir}/quested_production_backup_{timestamp}.sql"
    
    # mysqldumpコマンド実行
    cmd = [
        'mysqldump',
        f"--host={DB_CONFIG['host']}",
        f"--user={DB_CONFIG['user']}",
        f"--password={DB_CONFIG['password']}",
        '--single-transaction',
        '--routines',
        '--triggers',
        '--add-drop-table',
        '--comments',
        '--create-options',
        '--complete-insert',
        DB_CONFIG['database']
    ]
    
    try:
        print(f"🔄 バックアップ開始: {backup_file}")
        
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            file_size = os.path.getsize(backup_file) / (1024 * 1024)  # MB
            print(f"✅ バックアップ完了: {backup_file}")
            print(f"📊 ファイルサイズ: {file_size:.2f} MB")
            
            # 圧縮バックアップも作成
            compressed_file = f"{backup_file}.gz"
            subprocess.run(['gzip', '-k', backup_file])
            
            if os.path.exists(compressed_file):
                compressed_size = os.path.getsize(compressed_file) / (1024 * 1024)
                print(f"📦 圧縮バックアップ: {compressed_file}")
                print(f"📊 圧縮サイズ: {compressed_size:.2f} MB")
            
            return backup_file
        else:
            print(f"❌ バックアップエラー: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ バックアップ実行エラー: {e}")
        return None

def verify_backup(backup_file):
    """バックアップファイルの整合性確認"""
    try:
        print(f"🔍 バックアップファイル検証中...")
        
        # ファイルサイズ確認
        if not os.path.exists(backup_file):
            print(f"❌ バックアップファイルが存在しません: {backup_file}")
            return False
        
        file_size = os.path.getsize(backup_file)
        if file_size < 1024:  # 1KB未満の場合は不正
            print(f"❌ バックアップファイルサイズが異常に小さい: {file_size} bytes")
            return False
        
        # SQL構文の基本確認
        with open(backup_file, 'r') as f:
            content = f.read(2000)  # 最初の2000文字
            if 'MySQL dump' not in content or 'Table structure' not in content:
                print(f"❌ バックアップファイルにSQLコンテンツが含まれていません")
                return False
        
        print(f"✅ バックアップファイル検証完了")
        return True
        
    except Exception as e:
        print(f"❌ バックアップ検証エラー: {e}")
        return False

def main():
    """メイン実行"""
    print(f"🛡️ QuestEd 本番環境データベース バックアップ")
    print(f"📅 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # バックアップ実行
    backup_file = create_backup()
    
    if backup_file:
        # バックアップ検証
        if verify_backup(backup_file):
            print("\n" + "=" * 60)
            print("✅ データベースバックアップ完了")
            print(f"📁 バックアップファイル: {backup_file}")
            print(f"📁 圧縮ファイル: {backup_file}.gz")
            print("\n💡 次のステップ:")
            print("   1. マイグレーション実行")
            print("   2. 動作確認")
            print("   3. 必要に応じてロールバック")
            return True
        else:
            print("\n❌ バックアップ検証に失敗しました")
            return False
    else:
        print("\n❌ バックアップ作成に失敗しました")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)