from fastapi import APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import requests
import random
import string
import smtplib
from email.message import EmailMessage

router = APIRouter()

# ------------------ MongoDB Setup ------------------

client = MongoClient("mongodb+srv://checkmain32:Kishore123@cluster0.jdacyq4.mongodb.net/admin?retryWrites=true&w=majority&appName=Cluster0/")
db = client["interview_db"]
jd_collection = db["jd_questions"]
interview_collection = db["interview_responses"]
assigned_collection = db["interview_user"]

# ------------------ Prompt Template ------------------

PROMPT_TEMPLATE = """
You are an expert technical recruiter.
Based on the following job description, generate 5 to 10 professional and highly relevant interview questions that assess the candidate’s understanding, practical experience, and problem-solving skills related to the role.
Only provide the interview questions. Do not include explanations, summaries, rewritten paragraphs, or skills.

Job Description:
{job_description}

Format:
1. Question 1
2. Question 2
...
"""

# ------------------ Pydantic Schemas ------------------

class JDInput(BaseModel):
    jd_text: str

class SaveQuestionsInput(BaseModel):
    jd: str
    questions: list[str]
    assigned_by: str

class SubmitInterviewInput(BaseModel):
    username: str
    email: EmailStr | None = None
    job_description_id: str
    job_description: str | None = None
    responses: list[dict]

class SendMailInput(BaseModel):
    to_email: EmailStr
    jd: str
    questions: list[str]
    assigned_by: str
    company_name: str
    contact_email: str

class VerifyAccessInput(BaseModel):
    interview_id: str
    username: str
    password: str

# ------------------ Utility Functions ------------------

def call_llama(prompt: str, model: str = "llama3.2", url: str = "http://localhost:11434/api/generate") -> str:
    try:
        response = requests.post(url, json={"model": model, "prompt": prompt, "stream": False})
        response.raise_for_status()
        return response.json().get("response", "No response received.")
    except Exception as e:
        raise Exception(f"LLaMA API Error: {str(e)}")

def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "kishore47777@gmail.com"
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login("kishore47777@gmail.com", "zafcywyjfieajqls")  # ⚠️ Replace with env var
            smtp.send_message(msg)
    except Exception as e:
        raise Exception(f"Email failed: {str(e)}")

# ------------------ API Routes ------------------

@router.post("/generate")
def generate_questions(data: JDInput):
    prompt = PROMPT_TEMPLATE.format(job_description=data.jd_text.strip())
    result = call_llama(prompt)
    jd_collection.insert_one({
        "job_description": data.jd_text.strip(),
        "interview_questions": result,
        "timestamp": datetime.utcnow()
    })
    return {"response": result}

@router.get("/get_job_descriptions")
def get_job_descriptions():
    jds = list(jd_collection.find({}, {"job_description": 1}))
    for jd in jds:
        jd["_id"] = str(jd["_id"])
    return {"job_descriptions": jds}

@router.get("/get_questions/{jd_id}")
def get_questions(jd_id: str):
    try:
        jd = jd_collection.find_one({"_id": ObjectId(jd_id)})
        if not jd:
            raise HTTPException(status_code=404, detail="JD not found")

        questions = jd.get("interview_questions", "")
        if isinstance(questions, str):
            questions = [q.strip() for q in questions.split("\n") if q.strip()]

        return {
            "job_description_id": str(jd["_id"]),
            "job_description": jd.get("job_description", ""),
            "questions": questions
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/save_interview_questions")
def save_interview_questions(data: SaveQuestionsInput):
    assigned_collection.insert_one({
        "job_description": data.jd,
        "interview_questions": "\n".join(data.questions),
        "assigned_by": data.assigned_by,
        "timestamp": datetime.utcnow()
    })
    return {"status": "success", "message": "Interview questions saved."}

@router.post("/submit_interview")
def submit_interview(data: SubmitInterviewInput):
    jd_id = data.job_description_id
    job_desc = data.job_description or jd_collection.find_one({"_id": ObjectId(jd_id)}).get("job_description", "N/A")

    doc = {
        "username": data.username,
        "job_description_id": jd_id,
        "job_description": job_desc,
        "responses": data.responses,
        "submitted_at": datetime.utcnow()
    }

    if data.email:
        doc["candidate_email"] = data.email

    interview_collection.insert_one(doc)
    return {"status": "success", "message": "Interview submitted."}

@router.post("/send_mail")
def send_interview_email(data: SendMailInput):
    interview_id = str(ObjectId())
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    interview_url = f"http://localhost:3000/interview/{interview_id}"

    assigned_collection.insert_one({
        "_id": ObjectId(interview_id),
        "job_description": data.jd,
        "questions": data.questions,
        "assigned_by": data.assigned_by,
        "assigned_to": data.to_email,
        "password": password,
        "created_at": datetime.utcnow(),
        "status": "pending"
    })

    body = f"""Congratulations! You have been shortlisted for the next stage of the interview process at {data.company_name}.





Please find below the access details for your interview:



Interview Link: {interview_url}

Username: {data.to_email}

Password: {password}



Kindly ensure you join the interview using the above credentials. If you experience any issues accessing the link or have any questions, feel free to reach out to us at {data.contact_email}.



We look forward to speaking with you and learning more about your background.



Best regards,

{data.assigned_by}
"""
    send_email(data.to_email, f"Interview Access - {data.company_name}", body)

    return {
        "status": "success",
        "message": "Email sent",
        "interview_id": interview_id,
        "interview_url": interview_url
    }

@router.post("/verify_interview_access")
def verify_interview_access(data: VerifyAccessInput):
    interview = assigned_collection.find_one({
        "_id": ObjectId(data.interview_id),
        "assigned_to": data.username,
        "password": data.password
    })

    if not interview:
        raise HTTPException(status_code=401, detail="Invalid credentials or interview not found")

    if interview.get("status") == "completed":
        raise HTTPException(status_code=400, detail="This interview has already been completed")

    return {
        "status": "success",
        "interview_id": str(interview["_id"]),
        "job_description": interview.get("job_description", ""),
        "questions": interview.get("questions", "").split("\n") if isinstance(interview.get("questions"), str) else interview.get("questions", [])
    }
