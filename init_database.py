"""
Database Initialization Script for Neon Postgres
Run this script to initialize your database with the required schema.
"""

import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

load_dotenv()

def init_database():
    """Initialize the database with the schema from init_db.sql"""
    
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in .env file")
        print("Please add your Neon Postgres connection string to backend/.env")
        return False
    
    try:
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("📖 Reading init_db.sql...")
        with open('init_db.sql', 'r') as f:
            sql_script = f.read()
        
        print("🚀 Executing SQL script...")
        cursor.execute(sql_script)
        conn.commit()
        
        print("✅ Database initialized successfully!")
        print("\nCreated tables:")
        print("  - users")
        print("  - accounts")
        print("  - sessions")
        print("  - user_profiles")
        print("  - chat_messages")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"\n📊 Total tables in database: {len(tables)}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except FileNotFoundError:
        print("❌ ERROR: init_db.sql not found")
        print("Make sure you're running this script from the backend/ directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Database Initialization Script")
    print("=" * 50)
    print()
    
    success = init_database()
    
    if success:
        print("\n🎉 You're all set! You can now start the backend server.")
        print("Run: python main.py")
    else:
        print("\n❌ Initialization failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("1. Verify DATABASE_URL in .env is correct")
        print("2. Check that your Neon database is active")
        print("3. Ensure you have network connectivity")
