from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get MongoDB URI from environment variables or use default
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB_NAME", "data")

# Global database connection
_client: Optional[MongoClient] = None

def get_client() -> MongoClient:
    """Get or create MongoDB client."""
    global _client
    if _client is not None:
        return _client
        
    try:
        client = MongoClient(
            MONGO_URI,
            server_api=ServerApi('1'),
            connectTimeoutMS=5000,
            serverSelectionTimeoutMS=5000
        )
        # Test the connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB")
        _client = client
        return client
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        _client = None
        raise

def get_db() -> Database:
    """Get database instance.
    
    Returns:
        Database: The MongoDB database instance.
        
    Raises:
        RuntimeError: If the database client cannot be initialized.
    """
    try:
        client = get_client()
        if client is None:
            raise RuntimeError("Failed to initialize database client")
        return client[DB_NAME]
    except Exception as e:
        print(f"❌ Error getting database instance: {e}")
        raise RuntimeError("Failed to get database instance") from e

def close_connection():
    """Close MongoDB connection."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        print("✅ MongoDB connection closed")
