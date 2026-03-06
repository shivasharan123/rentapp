import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Environment Variables
DATABASE_URL = os.getenv("DATABASE_URL")  # Set this for Postgres (e.g., Supabase)
DB_NAME = "rent_app.db"  # Fallback for local SQLite

def get_db_connection():
    """Get a database connection (Postgres or SQLite)."""
    if DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            return conn
        except Exception as e:
            print(f"Error connecting to Postgres: {e}")
            raise
    else:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Initialize the database with tables (supports both SQLite and Postgres)."""
    conn = get_db_connection()
    c = conn.cursor()

    # Define SQL types based on DB engine
    if DATABASE_URL:
        # PostgreSQL syntax
        primary_key = "SERIAL PRIMARY KEY"
        timestamp_def = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    else:
        # SQLite syntax
        primary_key = "INTEGER PRIMARY KEY AUTOINCREMENT"
        timestamp_def = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"

    # Create Tenants Table
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS tenants (
            id {primary_key},
            phone_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            apartment_number TEXT NOT NULL,
            rent_amount REAL NOT NULL,
            balance REAL DEFAULT 0
        )
    ''')

    # Create Transactions Table
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS transactions (
            id {primary_key},
            tenant_id INTEGER NOT NULL,
            date {timestamp_def},
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            utr TEXT UNIQUE,
            status TEXT DEFAULT 'PENDING',
            image_url TEXT,
            FOREIGN KEY (tenant_id) REFERENCES tenants (id)
        )
    ''')

    # Create Maintenance Table
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS maintenance (
            id {primary_key},
            tenant_id INTEGER NOT NULL,
            date {timestamp_def},
            issue_description TEXT NOT NULL,
            status TEXT DEFAULT 'OPEN',
            FOREIGN KEY (tenant_id) REFERENCES tenants (id)
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Database initialized successfully ({'Postgres' if DATABASE_URL else 'SQLite'}).")

def add_test_data():
    """Add a dummy tenant for testing."""
    conn = get_db_connection()
    c = conn.cursor()

    # Parameter placeholder syntax depends on DB engine
    placeholder = "%s" if DATABASE_URL else "?"

    # Check if test tenant exists
    query_check = f"SELECT * FROM tenants WHERE phone_number = {placeholder}"
    c.execute(query_check, ('+1234567890',))
    
    if c.fetchone() is None:
        query_insert = f'''
            INSERT INTO tenants (phone_number, name, apartment_number, rent_amount, balance)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        '''
        c.execute(query_insert, ('+1234567890', 'Test Tenant', '101', 15000, 0))
        print("Test tenant added: Test Tenant (Apt 101)")
    else:
        print("Test tenant already exists.")
    
    conn.commit()
    conn.close()

def execute_query(conn, query, params=()):
    """Execute a query safely across SQLite and Postgres."""
    # Replace '?' with '%s' if using Postgres
    if DATABASE_URL:
        query = query.replace('?', '%s')
    
    cur = conn.cursor()
    cur.execute(query, params)
    return cur

if __name__ == "__main__":
    init_db()
    add_test_data()
