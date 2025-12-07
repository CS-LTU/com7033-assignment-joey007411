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
dashboard_bp = Blueprint('dashboard', __name__)

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

@dashboard_bp.route('/dashboard')
def dashboard():
    """
    Display main dashboard with patient statistics and aggregations.
    Retrieves data from MongoDB collection.
    """
    coll, client = get_mongo_collection()
    try:
        # Fetch recent patient records (limit 10)
        patients = list(coll.find({}, {"_id": 0, "id": 1, "age": 1, "gender": 1, "Residence_type": 1, "work_type": 1, "avg_glucose_level": 1, "bmi": 1, "stroke": 1}).limit(10))
        count = coll.count_documents({})

        # Calculate average BMI
        avg_bmi = coll.aggregate([{"$group": {"_id": None, "avg_bmi": {"$avg": "$bmi"}}}])
        avg_bmi = next(avg_bmi, {}).get("avg_bmi", 0)

        # Calculate average glucose level
        avg_glucose = coll.aggregate([{"$group": {"_id": None, "avg_glucose": {"$avg": "$avg_glucose_level"}}}])
        avg_glucose = next(avg_glucose, {}).get("avg_glucose", 0)

        # Count stroke cases
        stroke_stats = coll.aggregate([
            {"$group": {"_id": "$stroke", "count": {"$sum": 1}}}
        ])
        stroke_data = {item["_id"]: item["count"] for item in stroke_stats}
        stroke_count = stroke_data.get(1, 0)
        no_stroke_count = stroke_data.get(0, 0)

        # Aggregate gender distribution
        gender_stats = coll.aggregate([
            {"$group": {"_id": "$gender", "count": {"$sum": 1}}}
        ])
        gender_data = {item["_id"]: item["count"] for item in gender_stats}
    finally:
        client.close()

    return render_template(
        'dashboard.html',
        patients=patients,
        patients_count=count,
        avg_bmi=avg_bmi,
        avg_glucose=avg_glucose,
        stroke_count=stroke_count,
        no_stroke_count=no_stroke_count,
        gender_data=gender_data,
        user_role=session.get('role', 'user')
    )

