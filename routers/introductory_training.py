from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pymongo.collection import ReturnDocument
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from pymongo import MongoClient
from jose import JWTError, jwt
import os
from bson import ObjectId
 
load_dotenv()
 
 
# SECRET_KEY = os.getenv("SECRET_KEY", "your-secret")  # instead of JWT_SECRET
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")
print("🔐 Using JWT SECRET_KEY:", SECRET_KEY)
ALGORITHM = "HS256"
 
# router = APIRouter()
router = APIRouter(prefix="/training-progress", tags=["training-progress"])
 
class TrainingProgressIn(BaseModel):
    completedVideos: List[int]
    watchedVideos: List[int]
    certificateIssued: bool
 
client = MongoClient(os.getenv("MONGO_URI", "mongodb+srv://checkmain32:Kishore123@cluster0.jdacyq4.mongodb.net/admin?retryWrites=true&w=majority&appName=Cluster0/"))
db = client[os.getenv("MONGO_DB_NAME", "data")]
progress_collection = db["training_progress"]
 
# Utility function to decode JWT
def get_email_from_token(auth_header: str):
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
 
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("✅ Token decoded:", payload)
        return payload.get("email")
    except JWTError as e:
        print("❌ Token decode failed:", e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")
 
def fix_objectid(doc):
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc
 
@router.post("/save")
async def save_training_progress(
    progress: TrainingProgressIn,
    authorization: str = Header(None),
):
    email = get_email_from_token(authorization)
 
    print(f"📩 Saving progress for {email}")
    print(f"➡️ completedVideos: {progress.completedVideos}")
    print(f"➡️ watchedVideos: {progress.watchedVideos}")
    print(f"➡️ certificateIssued: {progress.certificateIssued}")
 
    updated = progress_collection.find_one_and_update(
        {"email": email},
        {
            "$set": {
                "completedVideos": progress.completedVideos,
                "watchedVideos": progress.watchedVideos,
                "certificateIssued": progress.certificateIssued,
            }
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
 
    print(f"✅ Mongo Updated Doc: {updated}")
    return {
        "message": "Progress saved successfully",
        "progress": fix_objectid(updated),
    }
 
 
 
# @router.get("/api/user/get-training-progress")
@router.get("/get")
async def get_training_progress(authorization: str = Header(None)):
    email = get_email_from_token(authorization)
 
    data = progress_collection.find_one({"email": email})
    if not data:
        return JSONResponse(
            content={
                "completedVideos": [],
                "watchedVideos": [],
                "certificateIssued": False,
            },
            status_code=200,
        )
 
    return {
        "completedVideos": data.get("completedVideos", []),
        "watchedVideos": data.get("watchedVideos", []),
        "certificateIssued": data.get("certificateIssued", False),
    }
 