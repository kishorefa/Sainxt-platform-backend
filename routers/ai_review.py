from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
import requests
import json
import time

router = APIRouter(
    prefix="/ai-review",
    tags=["AI Review"],
    responses={404: {"description": "Not found"}},
)

class EmailRequest(BaseModel):
    email: str

# MongoDB connection (shared with main app)
client = MongoClient("mongodb://localhost:27017/")
db = client["data"]
collection = db["profiles"]

@router.post("/generate-scores")
async def generate_scores(payload: EmailRequest):
    try:
        print(f"🎯 Received request for email: {payload.email}")
        email = payload.email.strip()
        
        print("🔍 Connected to database:", db.name)
        print("🔍 Using collection:", collection.name)

        # Fetch and clean profile
        print("🔍 Fetching profile from database...")
        profile = collection.find_one({"email": email}, {"_id": 0})
        if not profile:
            print(f"❌ Profile not found for email: {email}")
            raise HTTPException(status_code=404, detail="Profile not found")
            
        print("✅ Profile found. Cleaning profile data...")
        cleaned_profile = {
            k: v for k, v in profile.items()
            if v and str(v).strip().lower() not in ["n/a", "none", "null", "0", ""]
        }
        
        print(f"🧹 Cleaned profile keys: {list(cleaned_profile.keys())}")
        low_quality_profile = len(cleaned_profile.keys()) <= 2
        if low_quality_profile:
            print("⚠️ Low quality profile detected - not enough valid fields")

        # STRONG Prompt
        print("📝 Generating prompt for LLaMA 3.2...")
        prompt = f"""
You are an expert AI/ML career evaluator trained on current market trends and employer expectations.
 
Your role is to assess how well a **student profile (2nd or final year)** is aligned for a career in **AI, Machine Learning, or Data Science** — especially for internships and entry-level positions.
 
You must evaluate the candidate’s **readiness and potential** for AI/ML roles, not just based on what's present in the profile, but also what's missing or underdeveloped.
 
---
 
### 🎓 Score the following (float from 0.0 to 5.0):
 
- `profile_score`: Overall alignment to AI/ML career goals — relevance, presentation, completeness.
- `qualification_score`: How well academic background supports AI/ML (math, CS, stats, coursework).
- `skill_score`: Relevance of programming languages, libraries, ML tools, and project experience.
- `soft_skills_score`: Curiosity, communication, problem-solving mindset — shown via goals, projects, descriptions.
 
---
 
### 🧪 Scoring Guidelines (AI/ML Fit)
 
- 0.0–1.0 → Lacks essential relevance (e.g., no coding, vague profile)
- 1.1–3.0 → Some early signals but missing depth or direction
- 3.1–4.0 → On the right track with relevant foundation and/or minor projects
- 4.1–5.0 → Strong potential for AI/ML career — well-targeted, specific and technically relevant
 
---
 
### ✅ Look For:
 
- **Programming**: Python, NumPy, Pandas, SQL, Git
- **Math/Stats Foundations**: Any mention of linear algebra, probability, stats, calculus
- **ML Projects**: Academic/Kaggle/self-initiated projects using ML models or data pipelines
- **Tools**: scikit-learn, TensorFlow, PyTorch, Jupyter, Colab
- **Soft Skills**: Clear curiosity, learning attitude, problem-solving, data storytelling
 
---
 
### ⚠️ Penalize or reduce scores if:
 
- Profile lacks any coding, math, or project effort in relevant areas
- Generic or copy-paste goals with no connection to AI/ML
- Placeholder or fantasy content (e.g., "Mind reading", "N/A", "asdf", etc.)
- Skills mentioned are vague or outdated (e.g., "MS Paint", "Typing")
 
---
 
### 📄 Candidate Profile:
 
{json.dumps(cleaned_profile, indent=2)}
 
---
 
Now evaluate the student's **AI/ML career readiness** and return a strict JSON response:
 
{{
  "profile_score": float,
  "qualification_score": float,
  "skill_score": float,
  "soft_skills_score": float
}}
"""
 

        # 🎯 Get scores: either default or from LLM
        try:
            if low_quality_profile:
                print("⚠️ Using default scores due to low quality profile")
                scores_json = {
                    "profile_score": 0.0,
                    "qualification_score": 0.0,
                    "skill_score": 0.0,
                    "soft_skills_score": 0.0
                }
            else:
                print("🤖 Sending request to LLaMA 3.2...")
                start_time = time.time()
                response = requests.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": "llama3.2",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False
                    },
                    timeout=None  # No timeout
                )
                response_time = time.time() - start_time
                print(f"✅ Received response from LLaMA in {response_time:.2f} seconds")
                response.raise_for_status()
                
                result = response.json()
                print("📥 Raw LLaMA response:", json.dumps(result, indent=2)[:500] + "...")  # Log first 500 chars
                
                output = result.get("message", {}).get("content", "").strip()
                if not output:
                    raise ValueError("Empty response from LLaMA")
                    
                start = output.find('{')
                end = output.rfind('}') + 1
                if start == -1 or end == 0:
                    print("❌ Could not find JSON in LLaMA response")
                    print("LLaMA output:", output)
                    raise ValueError("Invalid JSON format in LLaMA response")
                    
                scores_json = json.loads(output[start:end])
                print("📊 Parsed scores:", json.dumps(scores_json, indent=2))

        except requests.exceptions.RequestException as e:
            print(f"❌ Network/Request error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error connecting to LLaMA service: {str(e)}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {str(e)}")
            print("Raw response that failed to parse:", output if 'output' in locals() else 'No output')
            raise HTTPException(status_code=500, detail=f"Error parsing LLaMA response: {str(e)}")
        except Exception as e:
            print(f"❌ Unexpected error in generate_scores: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error generating scores: {str(e)}")

        # SECOND CALL: Insights (always run)
        try:
            print("🧠 Generating insights...")
            insights_prompt = f"""
You are an intelligent AI career assistant focused on helping students prepare for careers in **Artificial Intelligence, Machine Learning, and Data Science**.
 
The following is a candidate's profile and the scores given after evaluation:
 
### Candidate Profile:
{json.dumps(cleaned_profile, indent=2)}
 
### Score Summary:
{json.dumps(scores_json, indent=2)}
 
Your task is to analyze this profile and score summary to provide **constructive, student-friendly feedback** that helps the candidate grow toward an AI/ML career. Use both the profile content and the scores to determine strengths, gaps, and overall alignment with market expectations.
 
---
 
### Return the following:
 
1. **Gap Analysis**  
   - Identify **2 clear strengths** that support potential for AI/ML.  
   - Identify **3 specific weaknesses or gaps** based on low scores or missing components in the profile (e.g., lack of ML tools, unclear goals, no math foundation).  
   - Make sure weaknesses are logically connected to the evaluation scores.
 
2. **Recommendations**  
   - Suggest **2 to 3 beginner-friendly learning resources or courses** to address those weaknesses.  
   - Prefer accessible platforms like **Coursera**, **Kaggle**, **fast.ai**, **YouTube**, or **GitHub**.  
   - Keep suggestions realistic for students in **2nd or final year**, even without prior industry experience.
 
3. **Skill Development Pathway**  
   - Recommend a **logical sequence of 4–6 technical skills** the student should focus on next.  
   - Order the list from **foundational to applied**, starting with programming basics and building toward ML tools.  
   - Focus only on **AI/ML-relevant skills** (e.g., Python, NumPy, Pandas, scikit-learn, model evaluation).
 
4. **Market Fitment Summary**  
   - Based **only on the scores and profile content provided**, assess the candidate's current alignment with **entry-level job market expectations** in AI/ML.  
   - Do **not project future growth or assume intent** — focus purely on what the candidate has already demonstrated.
   - Choose the `fit_level` using the rules below:
     - `"emerging"`: Major foundational skills missing (e.g., no programming, no math, no projects)
     - `"developing"`: Some relevant skills present, but significant gaps in applied tools, projects, or understanding
     - `"competitive"`: Well-rounded profile that meets expectations for internships or junior AI/ML roles
   - Write the `"summary"` directly to the user, using **second-person voice** (e.g., "You need to build..."). Be factual, constructive, and focused on the current state. Tie it clearly to the evaluation scores.
 
---
 
### Output Guidelines:
 
- Keep tone **supportive, realistic, and growth-oriented**.
- Do **not** include job titles, job-matching, fit percentages, or hiring recommendations.
- Be honest but encouraging for student-level users.
- Output must be in **strict, valid JSON** format with no extra text.
 
---
 
### Respond in this exact JSON structure:
 
{{
  "gap_analysis": {{
    "strengths": [str, str],
    "weaknesses": [str, str, str]
  }},
  "recommendations": [str, str, str],
  "skill_pathway": [str, str, str, str, str],
 "market_fitment": {{
    "fit_level": "developing",
    "summary": "You currently show potential in areas like X and Y, but you need to work on Z to align with entry-level expectations..."
  }}
}}
"""
 
 
            print("📝 Sending insights request to LLaMA 3.2...")
            start_time = time.time()
            response2 = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "llama3.2",
                    "messages": [{"role": "user", "content": insights_prompt}],
                    "stream": False
                },
                timeout=None  # No timeout
            )
            response2.raise_for_status()
            result2 = response2.json()
            print(f"✅ Received insights response in {time.time() - start_time:.2f} seconds")
            
            insights_output = result2.get("message", {}).get("content", "").strip()
            if not insights_output:
                raise ValueError("Empty response from LLaMA for insights")
                
            start = insights_output.find('{')
            end = insights_output.rfind('}') + 1
            if start == -1 or end == 0:
                print("❌ Could not find JSON in insights response")
                print("LLaMA output:", insights_output)
                raise ValueError("Invalid JSON format in insights response")
                
            insights_json = json.loads(insights_output[start:end])
            print("📊 Parsed insights:", json.dumps(insights_json, indent=2))

        except Exception as e:
            print(f"❌ Error in insights generation: {str(e)}")
            insights_json = {
                "gap_analysis": {
                    "strengths": [],
                    "weaknesses": []
                },
                "recommendations": [],
                "skill_pathway": []
            }

        # Combine and store in MongoDB
        final_result = {
            "scores": scores_json,
            "evaluation": insights_json
        }

        print("💾 Saving results to database...")
        collection.update_one(
            {"email": email}, 
            {"$set": final_result},
            upsert=True
        )
        print("✅ Results saved successfully")
        
        return final_result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in generate_scores: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
