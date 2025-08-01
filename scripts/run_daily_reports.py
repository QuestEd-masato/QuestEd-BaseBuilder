#!/usr/bin/env python3
"""
日次レポート実行スクリプト（ログ記録対応）
既存のDailyReportServiceを使用して日次レポートを生成・送信

Usage:
    python scripts/run_daily_reports.py
    
Environment Variables:
    EMAIL_LOG_ENABLED=true  # メール送信ログを有効化
    SMTP_USER=...           # SMTP設定
    SMTP_PASSWORD=...       # SMTP設定
"""
import os
import sys
import logging
from datetime import datetime

# プロジェクトルートをPythonパスに追加
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/quested_daily_reports.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    logger.info("=== QuestEd 日次レポート開始 ===")
    logger.info(f"実行時刻: {datetime.now()}")
    
    try:
        # 環境変数の確認
        email_log_enabled = os.getenv("EMAIL_LOG_ENABLED", "false").lower() == "true"
        smtp_user = os.getenv("SMTP_USER")
        
        logger.info(f"メールログ記録: {'有効' if email_log_enabled else '無効'}")
        logger.info(f"SMTP設定: {'設定済み' if smtp_user and smtp_user != 'your_email@gmail.com' else '未設定'}")
        
        if not smtp_user or smtp_user == 'your_email@gmail.com':
            logger.warning("SMTP設定が未完了です。.envファイルでSMTP_USERとSMTP_PASSWORDを設定してください。")
            return False
        
        # Flaskアプリケーションの初期化
        from app import create_app
        from app.tasks.daily_report import DailyReportService
        
        app = create_app()
        
        with app.app_context():
            # DailyReportServiceを使用してレポート生成
            service = DailyReportService(app)
            success, message = service.generate_all_reports()
            
            if success:
                logger.info(f"✅ 日次レポート送信完了: {message}")
                return True
            else:
                logger.error(f"❌ 日次レポート送信失敗: {message}")
                return False
                
    except Exception as e:
        logger.error(f"❌ 日次レポート実行中にエラーが発生: {str(e)}", exc_info=True)
        return False
    
    finally:
        logger.info("=== QuestEd 日次レポート終了 ===")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)