@dashboard_bp.route('/patient_list_full')
def patient_list_full():
    """
    Display paginated list of all patients from MongoDB.
    Supports pagination with configurable page size.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of patients per page
    coll, client = get_mongo_collection()
    try:
        # Calculate pagination parameters
        total_patients = coll.count_documents({})
        total_pages = (total_patients + per_page - 1) // per_page
        skip = (page - 1) * per_page
        docs = list(coll.find().skip(skip).limit(per_page))
        
        # Decrypt sensitive fields if encryption is enabled
        decrypt_keys = ['name', 'mrn', 'smoking_status', 'ever_married', 'work_type', 'Residence_type']
        for d in docs:
            for k in decrypt_keys:
                if k in d and isinstance(d.get(k), str) and _has_fernet:
                    try:
                        d[k] = decrypt_value(d.get(k))
                    except Exception:
                        pass
    finally:
        client.close()

    return render_template(
        'patient_list_full.html',
        patients=docs,
        current_page=page,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
        prev_page=page - 1,
        next_page=page + 1
    )

@dashboard_bp.route('/add_update_patient', methods=['GET', 'POST'])
def add_update_patient():
    """
    Add or update patient records in MongoDB.
    Handles form validation, encryption, and document operations.
    """
    if request.method == 'POST':
        # Sanitize all input fields
        pid = clean_text(request.form.get('id'), maxlen=32)
        dataset_id = clean_text(request.form.get('patient_id', ''), maxlen=32)
        gender = clean_text(request.form.get('gender', ''), maxlen=32)
        age_raw = clean_text(request.form.get('age', ''), maxlen=8)
        hypertension_raw = clean_text(request.form.get('hypertension', ''), maxlen=4)
        heart_disease_raw = clean_text(request.form.get('heart_disease', ''), maxlen=4)
        ever_married = clean_text(request.form.get('ever_married', ''), maxlen=16)
        work_type = clean_text(request.form.get('work_type', ''), maxlen=64)
        residence_type = clean_text(request.form.get('Residence_type', ''), maxlen=32)
        avg_glucose_raw = clean_text(request.form.get('avg_glucose_level', ''), maxlen=32)
        bmi_raw = clean_text(request.form.get('bmi', ''), maxlen=32)
        smoking_status = clean_text(request.form.get('smoking_status', ''), maxlen=64)
        stroke_raw = clean_text(request.form.get('stroke', ''), maxlen=4)

        # Validate required fields
        if not dataset_id:
            flash('Dataset id is required', 'error')
            return render_template('add_update_patient.html', patient=request.form)

        # Helper functions to convert string inputs to numeric types
        def to_int(v):
            try:
                return int(v)
            except Exception:
                return None
        
        def to_float(v):
            try:
                return float(v)
            except Exception:
                return None

        # Convert fields to appropriate types
        age = to_int(age_raw)
        hypertension = to_int(hypertension_raw)
        heart_disease = to_int(heart_disease_raw)
        stroke = to_int(stroke_raw)
        avg_glucose_level = to_float(avg_glucose_raw)
        bmi = to_float(bmi_raw)

        # Helper to conditionally encrypt sensitive fields
        def maybe_encrypt(val):
            if val is None:
                return None
            return encrypt_value(val) if (_has_fernet and isinstance(val, str) and val != '') else val

        # Build document for MongoDB
        doc = {
            'id': to_int(dataset_id) if dataset_id.isdigit() else dataset_id,
            'gender': maybe_encrypt(gender),
            'age': age,
            'hypertension': hypertension,
            'heart_disease': heart_disease,
            'ever_married': maybe_encrypt(ever_married),
            'work_type': maybe_encrypt(work_type),
            'Residence_type': maybe_encrypt(residence_type),
            'avg_glucose_level': avg_glucose_level,
            'bmi': bmi,
            'smoking_status': maybe_encrypt(smoking_status),
            'stroke': stroke,
            'owner_user_id': session.get('user_id')
        }

        coll, client = get_mongo_collection()
        try:
            if pid:
                # Update existing document
                try:
                    oid = ObjectId(pid)
                    coll.update_one({'_id': oid}, {'$set': doc})
                    flash('Patient updated', 'success')
                except Exception:
                    flash('Invalid patient id', 'error')
            else:
                # Insert new document
                coll.insert_one(doc)
                flash('Patient added', 'success')
        finally:
            client.close()
        return redirect(url_for('dashboard.patient_list_full'))

    # GET - load existing patient if id provided
    pid = request.args.get('id')
    patient = {}
    if pid:
        print(f"Received patient ID: {pid}")
        coll, client = get_mongo_collection()
        try:
            # Validate if `pid` is a valid ObjectId
            try:
                oid = ObjectId(pid)  # Attempt to convert `pid` to ObjectId
                patient = coll.find_one({'_id': oid})
            except InvalidId:
                print(f"Invalid ObjectId: {pid}. Querying by custom `id` field.")
                # If not a valid ObjectId, query using the custom `id` field
                try:
                    patient = coll.find_one({'id': int(pid)})  # Assuming `id` is an integer
                except ValueError:
                    print(f"Invalid integer ID: {pid}")
                    patient = {}
            if patient:
                print(f"Patient found: {patient}")
                # Decrypt known string fields for the edit form
                decrypt_keys = ['gender', 'ever_married', 'work_type', 'Residence_type', 'smoking_status']
                for k in decrypt_keys:
                    if k in patient and isinstance(patient.get(k), str) and _has_fernet:
                        try:
                            patient[k] = decrypt_value(patient.get(k))
                        except Exception as e:
                            print(f"Decryption failed for key '{k}': {e}")
            else:
                print("No patient found with the given ID.")
        except Exception as e:
            print(f"Database error: {e}")
        finally:
            client.close()
    else:
        print("No patient ID provided in the request.")
    return render_template('add_update_patient.html', patient=patient)

@dashboard_bp.route('/patient_delete', methods=['POST'])
def patient_delete():
    """Delete a patient record from MongoDB"""
    pid = request.form.get('id')
    if not pid:
        abort(400)
    coll, client = get_mongo_collection()
    try:
        try:
            coll.delete_one({'_id': ObjectId(pid)})
            flash('Patient deleted', 'success')
        except Exception:
            flash('Failed to delete patient', 'error')
    finally:
        client.close()
    return redirect(url_for('dashboard.patient_list_full'))


# ============================================================================
# USER MANAGEMENT ROUTES - Admin-only operations
# ============================================================================

def admin_required(f):
    """
    Decorator to restrict route access to admin users only.
    Redirects non-admin users to dashboard with error message.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@dashboard_bp.route('/user_dashboard')
@admin_required
def user_dashboard():
    """Display list of all users in the system"""
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, role FROM users ORDER BY id DESC")
    users = cur.fetchall()
    conn.close()
    return render_template('user_dashboard.html', users=users)

@dashboard_bp.route('/user_update', methods=['POST'])
@admin_required
def user_update():
    """Update user details (username, email, role)"""
    user_id = clean_text(request.form.get('id'), maxlen=32)
    username = clean_text(request.form.get('username', ''), maxlen=150)
    email = clean_text(request.form.get('email', ''), maxlen=254)
    role = clean_text(request.form.get('role', 'user'), maxlen=50)
    
    if not user_id or not username or not email:
        flash('All fields are required', 'error')
        return redirect(url_for('dashboard.user_dashboard'))
    
    conn = get_sqlite_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET username = ?, email = ?, role = ? WHERE id = ?",
                    (username, email, role, user_id))
        conn.commit()
        flash('User updated successfully', 'success')
    except sqlite3.IntegrityError:
        flash('Email or username already exists', 'error')
    finally:
        conn.close()
    return redirect(url_for('dashboard.user_dashboard'))

@dashboard_bp.route('/user_delete', methods=['POST'])
@admin_required
def user_delete():
    """Delete a user account (prevents self-deletion)"""
    user_id = clean_text(request.form.get('id'), maxlen=32)
    
    # Prevent admin from deleting their own account
    if not user_id or int(user_id) == session.get('user_id'):
        flash('Cannot delete your own account', 'error')
        return redirect(url_for('dashboard.user_dashboard'))
    
    conn = get_sqlite_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        flash('User deleted successfully', 'success')
    except Exception:
        flash('Failed to delete user', 'error')
    finally:
        conn.close()
    return redirect(url_for('dashboard.user_dashboard'))
