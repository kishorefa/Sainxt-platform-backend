from fastapi import APIRouter, Header, HTTPException
from jose import jwt, JWTError
from pymongo import MongoClient
import os
 
router = APIRouter(prefix="/certificate", tags=["certificate"])
 
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"
 
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGO_DB_NAME", "data")]
progress_collection = db["training_progress"]
 
def get_email_from_token(auth_header: str):
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("email")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
 
@router.get("/status")
async def check_certificate_status(authorization: str = Header(...)):
    email = get_email_from_token(authorization)
    doc = progress_collection.find_one({"email": email})
    return {"certificateIssued": doc.get("certificateIssued", False)} if doc else {"certificateIssued": False}
 