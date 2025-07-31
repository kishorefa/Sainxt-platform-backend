from fastapi import APIRouter, Form, HTTPException, status
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import datetime

# Load environment variables from .env file
load_dotenv()

router = APIRouter()

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI", "mongodb+srv://checkmain32:Kishore123@cluster0.jdacyq4.mongodb.net/admin?retryWrites=true&w=majority&appName=Cluster0/"))
db_name = os.getenv("MONGO_DB_NAME", "data")
db = client[db_name]
collection = db["submitted_articles"]

# Debug: Print database and collection info
print(f"Connected to database: {db_name}")
print(f"Available collections: {db.list_collection_names()}")
print(f"Sample documents in submitted_articles: {list(collection.find().limit(2))}")

# Pydantic model for update endpoint
class UpdateContentModel(BaseModel):
    content: str

# --- Submit New Article ---
@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_article(
    article_id: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    status: str = Form(...)
):
    try:
        article_id = article_id.strip()
        title = title.strip()
        content = content.strip()
        status = status.strip()

        if not all([article_id, title, content, status]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All fields are required"
            )

        result = collection.update_one(
            {"article_id": article_id},
            {"$set": {
                "article_id": article_id,
                "title": title,
                "content": content,
                "status": status,
                "updated_at": datetime.datetime.utcnow()
            }},
            upsert=True
        )
        
        return {
            "message": "Article submitted successfully", 
            "article_id": article_id,
            "is_new": result.upserted_id is not None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit article: {str(e)}"
        )

# --- Get Full Article by ID ---
@router.get("/{article_id}", status_code=status.HTTP_200_OK)
async def get_article(article_id: str):
    try:
        article_id = article_id.strip()
        article = collection.find_one({"article_id": article_id})

        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )

        article["_id"] = str(article["_id"])
        return article
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch article: {str(e)}"
        )

# --- Get Only the Content of Article ---
@router.get("/{article_id}/content")
async def get_only_content(article_id: str):
    try:
        article = collection.find_one(
            {"article_id": article_id},
            {"content": 1, "_id": 0}
        )
        
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
            
        return article
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching article content: {str(e)}"
        )

# --- Delete Article ---
@router.delete("/{article_id}", status_code=status.HTTP_200_OK)
async def delete_article(article_id: str):
    """
    Delete an article by its ID or article_id
    """
    try:
        from bson import ObjectId
        from bson.errors import InvalidId
        
        # First try to find by _id (as ObjectId)
        try:
            query = {"_id": ObjectId(article_id)}
            existing_article = collection.find_one(query)
        except (InvalidId, TypeError):
            existing_article = None
        
        # If not found by _id as ObjectId, try as string _id
        if not existing_article:
            query = {"_id": article_id}
            existing_article = collection.find_one(query)
        
        # If still not found, try by article_id
        if not existing_article:
            query = {"article_id": article_id}
            existing_article = collection.find_one(query)
        
        if not existing_article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
        
        # Delete the article
        result = collection.delete_one(query)
        
        if result.deleted_count == 1:
            return {
                "status": "success",
                "message": "Article deleted successfully",
                "data": {
                    "id": str(existing_article.get("_id")),
                    "article_id": existing_article.get("article_id"),
                    "title": existing_article.get("title")
                }
            }
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete article"
        )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting article: {str(e)}"
        )

# --- Update Only the Content of Article ---
@router.put("/update-content/{article_id}", status_code=status.HTTP_200_OK)
async def update_article_content(article_id: str, update: UpdateContentModel):
    try:
        article_id = article_id.strip()
        
        if not article_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Article ID is required"
            )
            
        # Check if article exists
        existing_article = collection.find_one({"article_id": article_id})
        if not existing_article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
            
        # Update only the content
        result = collection.update_one(
            {"article_id": article_id},
            {"$set": {
                "content": update.content,
                "updated_at": datetime.datetime.utcnow()
            }}
        )
        
        if result.modified_count == 1:
            return {"status": "success", "message": "Content updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update article content"
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating article content: {str(e)}"
        )