from fastapi import APIRouter, Depends
from pymongo.database import Database
from pymongo import MongoClient
from database import get_db  
import os
 
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
 
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db_name = os.getenv("MONGO_DB_NAME", "dataaa")
db = client[db_name]
users_collection = db["users"]
progress_collection = db["training_progress"]
 
@router.get("/metrics")
async def get_platform_metrics(db: Database = Depends(get_db)):
 
    # Count total users (all user types: individual, enterprise, admin, etc.)
    total_users = users_collection.count_documents({})
 
    # Count enterprise clients only
    enterprise_clients = users_collection.count_documents({"userType": "enterprise"})
 
    # Count active assessments = number of documents in training_progress
    active_assessments = progress_collection.count_documents({})
 
    return {
        "total_users": total_users,
        "enterprise_clients": enterprise_clients,
        "active_assessments": active_assessments
    }
 