import os
import requests
from sqlalchemy import create_engine, text
from config import Config

def test_database_connection():
    """Test PostgreSQL database connection"""
    print("Testing database connection...")
    try:
        config = Config()
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print("❌ Database connection failed:")
        print(f"Error: {str(e)}")
        return False

def test_apache_music_access():
    """Test Apache music directory access"""
    print("\nTesting Apache music directory access...")
    try:
        response = requests.get('http://localhost/music/')
        if response.status_code == 200:
            print("✅ Apache music directory is accessible!")
            return True
        else:
            print(f"❌ Apache returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print("❌ Failed to access Apache music directory:")
        print(f"Error: {str(e)}")
        return False

if __name__ == '__main__':
    print("Running setup tests...")
    db_ok = test_database_connection()
    apache_ok = test_apache_music_access()

    if db_ok and apache_ok:
        print("\n✅ All tests passed! Your setup is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
