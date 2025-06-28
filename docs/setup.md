# Development Setup Guide

Generated on 2025-06-28 07:02:29

## 📋 Prerequisites

### Required Software
- Python 3.8+
- MySQL 8.0+
- Redis (for caching)
- Node.js (for frontend tools)

### Development Tools
- Git
- Virtual environment manager
- Code editor (VS Code recommended)

## 🚀 Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd quested
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create `.env` file:
```env
SECRET_KEY=your-secret-key
DB_USERNAME=username
DB_PASSWORD=password
DB_HOST=localhost
DB_NAME=quested
OPENAI_API_KEY=your-openai-key
```

### 5. Database Setup
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 6. Run Application
```bash
python app.py
```

## 🔧 Development Workflow

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Write comprehensive docstrings

### Testing
```bash
pytest tests/
```

### Database Migrations
```bash
flask db migrate -m "Description"
flask db upgrade
```

## 📦 Project Structure

```
quested/
├── app/                 # Main application
├── basebuilder/         # Learning module
├── static/              # Static assets
├── templates/           # HTML templates
├── tests/               # Test suite
├── docs/                # Documentation
├── requirements.txt     # Dependencies
└── app.py              # Entry point
```

## 🚨 Troubleshooting

### Common Issues
- Database connection errors
- Import path problems
- Missing environment variables

### Debug Mode
Set `FLASK_DEBUG=1` for development debugging.
