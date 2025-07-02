# QuestEd Development Guide

*📅 Last Updated: 2025-07-02 | Status: Safe Development Practices*

This document provides comprehensive guidelines for safe development practices, constraints, and recommended procedures for QuestEd.

---

## ⚠️ Critical Development Constraints

### 🚫 Prohibited Changes

#### Database Schema Modifications
```sql
-- ❌ NEVER DO THESE WITHOUT EXPLICIT APPROVAL:
DROP TABLE any_table;
ALTER TABLE users DROP COLUMN username;
ALTER TABLE basic_knowledge_items CHANGE difficulty difficulty_level;
DELETE FROM users WHERE role = 'admin';
```
**Reason**: Impact on 55 tables and complex relationships unknown

#### Blueprint Name Changes
```python
# ❌ NEVER CHANGE BLUEPRINT NAMES:
Blueprint('auth', __name__)  → Blueprint('authentication', __name__)
Blueprint('student', __name__) → Blueprint('student_module', __name__)
```
**Reason**: Breaks 199+ template references across 59 files

#### Model Relationship Modifications
```python
# ❌ NEVER MODIFY RELATIONSHIPS WITHOUT PLANNING:
class User(db.Model):
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'))
    # Don't change to different table or remove relationship
```
**Reason**: Complex dependencies across educational hierarchy

#### Large-Scale Code Movement
```python
# ❌ AVOID MASSIVE FILE REORGANIZATION:
# Moving entire modules between directories
# Changing import structures across multiple files
```
**Reason**: Import complexity and circular dependency risks

---

## ✅ Safe Change Areas

### Individual Route Function Improvements
```python
# ✅ SAFE: Enhance individual route functions
@categories_bp.route('/categories')
@login_required
def categories():
    # Add error handling, improve logic
    try:
        categories = ProblemCategory.query.all()
        return render_template('basebuilder/categories.html', categories=categories)
    except Exception as e:
        current_app.logger.error(f"Categories error: {e}")
        flash('Error loading categories', 'error')
        return redirect(url_for('basebuilder.index'))
```

### Error Handling Enhancements
```python
# ✅ SAFE: Add comprehensive error handling
from basebuilder.utils import handle_db_error

@handle_db_error("Category creation")
def create_category():
    # Existing logic with enhanced error handling
```

### Template UI Improvements
```html
<!-- ✅ SAFE: Improve templates -->
<!-- Add better styling, responsive design, user experience -->
<div class="card">
    <div class="card-header">
        <h3>{{ title }}</h3>
    </div>
    <div class="card-body">
        <!-- Enhanced UI elements -->
    </div>
</div>
```

### Utility Function Additions
```python
# ✅ SAFE: Add new utility functions
def format_study_time(minutes):
    """Convert minutes to human-readable format"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
```

---

## 📋 Safe Development Procedures

### 1. Pre-Development Analysis
```bash
# Before making changes, analyze impact:
grep -r "function_name" --include="*.py" .
grep -r "template_name" --include="*.html" templates/
grep -r "endpoint_name" --include="*.js" static/js/
```

### 2. Database Safety Checks
```python
# Always use try-catch for database operations
try:
    db.session.add(new_object)
    db.session.commit()
    flash('Success message', 'success')
except Exception as e:
    db.session.rollback()
    current_app.logger.error(f"Database error: {e}")
    flash(f'Error: {str(e)}', 'error')
```

### 3. Template Safety Patterns
```python
# Always provide template variables with defaults
@app.route('/example')
def example():
    try:
        data = get_complex_data()
        return render_template('example.html', 
                             data=data,
                             title='Example Page',
                             user=current_user,
                             # Provide defaults for safety
                             stats={'total': 0, 'completed': 0})
    except Exception as e:
        # Fallback template with minimal data
        return render_template('example.html', 
                             data=[],
                             title='Example Page (Error)',
                             error_message=str(e))
```

### 4. Import Safety Guidelines
```python
# ✅ SAFE: Specific imports
from app.models import User, Class, BasicKnowledgeItem

# ✅ SAFE: Module-level imports
from app.services import UserService
from app.utils import format_date

# ⚠️ CAREFUL: Avoid circular imports
# Check import chain: A imports B imports C imports A
```

---

