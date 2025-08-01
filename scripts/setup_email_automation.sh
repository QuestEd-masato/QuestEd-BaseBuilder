#!/bin/bash
# QuestEd メール機能とレポート自動化のセットアップスクリプト

echo "=== QuestEd メール機能セットアップ ==="

# プロジェクトディレクトリの取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "プロジェクトディレクトリ: $PROJECT_DIR"

# .envファイルのチェック
ENV_FILE="$PROJECT_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "❌ .envファイルが見つかりません: $ENV_FILE"
    exit 1
fi

# SMTP設定の確認
echo ""
echo "=== SMTP設定確認 ==="
source "$ENV_FILE"

if [[ "$SMTP_USER" == "your_email@gmail.com" ]] || [[ -z "$SMTP_USER" ]]; then
    echo "❌ SMTP_USERが設定されていません"
    echo "   .envファイルでSMTP_USERにGmailアドレスを設定してください"
    SMTP_CONFIGURED=false
else
    echo "✅ SMTP_USER: $SMTP_USER"
    SMTP_CONFIGURED=true
fi

if [[ "$SMTP_PASSWORD" == "your_16_char_app_password" ]] || [[ -z "$SMTP_PASSWORD" ]]; then
    echo "❌ SMTP_PASSWORDが設定されていません"
    echo "   .envファイルでSMTP_PASSWORDにGmailアプリパスワードを設定してください"
    SMTP_CONFIGURED=false
else
    echo "✅ SMTP_PASSWORD: 設定済み"
fi

# メールログ機能の設定
echo ""
echo "=== メールログ機能 ==="
read -p "メール送信ログをデータベースに記録しますか？ (y/n): " enable_log
if [[ "$enable_log" =~ ^[Yy]$ ]]; then
    # .envファイルでEMAIL_LOG_ENABLEDをtrueに設定
    if grep -q "EMAIL_LOG_ENABLED=" "$ENV_FILE"; then
        sed -i 's/EMAIL_LOG_ENABLED=.*/EMAIL_LOG_ENABLED=true/' "$ENV_FILE"
    else
        echo "EMAIL_LOG_ENABLED=true" >> "$ENV_FILE"
    fi
    echo "✅ メールログ機能を有効化しました"
else
    echo "ℹ️ メールログ機能は無効のままです"
fi

# 日次レポートの設定
echo ""
echo "=== 日次レポート自動化 ==="
if [[ "$SMTP_CONFIGURED" == true ]]; then
    read -p "日次レポートの自動送信を設定しますか？ (y/n): " setup_cron
    if [[ "$setup_cron" =~ ^[Yy]$ ]]; then
        # 送信時間の設定
        echo "日次レポートの送信時間を設定してください："
        read -p "時間（0-23）: " hour
        read -p "分（0-59）: " minute
        
        # 数値チェック
        if ! [[ "$hour" =~ ^[0-9]+$ ]] || ! [[ "$minute" =~ ^[0-9]+$ ]] || 
           [ "$hour" -lt 0 ] || [ "$hour" -gt 23 ] || 
           [ "$minute" -lt 0 ] || [ "$minute" -gt 59 ]; then
            echo "❌ 無効な時間が入力されました。デフォルト（20:00）を使用します。"
            hour=20
            minute=0
        fi
        
        # Cronジョブの設定
        CRON_JOB="$minute $hour * * * cd $PROJECT_DIR && $PROJECT_DIR/venv/bin/python $PROJECT_DIR/scripts/run_daily_reports.py >> /tmp/quested_daily_reports.log 2>&1"
        
        # 既存のcronジョブを確認
        crontab -l > /tmp/current_cron 2>/dev/null || true
        
        if grep -q "run_daily_reports.py" /tmp/current_cron; then
            echo "⚠️ 日次レポートのcronジョブが既に存在します"
            read -p "更新しますか？ (y/n): " update_cron
            if [[ "$update_cron" =~ ^[Yy]$ ]]; then
                # 既存のジョブを削除してから追加
                grep -v "run_daily_reports.py" /tmp/current_cron > /tmp/new_cron
                echo "$CRON_JOB" >> /tmp/new_cron
                crontab /tmp/new_cron
                echo "✅ 日次レポートのcronジョブを更新しました（毎日 $hour:$(printf %02d $minute)）"
            fi
        else
            echo "$CRON_JOB" >> /tmp/current_cron
            crontab /tmp/current_cron
            echo "✅ 日次レポートのcronジョブを追加しました（毎日 $hour:$(printf %02d $minute)）"
        fi
        
        echo "   ログファイル: /tmp/quested_daily_reports.log"
    else
        echo "ℹ️ 日次レポートの自動化はスキップされました"
    fi
else
    echo "⚠️ SMTP設定が未完了のため、日次レポートの設定をスキップします"
fi

# テスト実行の提案
echo ""
echo "=== 次のステップ ==="
if [[ "$SMTP_CONFIGURED" == true ]]; then
    echo "1. メール設定のテスト:"
    echo "   python test_email_config.py --send"
    echo ""
    echo "2. 日次レポートのテスト実行:"
    echo "   python scripts/run_daily_reports.py"
    echo ""
    echo "3. cronジョブの確認:"
    echo "   crontab -l"
else
    echo "1. .envファイルでSMTP設定を完了してください"
    echo "2. 設定完了後、このスクリプトを再実行してください"
fi

echo ""
echo "=== セットアップ完了 ==="