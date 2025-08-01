#!/bin/bash
"""
QuestEd MySQL Development Environment Setup
==========================================
Docker Composeを使用したローカル開発環境の構築

前提条件: docker, docker-composeがインストール済み
"""

echo "🔍 QuestEd MySQL Development Environment Setup"
echo "=============================================="

# 現在のディレクトリ確認
CURRENT_DIR=$(pwd)
echo "📁 Current directory: $CURRENT_DIR"

# Docker Composeファイルが存在するか確認
if [ -f "docker-compose.yml" ]; then
    echo "✅ Found existing docker-compose.yml"
else
    echo "❌ docker-compose.yml not found"
    echo "   Creating minimal MySQL setup..."
    
    # 最小限のMySQL構成を作成
    cat > docker-compose.dev.yml << 'EOF'
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: quested_mysql_dev
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: quested_root_2025
      MYSQL_DATABASE: quested_dev
      MYSQL_USER: quested_user
      MYSQL_PASSWORD: quested_pass_2025
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./deployment/mysql-init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

volumes:
  mysql_data:
EOF

    echo "✅ Created docker-compose.dev.yml"
fi

# 環境変数ファイルの確認
if [ -f ".env" ]; then
    echo "✅ Found existing .env file"
else
    echo "📝 Creating development .env file..."
    
    cat > .env.dev << 'EOF'
# QuestEd Development Environment Configuration
# ===========================================

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=true
SECRET_KEY=dev_secret_key_change_in_production

# Database Configuration  
DB_HOST=localhost
DB_PORT=3306
DB_USERNAME=quested_user
DB_PASSWORD=quested_pass_2025
DB_NAME=quested_dev

# Database URL (for SQLAlchemy)
DATABASE_URL=mysql+pymysql://quested_user:quested_pass_2025@localhost:3306/quested_dev

# Optional: OpenAI API (for AI features)
# OPENAI_API_KEY=your_openai_api_key_here

# Email Configuration (optional for development)
# MAIL_SERVER=smtp.gmail.com
# MAIL_PORT=587
# MAIL_USE_TLS=true
# MAIL_USERNAME=your_email@gmail.com
# MAIL_PASSWORD=your_app_password

# Redis Configuration (optional)
# REDIS_URL=redis://localhost:6379

# Celery Configuration (optional)
# CELERY_BROKER_URL=redis://localhost:6379
# CELERY_RESULT_BACKEND=redis://localhost:6379
EOF

    echo "✅ Created .env.dev file"
    echo "   📝 Copy to .env and modify as needed"
fi

echo ""
echo "🚀 Next Steps:"
echo "=============="
echo "1. Install Docker and Docker Compose if not already installed"
echo "2. Copy .env.dev to .env: cp .env.dev .env"
echo "3. Start MySQL: docker-compose -f docker-compose.dev.yml up -d"
echo "4. Wait for MySQL to initialize (1-2 minutes)"
echo "5. Test connection: docker exec quested_mysql_dev mysql -u quested_user -p quested_dev"
echo "6. Install Python dependencies: pip install -r requirements.txt"
echo "7. Run migrations: flask db upgrade"
echo "8. Test BaseBuilder: python scripts/check_basebuilder_tables.py"
echo ""
echo "🔧 MySQL Access:"
echo "   Host: localhost"
echo "   Port: 3306"
echo "   User: quested_user"
echo "   Password: quested_pass_2025"
echo "   Database: quested_dev"