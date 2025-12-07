from flask import Blueprint, redirect, url_for, render_template, request, flash, session, current_app, abort
from flask_login import login_required
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
import bleach
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId

from app.helpers.encryption import clean_text, decrypt_value, encrypt_value
from app.helpers.mongodb import get_mongo_collection
from app.helpers.sqlite import get_sqlite_conn

# Blueprint definitions for authentication and dashboard routes
auth_bp = Blueprint('auth', __name__)


# Check if Fernet encryption is available
try:
    from cryptography.fernet import Fernet, InvalidToken
    _has_fernet = True
except Exception:
    _has_fernet = False


# ============================================================================
# AUTH ROUTES - User authentication and registration
# ============================================================================

@auth_bp.route('/')
def index():
    """Redirect to login page on root access"""
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login with email and password validation.
    Stores user_id, username, and role in session.
    """
    if request.method == 'POST':
        # Sanitize email input to prevent injection attacks
        email = clean_text(request.form.get('email', ''), maxlen=254)
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password required', 'error')
            return render_template('login.html')

        # Query SQLite database for user credentials
        conn = get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash, role FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        conn.close()
        
        # Verify password hash and create session
        if row and check_password_hash(row['password_hash'], password):
            session.clear()
            session['user_id'] = row['id']
            session['username'] = row['username']
            session['role'] = row['role']
            return redirect(url_for('dashboard.dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration with input validation.
    Admin role requires secret code verification.
    """
    if request.method == 'POST':
        # Sanitize all user inputs
        username = clean_text(request.form.get('username', ''), maxlen=150)
        email = clean_text(request.form.get('email', ''), maxlen=254)
        password = request.form.get('password', '')
        role = clean_text(request.form.get('role', 'user'), maxlen=50)
        
        # Validate required fields
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        # Enforce minimum password length
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('register.html')
        
        # Validate secret code for admin registration
        if role == 'admin':
            secret_code = clean_text(request.form.get('secret_code', ''), maxlen=100)
            admin_secret = os.getenv('ADMIN_SECRET_CODE', 'admin123')
            if not secret_code or secret_code != admin_secret:
                flash('Invalid or missing secret code for admin role', 'error')
                return render_template('register.html')

        # Hash password using werkzeug security
        password_hash = generate_password_hash(password)
        conn = get_sqlite_conn()
        cur = conn.cursor()
        try:
            # Insert new user into database
            cur.execute("INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                        (username, email, password_hash, role))
            conn.commit()
            flash('Account created — please log in', 'success')
            return redirect(url_for('auth.login'))
        except sqlite3.IntegrityError:
            # Handle duplicate username or email
            flash('User with that email or username already exists', 'error')
        finally:
            conn.close()
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    """Clear session and redirect to login"""
    session.clear()
    return redirect(url_for('auth.login'))