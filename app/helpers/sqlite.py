"""
SQLite Database Connection and Management

This module provides utilities for connecting to SQLite database,
executing queries, and managing user authentication data.
"""

import sqlite3
import os
from flask import current_app


def get_sqlite_conn():
    """
    Get a SQLite database connection with row factory.
    
    Establishes connection to SQLite database from Flask config.
    Returns connection with row factory to enable dict-like access to results.
    
    Returns:
        sqlite3.Connection: Database connection with Row factory enabled
    
    Config Requirements:
        SQLALCHEMY_DATABASE_URI (str): SQLite database URI
                                       Format: sqlite:///path/to/database.db
    
    Features:
        - Row factory enables dict-like column access
        - Automatic type conversions
        - Connection pooling support
    
    Example:
        >>> conn = get_sqlite_conn()
        >>> cur = conn.cursor()
        >>> cur.execute("SELECT * FROM users WHERE id = ?", (1,))
        >>> user = cur.fetchone()
        >>> user['username']  # Access columns as dict keys
        >>> conn.close()
    
    Note:
        - Always close connection after use
        - Use with context managers for automatic cleanup:
          with get_sqlite_conn() as conn:
              cur = conn.cursor()
    """
    # Extract database path from Flask config
    db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///app.db')
    
    # Parse database path from SQLite URI
    # Format: sqlite:///path/to/db.db
    db_path = db_uri.replace('sqlite:///', '')
    
    # Establish connection
    conn = sqlite3.connect(db_path)
    
    # Enable dict-like access to row results using Column names
    conn.row_factory = sqlite3.Row
    
    return conn


def init_db(schema_path=None):
    """
    Initialize SQLite database with schema.
    
    Creates tables and initializes database structure if not exists.
    Can load schema from SQL file or create default tables.
    
    Args:
        schema_path (str, optional): Path to SQL schema file.
                                     If None, creates default tables.
    
    Returns:
        bool: True if initialization successful, False otherwise
    
    Example:
        >>> init_db('app/schema.sql')
        >>> # or with default schema:
        >>> init_db()
    
    Note:
        - Safe to call multiple times (idempotent)
        - SQL file should contain complete schema with CREATE TABLE statements
        - Default schema creates 'users' table
    """
    try:
        conn = get_sqlite_conn()
        cur = conn.cursor()
        
        if schema_path and os.path.exists(schema_path):
            # Load schema from file
            with open(schema_path, 'r') as f:
                schema = f.read()
            cur.executescript(schema)
        else:
            # Create default schema
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user' NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            """)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False


def execute_query(query, params=None, fetch_one=False):
    """
    Execute a parameterized SQL query safely.
    
    Provides a simplified interface for executing queries with automatic
    connection management and error handling.
    
    Args:
        query (str): SQL query with ? placeholders for parameters
        params (tuple, optional): Query parameters to bind
        fetch_one (bool): If True, returns single row; else returns all rows
    
    Returns:
        list or dict: Query results or empty list/dict if no results
    
    Raises:
        sqlite3.Error: Database errors are logged and re-raised
    
    Examples:
        >>> # Fetch single user
        >>> user = execute_query(
        ...     "SELECT * FROM users WHERE id = ?",
        ...     (1,),
        ...     fetch_one=True
        ... )
        
        >>> # Fetch multiple users
        >>> users = execute_query(
        ...     "SELECT * FROM users WHERE role = ?",
        ...     ('admin',)
        ... )
    
    Note:
        - Always use ? placeholders to prevent SQL injection
        - Returns empty list [] for no results on fetchall
        - Returns empty dict {} for no results on fetchone
    """
    try:
        conn = get_sqlite_conn()
        cur = conn.cursor()
        
        # Execute query with parameters
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        
        # Fetch results based on mode
        if fetch_one:
            result = cur.fetchone()
            return dict(result) if result else {}
        else:
            results = cur.fetchall()
            return [dict(row) for row in results]
    
    except sqlite3.Error as e:
        print(f"Database query error: {e}")
        raise
    finally:
        conn.close()


def check_sqlite_connection():
    """
    Test SQLite connection without raising exceptions.
    
    Safely validates database connection and accessibility.
    Useful for health checks and startup validation.
    
    Returns:
        bool: True if connection successful, False otherwise
    
    Example:
        >>> if check_sqlite_connection():
        ...     print("SQLite database is ready")
        ... else:
        ...     print("SQLite connection failed")
    """
    try:
        conn = get_sqlite_conn()
        cur = conn.cursor()
        # Execute simple query to verify connection
        cur.execute("SELECT 1")
        conn.close()
        return True
    except Exception as e:
        print(f"SQLite connection check failed: {e}")
        return False
