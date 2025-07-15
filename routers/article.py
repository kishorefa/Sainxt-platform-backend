from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

router = APIRouter()

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client[os.getenv("MONGO_DB_NAME", "data")]
collection = db["submitted_articles"]

# Pydantic model for update endpoint
class UpdateContentModel(BaseModel):
    content: str

# --- Submit New Article ---
@router.post("/submit/")
async def submit_article(
    article_id: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    status: str = Form(...)
):
    article_id = article_id.strip()
    title = title.strip()
    content = content.strip()
    status = status.strip()

    if not article_id or not title or not content or not status:
        raise HTTPException(status_code=400, detail="All fields are required")

    collection.update_one(
        {"article_id": article_id},
        {"$set": {
            "article_id": article_id,
            "title": title,
            "content": content,
            "status": status
        }},
        upsert=True
    )

    return {"message": "Article submitted successfully", "article_id": article_id}

# --- Get Full Article by ID ---
@router.get("/{article_id}")
async def get_article(article_id: str):
    article_id = article_id.strip()
    article = collection.find_one({"article_id": article_id})

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article["_id"] = str(article["_id"])  # Convert ObjectId to string
    return article

# --- Update Only the Content of Article ---
@router.put("/update-content/{article_id}")
async def update_article_content(article_id: str, update: UpdateContentModel):
    article_id = article_id.strip()
    new_content = update.content.strip()

    if not new_content:
        raise HTTPException(status_code=400, detail="Content is required")

    result = collection.update_one(
        {"article_id": article_id},
        {"$set": {"content": new_content}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"message": "Article content updated", "article_id": article_id}

# --- Get Only the Content of Article ---
@router.get("/get-content/{article_id}")
async def get_only_content(article_id: str):
    article_id = article_id.strip()
    article = collection.find_one({"article_id": article_id})

    return {"content": article.get("content", "")} if article else {"content": ""}
