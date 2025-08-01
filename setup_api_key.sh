#!/bin/bash
# OPENAI_API_KEY インタラクティブ設定スクリプト
# QuestEd Ver.2.0用

echo "🤖 QuestEd Ver.2.0 - OPENAI_API_KEY 設定スクリプト"
echo "=================================================="
echo ""

# 現在の設定確認
echo "📋 現在の設定状況:"
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ 環境変数: 未設定"
else
    echo "✅ 環境変数: 設定済み"
fi

# .envファイル確認
if grep -q "^OPENAI_API_KEY=" .env 2>/dev/null; then
    echo "✅ .envファイル: 設定済み"
else
    echo "❌ .envファイル: 未設定"
fi

echo ""
echo "🔧 設定オプション:"
echo "1. .envファイルで設定（推奨・永続的）"
echo "2. 環境変数で設定（一時的）"
echo "3. 設定状況の確認のみ"
echo "4. 終了"
echo ""

read -p "選択してください [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "📝 .envファイル設定モード"
        echo "OpenAI Platform (https://platform.openai.com/api-keys) でAPIキーを取得してください"
        echo ""
        read -p "OpenAI API Key (sk-で始まる文字列): " api_key
        
        if [[ $api_key == sk-* ]]; then
            # バックアップ作成
            cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
            echo "✅ .envファイルのバックアップを作成しました"
            
            # APIキー設定
            if grep -q "# OPENAI_API_KEY=sk-" .env; then
                # 既存のコメント行を置換
                sed -i "s/# OPENAI_API_KEY=sk-.*/OPENAI_API_KEY=$api_key/" .env
                echo "✅ .envファイルにAPIキーを設定しました"
            else
                # 新規追加
                echo "" >> .env
                echo "# OpenAI API Configuration" >> .env
                echo "OPENAI_API_KEY=$api_key" >> .env
                echo "✅ .envファイルに新規でAPIキーを追加しました"
            fi
            
            echo ""
            echo "🎉 設定完了！"
            echo "次のステップ:"
            echo "1. source venv/bin/activate"
            echo "2. python run.py"
            echo "3. http://localhost:5000 でAI機能をお試しください"
            
        else
            echo "❌ 無効なAPIキー形式です（sk-で始まる必要があります）"
            exit 1
        fi
        ;;
        
    2)
        echo ""
        echo "🔄 環境変数設定モード（現在のセッションのみ有効）"
        read -p "OpenAI API Key (sk-で始まる文字列): " api_key
        
        if [[ $api_key == sk-* ]]; then
            export OPENAI_API_KEY="$api_key"
            echo "✅ 環境変数にAPIキーを設定しました"
            echo ""
            echo "⚠️  注意: この設定は現在のターミナルセッションでのみ有効です"
            echo "永続的な設定は .envファイル設定を使用してください"
            echo ""
            echo "QuestEd Ver.2.0を起動:"
            echo "python run.py"
        else
            echo "❌ 無効なAPIキー形式です（sk-で始まる必要があります）"
            exit 1
        fi
        ;;
        
    3)
        echo ""
        echo "📊 設定確認中..."
        python check_api_key.py
        ;;
        
    4)
        echo "👋 設定を終了します"
        exit 0
        ;;
        
    *)
        echo "❌ 無効な選択です"
        exit 1
        ;;
esac