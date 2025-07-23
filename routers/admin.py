from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from pymongo import MongoClient
from bson import ObjectId
from bson.binary import Binary
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
import jwt
import bcrypt

# Load environment variables
load_dotenv()

# JWT config
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
JWT_ALGORITHM = "HS256"

# Load environment variables
load_dotenv()

# MongoDB Setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME")]
admin_collection = db["users"]

# Router
router = APIRouter(tags=["admin"])

# Password Hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic Models
class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    firstName: str
    lastName: str
    phone: str = ""

# Helper Functions
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_admin_by_email(email: str):
    return admin_collection.find_one({"email": email})

# Routes
@router.post("")
def create_admin(admin: AdminCreate):
    if get_admin_by_email(admin.email):
        raise HTTPException(status_code=400, detail="Admin already exists")

    # Hash password using bcrypt
    hashed_password = bcrypt.hashpw(admin.password.encode("utf-8"), bcrypt.gensalt())
    
    admin_data = {
        "firstName": admin.firstName,
        "lastName": admin.lastName,
        "email": admin.email,
        "password": Binary(hashed_password),  # Store as bytes using Binary
        "userType": "admin",
        "phone": admin.phone,
        "created_at": datetime.utcnow()
    }

    admin_collection.insert_one(admin_data)
    return {"message": "Admin created successfully"}

@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_admin_by_email(form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Verify password directly using bcrypt
    if not bcrypt.checkpw(form_data.password.encode("utf-8"), user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Generate JWT token
    token_data = {
        "sub": user["email"],
        "userType": user["userType"],
        "exp": datetime.utcnow() + timedelta(hours=24),
        "firstName": user["firstName"],
        "lastName": user["lastName"]
    }
    access_token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "userType": user["userType"],
        "user": {
            "email": user["email"],
            "firstName": user["firstName"],
            "lastName": user["lastName"],
            "userType": user["userType"]
        }
    }

@router.get("/admin/dashboard")
def admin_dashboard():
    return {"message": "Welcome to the admin dashboard"}

# Get all users categorized by type
@router.get("/users", response_model=Dict[str, List[Dict[str, Any]]])
async def get_users():
    try:
        # Get all users from the database
        users = list(db.users.find({}, {
            "password": 0,  # Exclude password hash
            "reset_password_token": 0,
            "reset_password_expires": 0
        }))
        
        # Convert ObjectId to string for JSON serialization
        for user in users:
            user["_id"] = str(user["_id"])
            # Ensure all expected fields exist
            user.setdefault("userType", "individual")
            user.setdefault("firstName", "")
            user.setdefault("lastName", "")
            user.setdefault("email", "")
            user.setdefault("createdAt", "")
        
        # Categorize users by type
        categorized_users = {
            "admin": [u for u in users if u.get("userType") == "admin"],
            "individual": [u for u in users if u.get("userType") == "individual"],
            "enterprise": [u for u in users if u.get("userType") == "enterprise"]
        }
        
        return categorized_users
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching users: {str(e)}"
        )
