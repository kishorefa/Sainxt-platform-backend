from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime, timezone
import jwt
import os
import datetime
from typing import Optional, List, Dict, Any
import logging
from dotenv import load_dotenv
from bson import ObjectId

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
JWT_ALGORITHM = "HS256"

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Assuming MongoDB connection is handled in fastapi_app.py and injected
router = APIRouter()

client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client[os.getenv("MONGO_DB_NAME", "dataaa")]
profile_collection = db["profiles"]

# Pydantic Models
class ProfileModel(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    location: str
    dob: str
    description: str

class EducationModel(BaseModel):
    university: str
    degree_level: str
    major: str
    graduation_year: str
    cgpa: str
    additional_info: str

class ExperienceModel(BaseModel):
    work_experience: str
    job_title: str
    company: str
    location: str
    start_date: str
    end_date: str
    description: str

class ProjectModel(BaseModel):
    project_title: str
    project_url: str
    start_date: str
    end_date: str
    description: str

class SkillsModel(BaseModel):
    technical_skills: str
    soft_skills: str
    language: str
    proficiency: str

class PreferencesModel(BaseModel):
    job_types: str
    salary_expectations: str
    location_preferences: str
    work_environment: str
    industry_preferences: str
    company_size: str
    career_goals: str

# Dependency to get the database collection
def get_db_collection():
    from fastapi import Request
    from fastapi_app import app
    return app.state.db['profiles']

last_email = None

@router.post('/save_profile')
async def api_save_profile(profile: ProfileModel, collection=Depends(get_db_collection)):
    global last_email
    last_email = profile.email

    # Check if the profile already exists
    existing_profile = collection.find_one({'email': profile.email})

    if existing_profile:
        # Update existing profile
        result = collection.update_one(
            {'email': profile.email},
            {'$set': profile.dict()}
        )
        if result.modified_count:
            return JSONResponse(content={'message': 'Profile updated successfully'}, status_code=200)
        else:
            return JSONResponse(content={'message': 'Profile already up to date'}, status_code=200)
    else:
        # Insert new profile
        collection.insert_one(profile.dict())
        return JSONResponse(content={'message': 'Profile created successfully'}, status_code=201)


@router.post('/save_education')
async def api_save_education(education: EducationModel, collection=Depends(get_db_collection)):
    global last_email
    if not last_email:
        raise HTTPException(status_code=400, detail='No profile found. Please submit profile first.')

    collection.update_one(
        {'email': last_email},
        {'$set': education.dict()},
        upsert=True
    )
    return JSONResponse(content={'message': 'Education details saved/updated successfully'}, status_code=200)


@router.post('/save_experience')
async def api_save_experience(exp: ExperienceModel, collection=Depends(get_db_collection)):
    global last_email
    if not last_email:
        raise HTTPException(status_code=400, detail='No profile found. Submit profile first.')

    collection.update_one(
        {'email': last_email},
        {'$set': exp.dict()},
        upsert=True
    )
    return JSONResponse(content={'message': 'Experience saved/updated successfully'}, status_code=200)


@router.post('/save_project')
async def api_save_project(project: ProjectModel, collection=Depends(get_db_collection)):
    global last_email
    if not last_email:
        raise HTTPException(status_code=400, detail='No profile found. Submit profile first.')

    collection.update_one(
        {'email': last_email},
        {'$set': project.dict()},
        upsert=True
    )
    return JSONResponse(content={'message': 'Project saved/updated successfully'}, status_code=200)


@router.post('/save_skills')
async def api_save_skills(skills: SkillsModel, collection=Depends(get_db_collection)):
    global last_email
    if not last_email:
        raise HTTPException(status_code=400, detail='No profile found. Submit profile first.')

    collection.update_one(
        {'email': last_email},
        {'$set': skills.dict()},
        upsert=True
    )
    return JSONResponse(content={'message': 'Skills saved/updated successfully'}, status_code=200)


@router.post('/save_preferences')
async def api_save_preferences(pref: PreferencesModel, collection=Depends(get_db_collection)):
    global last_email
    if not last_email:
        raise HTTPException(status_code=400, detail='No profile found. Submit profile first.')

    collection.update_one(
        {'email': last_email},
        {'$set': pref.dict()},
        upsert=True
    )
    return JSONResponse(content={'message': 'Preferences saved/updated successfully'}, status_code=200)




@router.get("/score")
def get_profile_score(email: str):
    profile = profile_collection.find_one({"email": email})
    if not profile:
        return {"exists": False}

    scores = profile.get("scores", {})
    try:
        profile_score = float(scores.get("profile_score", 0))
        qualification_score = float(scores.get("qualification_score", 0))
        skill_score = float(scores.get("skill_score", 0))
        soft_skills_score = float(scores.get("soft_skills_score", 0))
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid score data")

    avg_percent = (
        (profile_score / 5) +
        (qualification_score / 5) +
        (skill_score / 5) +
        (soft_skills_score / 5)
    ) * 25

    return {
        "exists": True,
        "percentage": round(avg_percent, 1)
    }

@router.get("/profile")
def get_profile_by_email(email: str):
    profile = profile_collection.find_one({"email": email})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile["_id"] = str(profile["_id"])
    if "user_id" in profile:
        profile["user_id"] = str(profile["user_id"])
        
    return profile









@router.get('/user/profile')
async def get_user_profile(token: str = Depends(oauth2_scheme), collection=Depends(get_db_collection)):
    try:
        print(f"Received token: {token}")
        
        # Decode the JWT token to get the user's email and ID
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_email = payload.get('email')
            user_id = payload.get('id')
            print(f"Decoded from token - email: {user_email}, user_id: {user_id}")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail='Token has expired')
        except jwt.InvalidTokenError as e:
            print(f"Invalid token error: {str(e)}")
            raise HTTPException(status_code=401, detail='Invalid token')
        
        if not user_email or not user_id:
            print(f"Missing required user data in token. Email: {user_email}, ID: {user_id}")
            raise HTTPException(status_code=400, detail='Incomplete user data in token')
        
        # Import ObjectId for MongoDB document IDs
        from bson import ObjectId
        
        # Get the database instance
        db = collection.database
        
        # Get user details from users collection
        user = db.users.find_one({"email": user_email, "_id": ObjectId(user_id)})
        
        if not user:
            print(f"User not found in users collection: {user_email}")
            raise HTTPException(status_code=404, detail='User account not found')
            
        # Try to find the user's profile
        user_profile = collection.find_one({"user_id": ObjectId(user_id)})
        
        # If profile doesn't exist, create one
        if not user_profile:
            print(f"No profile found for user {user_email}, creating one...")
            profile_data = {
                "user_id": ObjectId(user_id),
                "email": user_email,
                "first_name": user.get('firstName', ''),
                "last_name": user.get('lastName', ''),
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow()
            }
            
            # Insert the new profile
            result = collection.insert_one(profile_data)
            print(f"Created new profile with ID: {result.inserted_id}")
            
            # Get the newly created profile
            user_profile = collection.find_one({"_id": result.inserted_id})
        
        # Convert ObjectId to string for JSON serialization
        if user_profile and '_id' in user_profile:
            user_profile['_id'] = str(user_profile['_id'])
        if user_profile and 'user_id' in user_profile:
            user_profile['user_id'] = str(user_profile['user_id'])
            
        print(f"Returning profile: {user_profile}")
        return user_profile
        
    except HTTPException as he:
        print(f"HTTP Exception: {he.detail}")
        raise he
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail='Internal server error')
