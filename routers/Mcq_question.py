from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import random
from pymongo.database import Database
from database import get_db

# Create router
router = APIRouter(
    prefix="/api/mcqs",
    tags=["mcqs"],
    responses={404: {"description": "Not found"}},
)

def get_mcq_collection(db: Database = Depends(get_db)):
    return db["mcq_questions"]


# -------------------------------
# Request/Response Models
# -------------------------------
class AnswerItem(BaseModel):
    question: str
    answer: str


class SubmitRequest(BaseModel):
    name: Optional[str] = "Guest"
    answers: List[AnswerItem]


# -------------------------------
# 🚀 API 1: Get MCQs by category
# -------------------------------
@router.get("/start-assignment")
async def start_assignment(category: Optional[str] = None, collection = Depends(get_mcq_collection)):
    query = {"category": category} if category else {}
    questions = list(collection.find(query, {"_id": 0}))

    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this category.")

    random.shuffle(questions)
    return {"questions": questions[:10]}


# -------------------------------
# 🚀 API 2: Submit user answers
# -------------------------------
@router.post("/submit-assignment")
async def submit_assignment(
    payload: SubmitRequest,
    collection = Depends(get_mcq_collection)
):
    user_name = payload.name
    user_answers = payload.answers

    if not user_answers:
        raise HTTPException(status_code=400, detail="No answers provided")

    all_questions = list(collection.find({}, {"_id": 0}))
    question_map = {q["question"]: q["answer"] for q in all_questions}

    score = 0
    result_details = []

    for q in user_answers:
        question_text = q.question
        user_answer = q.answer
        correct_answer = question_map.get(question_text)

        if not correct_answer:
            result_details.append({
                "question": question_text,
                "your_answer": user_answer,
                "correct_answer": "Question not found",
                "is_correct": False
            })
            continue

        is_correct = user_answer == correct_answer
        if is_correct:
            score += 1

        result_details.append({
            "question": question_text,
            "your_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct
        })

    return {
        "name": user_name,
        "score": score,
        "total": len(user_answers),
        "result": result_details
    }


# Export the router
def get_mcq_router():
    return router