## 🔧 Recommended Development Patterns

### Service Layer Pattern
```python
# Create service classes for business logic
class CategoryService:
    @staticmethod
    def get_all_with_stats(school_id=None):
        """Get categories with problem/text counts"""
        try:
            query = ProblemCategory.query
            if school_id:
                query = query.filter_by(school_id=school_id)
            
            categories = query.all()
            return CategoryService._add_statistics(categories)
        except Exception as e:
            current_app.logger.error(f"CategoryService error: {e}")
            raise

    @staticmethod
    def _add_statistics(categories):
        """Add problem and text counts to categories"""
        # Implementation here
        pass
```

### Decorator Pattern for Common Operations
```python
# Create decorators for common functionality
from functools import wraps

def require_roles(*roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('Access denied', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage
@require_roles('admin', 'teacher')
def admin_function():
    pass
```

### Configuration Management
```python
# Use environment variables for configuration
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'mysql://user:pass@localhost/db'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Feature flags for safe development
    ENABLE_NEW_FEATURE = os.environ.get('ENABLE_NEW_FEATURE', 'False').lower() == 'true'
```

---

## 🛡️ Security Best Practices

### Authentication & Authorization
```python
# Always check authentication and authorization
@app.route('/sensitive_data')
@login_required
def sensitive_data():
    # Verify user has access to requested data
    if not can_access_data(current_user, requested_data_id):
        abort(403)
    
    # School-based data isolation
    if current_user.role != 'admin':
        data = Data.query.filter_by(school_id=current_user.school_id)
    else:
        data = Data.query.all()
```

### Input Validation
```python
# Validate all user inputs
from wtforms import Form, StringField, validators

class CategoryForm(Form):
    name = StringField('Name', [
        validators.Length(min=1, max=100),
        validators.DataRequired()
    ])
    description = StringField('Description', [
        validators.Length(max=500)
    ])

@app.route('/create_category', methods=['POST'])
def create_category():
    form = CategoryForm(request.form)
    if not form.validate():
        flash('Invalid input', 'error')
        return redirect(request.referrer)
    
    # Process validated data
```

### SQL Injection Prevention
```python
# ✅ SAFE: Use SQLAlchemy ORM
users = User.query.filter_by(school_id=school_id).all()

# ✅ SAFE: Parameterized queries if raw SQL needed
result = db.session.execute(
    text("SELECT * FROM users WHERE school_id = :school_id"),
    {"school_id": school_id}
)

# ❌ NEVER: String concatenation
# query = f"SELECT * FROM users WHERE school_id = {school_id}"
```

### File Upload Security
```python
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file provided', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to prevent conflicts
        filename = f"{int(time.time())}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
```

---

## 📊 Testing Guidelines

### Unit Testing Pattern
```python
import unittest
from app import create_app, db
from app.models import User, Category

class CategoryTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_category_creation(self):
        # Test category creation logic
        category = Category(name='Test Category')
        db.session.add(category)
        db.session.commit()
        
        self.assertEqual(category.name, 'Test Category')
        self.assertIsNotNone(category.id)
```

### Integration Testing
```python
def test_category_api_endpoint(self):
    # Test full API endpoint functionality
    with self.app.test_client() as client:
        # Login first
        response = client.post('/api/login', json={
            'username': 'test_user',
            'password': 'test_password'
        })
        token = response.json['data']['token']
        
        # Test category endpoint
        response = client.get('/api/basebuilder/categories',
                            headers={'Authorization': f'Bearer {token}'})
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['success'])
```

### Manual Testing Checklist
```bash
# 1. Authentication flow
# - Login with different roles
# - Test unauthorized access
# - Verify session management

# 2. Core functionality
# - Create, read, update operations
# - Test with different data sets
# - Verify error handling

# 3. Cross-browser testing
# - Chrome, Firefox, Safari
# - Mobile responsiveness
# - JavaScript functionality

# 4. Performance testing
# - Load testing with multiple users
# - Database query performance
# - File upload performance
```

---

## 🔄 Code Review Guidelines

### Review Checklist
- [ ] **Security**: No SQL injection, XSS, or authentication bypasses
- [ ] **Error Handling**: Comprehensive try-catch blocks
- [ ] **Performance**: No N+1 queries, proper indexing used
- [ ] **Testing**: Unit tests for new functionality
- [ ] **Documentation**: Code comments and docstrings
- [ ] **Backward Compatibility**: No breaking changes
- [ ] **Code Style**: Follows project conventions

### Git Workflow
```bash
# 1. Create feature branch
git checkout -b feature/improve-category-handling

# 2. Make incremental commits
git add specific_files
git commit -m "Add error handling to category creation"

# 3. Test thoroughly before merge
python -m pytest tests/
python app.py  # Manual testing

# 4. Create pull request with description
# Include: What changed, why, testing performed
```

---

## 📈 Performance Optimization

### Database Query Optimization
```python
# ✅ GOOD: Eager loading to prevent N+1 queries
students = User.query.options(
    joinedload(User.student_enrollments)
    .joinedload(StudentEnrollment.class_group)
).filter_by(role='student').all()

# ✅ GOOD: Pagination for large datasets
def get_paginated_results(page=1, per_page=20):
    return Category.query.paginate(
        page=page, per_page=per_page, error_out=False
    )

# ⚠️ AVOID: Loading all records at once
# all_records = LargeTable.query.all()  # Can cause memory issues
```

### Template Optimization
```html
<!-- ✅ GOOD: Minimize database calls in templates -->
{% for category in categories %}
    <div class="category-card">
        <h3>{{ category.name }}</h3>
        <p>Problems: {{ category.problem_count }}</p>  <!-- Pre-calculated -->
    </div>
{% endfor %}

<!-- ⚠️ AVOID: Database queries in templates -->
<!-- {% for category in categories %}
    <p>Problems: {{ category.problems|length }}</p>  <!-- Causes N+1 -->
{% endfor %} -->
```

### Caching Strategy
```python
from flask_caching import Cache

cache = Cache(app)

@cache.memoize(timeout=300)  # 5-minute cache
def get_category_statistics(school_id):
    """Expensive calculation that can be cached"""
    # Complex query or calculation
    return statistics

# Use cached function
@app.route('/categories')
def categories():
    stats = get_category_statistics(current_user.school_id)
    return render_template('categories.html', stats=stats)
```

---

## 🚨 Emergency Procedures

### Production Issue Response
1. **Immediate Assessment**
   ```bash
   # Check application logs
   tail -f /var/log/quested/app.log
   
   # Check database connectivity
   mysql -u $DB_USER -p$DB_PASS -h $DB_HOST -e "SELECT 1"
   
   # Check system resources
   htop
   df -h
   ```

2. **Quick Fixes**
   ```bash
   # Restart application service
   sudo systemctl restart quested
   
   # Clear cache if needed
   redis-cli FLUSHALL
   
   # Check service status
   sudo systemctl status quested
   ```

3. **Rollback Procedures**
   ```bash
   # Database rollback (if migration issues)
   flask db downgrade
   
   # Code rollback
   git checkout previous_stable_commit
   sudo systemctl restart quested
   ```

### Data Recovery
```sql
-- Database backup before changes
mysqldump -u $DB_USER -p$DB_PASS quested > backup_$(date +%Y%m%d_%H%M%S).sql

-- Point-in-time recovery
mysql -u $DB_USER -p$DB_PASS quested < backup_file.sql
```

---

## 📚 Additional Resources

### Development Tools
- **IDE Setup**: VS Code with Python extensions
- **Database Tools**: MySQL Workbench, phpMyAdmin
- **API Testing**: Postman collection available
- **Debugging**: Flask debug mode, logging configuration

### Documentation References
- **Flask Documentation**: https://flask.palletsprojects.com/
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/
- **Bootstrap Documentation**: https://getbootstrap.com/docs/
- **OpenAI API Documentation**: https://platform.openai.com/docs/

### Project-Specific Documentation
- **[DATABASE.md](../DATABASE.md)**: Complete schema reference
- **[ARCHITECTURE.md](../ARCHITECTURE.md)**: System architecture
- **[API_ENDPOINTS.md](./API_ENDPOINTS.md)**: API documentation
- **[TIMELINE.md](../TIMELINE.md)**: Development history

---

**🛡️ Following these development guidelines ensures safe, maintainable, and high-quality code for QuestEd. Always prioritize system stability over feature velocity.**