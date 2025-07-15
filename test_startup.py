#!/usr/bin/env python3
"""
Minimal test script to diagnose startup issues
"""

import traceback
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all required imports"""
    try:
        print("Testing imports...")
        
        # Basic Flask imports
        from flask import Flask
        print("✓ Flask import successful")
        
        # Database imports
        import mysql.connector
        print("✓ MySQL connector import successful")
        
        import pymysql
        print("✓ PyMySQL import successful")
        
        # App imports
        from app import create_app
        print("✓ App import successful")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False

def test_database_connection():
    """Test database connection directly"""
    try:
        print("\nTesting database connection...")
        import mysql.connector
        
        connection = mysql.connector.connect(
            host='localhost',
            user='QuestEd',
            password='QuestEd-03012025MySQL',
            database='quested',
            port=3306
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            print("✓ Database connection successful")
            cursor.close()
            connection.close()
            return True
        else:
            print("✗ Database connection failed: Unexpected result")
            return False
            
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        traceback.print_exc()
        return False

def test_app_creation():
    """Test app creation"""
    try:
        print("\nTesting app creation...")
        from app import create_app
        
        # Create app with minimal config
        app = create_app()
        print("✓ App creation successful")
        
        # Test app context
        with app.app_context():
            print("✓ App context successful")
            
        return app
    except Exception as e:
        print(f"✗ App creation failed: {e}")
        traceback.print_exc()
        return None

def main():
    """Main test function"""
    print("=== QuestEd Startup Diagnostic ===\n")
    
    # Test imports
    if not test_imports():
        print("\n❌ Import test failed. Cannot continue.")
        return False
    
    # Test database
    if not test_database_connection():
        print("\n❌ Database test failed. Cannot continue.")
        return False
    
    # Test app creation
    app = test_app_creation()
    if not app:
        print("\n❌ App creation failed. Cannot continue.")
        return False
    
    # Try to start server
    try:
        print("\nTesting server startup...")
        print("Starting server on localhost:5000...")
        app.run(host='localhost', port=5000, debug=True, use_reloader=False)
        
    except Exception as e:
        print(f"✗ Server startup failed: {e}")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)