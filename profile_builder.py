from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo import MongoClient

app = FastAPI()

# MongoDB connection (local)
client = MongoClient("mongodb+srv://checkmain32:Kishore123@cluster0.jdacyq4.mongodb.net/admin?retryWrites=true&w=majority&appName=Cluster0/")
db = client["user_profiles"]
collection = db["profiles"]

last_email = None

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

@app.post("/api/save_profile")
async def api_save_profile(profile: ProfileModel):
    global last_email
    collection.insert_one(profile.dict())
    last_email = profile.email
    return JSONResponse(content={"message": "Profile saved successfully"}, status_code=201)

@app.post("/api/save_education")
async def api_save_education(education: EducationModel):
    global last_email
    if not last_email:
        raise HTTPException(status_code=400, detail="No profile found. Please submit profile first.")
    result = collection.update_one({"email": last_email}, {"$set": education.dict()})
    if result.modified_count == 1:
        return JSONResponse(content={"message": "Education details saved successfully"}, status_code=200)
    raise HTTPException(status_code=404, detail="User profile not found")

@app.post("/api/save_experience")
async def api_save_experience(exp: ExperienceModel):
    global last_email
    if not last_email:
        raise HTTPException(status_code=400, detail="No profile found. Submit profile first.")
    result = collection.update_one({"email": last_email}, {"$set": exp.dict()})
    if result.modified_count == 1:
        return JSONResponse(content={"message": "Experience saved successfully"}, status_code=200)
    raise HTTPException(status_code=404, detail="User profile not found")

@app.post("/api/save_project")
async def api_save_project(project: ProjectModel):
    global last_email
    if not last_email:
        raise HTTPException(status_code=400, detail="No profile found. Submit profile first.")
    result = collection.update_one({"email": last_email}, {"$set": project.dict()})
    if result.modified_count == 1:
        return JSONResponse(content={"message": "Project saved successfully"}, status_code=200)
    raise HTTPException(status_code=404, detail="User profile not found")

@app.post("/api/save_skills")
async def api_save_skills(skills: SkillsModel):
    global last_email
    if not last_email:
        raise HTTPException(status_code=400, detail="No profile found. Submit profile first.")
    result = collection.update_one({"email": last_email}, {"$set": skills.dict()})
    if result.modified_count == 1:
        return JSONResponse(content={"message": "Skills saved successfully"}, status_code=200)
    raise HTTPException(status_code=404, detail="User profile not found")

@app.post("/api/save_preferences")
async def api_save_preferences(pref: PreferencesModel):
    global last_email
    if not last_email:
        raise HTTPException(status_code=400, detail="No profile found. Submit profile first.")
    result = collection.update_one({"email": last_email}, {"$set": pref.dict()})
    if result.modified_count == 1:
        return JSONResponse(content={"message": "Preferences saved. Profile complete ✅"}, status_code=200)
    raise HTTPException(status_code=404, detail="User profile not found")