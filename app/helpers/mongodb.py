"""
MongoDB Connection and Collection Management

This module provides utilities for connecting to MongoDB and accessing
patient data collections. It handles connection pooling and error management.
"""

import os
from pymongo import MongoClient
from flask import current_app


def get_mongo_collection(collection_name=None):
    """
    Get a MongoDB collection instance with connection pooling.
    
    Establishes connection to MongoDB using Flask config settings.
    Returns both the collection and client for proper resource cleanup.
    
    Args:
        collection_name (str, optional): Collection name to access.
                                        Defaults to MONGO_COLLECTION from config.
    
    Returns:
        tuple: (collection, client) where:
            - collection: PyMongo collection object for database operations
            - client: MongoClient instance for connection management
    
    Raises:
        ConnectionError: If MongoDB connection fails
        
    Config Requirements:
        MONGO_URI (str): MongoDB connection string (e.g., mongodb://localhost:27017)
        MONGO_DB (str): Database name (e.g., 'healthcare')
        MONGO_COLLECTION (str): Default collection name (e.g., 'strokes')
    
    Example:
        >>> coll, client = get_mongo_collection()
        >>> try:
        ...     patients = list(coll.find())
        ... finally:
        ...     client.close()
    
    Note:
        - Always close client in finally block to release connection
        - Collection name defaults to MONGO_COLLECTION if not provided
        - Supports custom collection names for different data types
    """
    # Retrieve configuration from Flask app context
    mongo_uri = current_app.config.get('MONGO_URI', 'mongodb://localhost:27017')
    db_name = current_app.config.get('MONGO_DB', 'healthcare')
    coll_name = collection_name or current_app.config.get('MONGO_COLLECTION', 'strokes')
    
    # Create MongoDB client with connection pooling
    client = MongoClient(mongo_uri)
    
    # Access database and collection
    db = client[db_name]
    collection = db[coll_name]
    
    return collection, client


def get_mongo_db():
    """
    Get a MongoDB database instance for multi-collection operations.
    
    Returns the database object when you need to work with multiple
    collections within the same database.
    
    Returns:
        tuple: (db, client) where:
            - db: PyMongo database object
            - client: MongoClient instance for cleanup
    
    Raises:
        ConnectionError: If MongoDB connection fails
        
    Example:
        >>> db, client = get_mongo_db()
        >>> try:
        ...     patients_coll = db['strokes']
        ...     users_coll = db['users']
        ... finally:
        ...     client.close()
    """
    # Retrieve MongoDB configuration
    mongo_uri = current_app.config.get('MONGO_URI', 'mongodb://localhost:27017')
    db_name = current_app.config.get('MONGO_DB', 'healthcare')
    
    # Create client and access database
    client = MongoClient(mongo_uri)
    db = client[db_name]
    
    return db, client


def create_indexes(collection):
    """
    Create database indexes for improved query performance.
    
    Establishes indexes on frequently queried fields to optimize
    MongoDB performance for common operations.
    
    Args:
        collection: PyMongo collection object
    
    Indexes Created:
        - 'id': Single field index on patient ID
        - 'stroke': Index on stroke status for filtering
        - 'age': Index on age for range queries
        - 'owner_user_id': Index for user-specific queries
    
    Example:
        >>> coll, client = get_mongo_collection()
        >>> try:
        ...     create_indexes(coll)
        ... finally:
        ...     client.close()
    
    Note:
        - Indexes improve query performance but slow down writes
        - Safe to call multiple times (idempotent)
        - Run during application initialization or data migration
    """
    # Create index on patient ID field
    collection.create_index('id', sparse=True)
    
    # Create index on stroke status for filtering
    collection.create_index('stroke')
    
    # Create index on age for range queries
    collection.create_index('age')
    
    # Create index on owner user ID for multi-user filtering
    collection.create_index('owner_user_id')


def check_mongo_connection():
    """
    Test MongoDB connection without raising exceptions.
    
    Safely checks if MongoDB is accessible and returns connection status.
    Useful for health checks and startup validation.
    
    Returns:
        bool: True if connection successful, False otherwise
    
    Example:
        >>> if check_mongo_connection():
        ...     print("MongoDB is connected")
        ... else:
        ...     print("MongoDB connection failed")
    """
    try:
        coll, client = get_mongo_collection()
        # Ping server to verify connection
        client.admin.command('ping')
        client.close()
        return True
    except Exception as e:
        print(f"MongoDB connection check failed: {e}")
        return False