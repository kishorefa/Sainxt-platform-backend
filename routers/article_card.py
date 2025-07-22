from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from pymongo import MongoClient
from dotenv import load_dotenv
import os, base64, datetime

load_dotenv()

router = APIRouter()
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME", "dataaa")]
featured_collection = db["featured_articles"]

@router.post("/admin/new_article-card")
async def add_article_card(
    title: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        image_bytes = await image.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        document = {
            "title": title.strip(),
            "description": description.strip(),
            "image_base64": image_base64,
            "image_filename": image.filename,
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow(),
        }

        result = featured_collection.insert_one(document)
        return {"message": "Card added", "id": str(result.inserted_id)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/public/featured-cards")
def get_featured_cards():
    cards = list(featured_collection.find({}, {"image_base64": 1, "title": 1, "description": 1}))
    for card in cards:
        card["_id"] = str(card["_id"])
    return {"cards": cards}
