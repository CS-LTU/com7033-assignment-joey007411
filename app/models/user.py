"""
User Model Module

This module defines the User database model for the Medical Dashboard application.
It handles user authentication, role management, and account metadata.
"""

from datetime import datetime
from flask_login import UserMixin
from app import db

class User(db.Model, UserMixin):
    """
    User model representing a registered user in the system.
    
    Inherits from db.Model (SQLAlchemy) and UserMixin (Flask-Login).
    Provides user authentication and role-based access control.
    
    Attributes:
        id (int): Primary key, unique user identifier
        username (str): Unique username for login, max 150 characters
        email (str): Unique email address, max 254 characters
        password_hash (str): Hashed password using werkzeug.security
        role (str): User role - 'user' or 'admin', defaults to 'user'
        created_at (datetime): Account creation timestamp, auto-set to UTC now
    """
    
    __tablename__ = "users"
    
    # ========================================================================
    # PRIMARY KEY
    # ========================================================================
    id = db.Column(db.Integer, primary_key=True)
    
    # ========================================================================
    # AUTHENTICATION FIELDS
    # ========================================================================
    username = db.Column(
        db.String(150), 
        unique=True, 
        nullable=False,
        comment="Unique username for user login"
    )
    
    email = db.Column(
        db.String(254), 
        unique=True, 
        nullable=False,
        comment="Unique email address for account recovery and notifications"
    )
    
    password_hash = db.Column(
        db.String(255), 
        nullable=False,
        comment="Hashed password using werkzeug.security.generate_password_hash()"
    )
    
    # ========================================================================
    # AUTHORIZATION FIELD
    # ========================================================================
    role = db.Column(
        db.String(50), 
        default="user", 
        nullable=False,
        comment="User role: 'user' (standard) or 'admin' (system administrator)"
    )
    
    # ========================================================================
    # METADATA FIELDS
    # ========================================================================
    created_at = db.Column(
        db.DateTime, 
        default=datetime.utcnow,
        comment="Account creation timestamp, automatically set to UTC current time"
    )

    def __repr__(self):
        """
        String representation of User object for debugging.
        
        Returns:
            str: Formatted string with username
            
        Example:
            >>> user = User(username='john_doe')
            >>> print(user)
            <User john_doe>
        """
        return f"<User {self.username}>"
    
    def is_admin(self):
        """
        Check if user has admin role.
        
        Returns:
            bool: True if user role is 'admin', False otherwise
        """
        return self.role == 'admin'
    
    def is_regular_user(self):
        """
        Check if user has regular user role.
        
        Returns:
            bool: True if user role is 'user', False otherwise
        """
        return self.role == 'user'
    
    def to_dict(self):
        """
        Convert user object to dictionary representation.
        Excludes sensitive password hash.
        
        Returns:
            dict: User data without password_hash
            
        Example:
            >>> user = User(id=1, username='john', email='john@example.com', role='user')
            >>> user.to_dict()
            {'id': 1, 'username': 'john', 'email': 'john@example.com', 'role': 'user'}
        """
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }