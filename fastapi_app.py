import os
from fastapi import FastAPI, HTTPException, Depends, status, Request,File, Form, UploadFile

from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pymongo import MongoClient
from dotenv import load_dotenv
import base64
import uuid
import bcrypt
import jwt
import datetime
from typing import Optional, Union, List
from pydantic import BaseModel, EmailStr
from bson import ObjectId
from pymongo import ReturnDocument
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi_mail.errors import ConnectionErrors
from routers.profile import router as profile_router
from routers.ai_review import router as ai_review_router
from routers.Mcq_question import get_mcq_router
from routers.admin import router as admin
from routers.article import router as article_router
from routers.jdinterview import router as jdinterview_router
from routers.report import router as report_router
from routers.article_card import router as article_card_router
from routers import introductory_training
from routers.certificate import router as certificate_router

# Load .env variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Interview Platform API", version="1.0.0")
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(mongo_uri)
db = client[os.getenv("MONGO_DB_NAME", "data")]
collection = db["submitted_articles"]
article_card_collection = db["article_cards"]
 
# MongoDB connection
@app.on_event("startup")
async def startup_db_client():
    try:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        db_name = os.getenv("MONGO_DB_NAME", "interview_db")
        app.state.mongo_client = MongoClient(mongo_uri)
        app.state.db = app.state.mongo_client[db_name]
        print("✅ Connected to MongoDB")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_db_client():
    app.state.mongo_client.close()

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Default Next.js dev server
        "http://localhost:3001",
        "http://127.0.0.1:3000", "http://192.168.0.229:3000","http://192.168.0.220:3000",
        "http://192.168.0.207:3000"  # Add other origins as needed
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Set-Cookie", "Authorization"],
)

# Include routers
app.include_router(profile_router, prefix='/api', tags=['profile'])
app.include_router(ai_review_router, prefix='/api', tags=['ai-review'])
app.include_router(get_mcq_router())
app.include_router(admin, prefix='/api/admin', tags=['admin'])
app.include_router(article_router, prefix="/api/article", tags=["article"])
app.include_router(article_card_router, prefix="/api", tags=["article_cards"])
app.include_router(jdinterview_router, prefix="/api/jd", tags=["jd"])
app.include_router(report_router)  # Add this line to include the report router
app.include_router(introductory_training.router, prefix="/api/user", tags=["training-progress"])
app.include_router(certificate_router, prefix="/api/user", tags=["certificate"])


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {request.headers}")
    
    if request.method in ["POST", "PUT"]:
        try:
            body = await request.body()
            print(f"Request body: {body.decode()}")
        except Exception as e:
            print(f"Error reading request body: {e}")
    
    response = await call_next(request)
    return response

# JWT config
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
JWT_ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Email configuration
mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME")),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=os.getenv("MAIL_USE_TLS", "True").lower() == "true",
    MAIL_SSL_TLS=os.getenv("MAIL_USE_SSL", "False").lower() == "true",
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False,  # Disable certificate validation for development
    MAIL_DEBUG=0,  # 0 = no debug output, 1 = normal debug output, 2 = more verbose
    SUPPRESS_SEND=0  # Set to 1 to prevent actual email sending
)

# Initialize FastMail
fastmail = FastMail(mail_config)

# Pydantic models
class UserBase(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    password: str
    userType: str
    phone: Optional[str] = None

class UserCreate(UserBase):
    pass

class EnterpriseCreate(UserBase):
    companyName: str
    contactPerson: str
    industry: str
    companySize: str
    address: str
    website: Optional[str] = None
    jobTitle: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ResetPassword(BaseModel):
    email: EmailStr

class NewPassword(BaseModel):
    token: str
    newPassword: str

# Helper functions
def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = app.state.db.users.find_one({"email": email})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

# Routes
@app.post("/api/create_account")
async def create_account(user: UserCreate):
    return await _create_user_account(user)

@app.post("/api/create_enterprise")
async def create_enterprise(enterprise: EnterpriseCreate):
    return await _create_user_account(enterprise)

async def _create_user_account(user_data: Union[UserCreate, EnterpriseCreate]):
    print(f"Creating {'enterprise ' if isinstance(user_data, EnterpriseCreate) else ''}account for email: {user_data.email}")

    # Check if user already exists in the 'users' collection
    if app.state.db.users.find_one({"email": user_data.email}):
        print(f"Account already exists for email: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already exists"
        )

    try:
        # Hash the password
        hashed_password = bcrypt.hashpw(user_data.password.encode("utf-8"), bcrypt.gensalt())
        
        # Common user data for the 'users' collection
        common_user_data = {
            "firstName": user_data.firstName,
            "lastName": user_data.lastName,
            "email": user_data.email,
            "password": hashed_password,
            "userType": user_data.userType,
            "phone": user_data.phone,
            "created_at": datetime.datetime.utcnow()
        }
        
        # Insert common user data and get the new user's ID
        user_result = app.state.db.users.insert_one(common_user_data)
        user_id = user_result.inserted_id
        
        # If it's an enterprise user, store enterprise-specific data
        if isinstance(user_data, EnterpriseCreate):
            enterprise_data = {
                "user_id": user_id,  # Link to the users collection
                "companyName": user_data.companyName,
                "contactPerson": user_data.contactPerson,
                "jobTitle": user_data.jobTitle,
                "industry": user_data.industry,
                "companySize": user_data.companySize,
                "address": user_data.address,
                "website": user_data.website,
                "created_at": datetime.datetime.utcnow()
            }
            app.state.db.enterprise.insert_one(enterprise_data)
            print(f"Enterprise details for {user_data.companyName} stored successfully.")
        
        # Create a basic profile for the user
        profile_data = {
            "user_id": user_id,
            "email": user_data.email,
            "first_name": user_data.firstName,
            "last_name": user_data.lastName,
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow()
        }
        app.state.db.profiles.insert_one(profile_data)
        print(f"Basic profile created for user: {user_data.email}")

        print(f"Account created successfully for: {user_data.email}")
        
        # Send welcome email
        try:
            await send_welcome_email(user_data.email, user_data.firstName, user_data.userType)
        except Exception as email_error:
            print(f"Error sending welcome email: {str(email_error)}")
        
        return {
            "message": "Account created successfully",
            "user_id": str(user_id)
        }
        
    except Exception as e:
        print(f"Error creating account: {str(e)}")
        # Optional: Add cleanup logic here to remove the user if enterprise creation fails
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the account"
        )

async def send_welcome_email(email: str, name: str, user_type: str):
    """Send a welcome email to the new user"""
    subject = f"Welcome to Our Platform - {user_type.capitalize()} Account"
    body = f"""
    <h2>Welcome to Our Platform, {name}!</h2>
    <p>Thank you for registering as a {user_type} user.</p>
    <p>Your account has been created successfully.</p>
    <p>If you have any questions, feel free to contact our support team.</p>
    <p>Best regards,<br>The Team</p>
    """
    
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype="html"
    )
    
    await fastmail.send_message(message)

@app.post("/api/login")
async def login(user_data: UserLogin, userType: str = None):
    # Check if user exists
    user = app.state.db.users.find_one({"email": user_data.email})
    
    if not user:
        raise HTTPException(status_code=401, detail="Email not registered.")
    
    # Get the password field
    password_field = user["password"]
    
    # If password is stored as Binary, convert it to bytes
    if isinstance(password_field, bytes):
        stored_password = password_field
    else:
        stored_password = password_field.encode("utf-8")
    
    # Verify password
    if not bcrypt.checkpw(user_data.password.encode("utf-8"), stored_password):
        raise HTTPException(status_code=401, detail="Incorrect password.")
    
    # If userType is provided and doesn't match, return error
    if userType and user["userType"] != userType:
        raise HTTPException(status_code=401, detail="Invalid user type.")
    
    # Create JWT token with user type from database
    access_token = create_access_token(
        data={
            "email": user["email"],
            "userType": user["userType"],
            "id": str(user["_id"])
        },
        expires_delta=datetime.timedelta(hours=24)  # 24-hour token expiration
    )
    
    # Return token and user type for redirection
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "userType": user["userType"],
        "email": user["email"],
        "user": {
            "email": user["email"],
            "firstName": user.get("firstName", ""),
            "lastName": user.get("lastName", ""),
            "userType": user["userType"]
        }
    }

@app.post("/api/forgot-password")
async def forgot_password(reset_data: ResetPassword):
    try:
        print(f"🔍 Looking up user with email: {reset_data.email}")
        user = app.state.db.users.find_one({"email": reset_data.email})

        if not user:
            print(f"ℹ️  Email not found in database: {reset_data.email}")
            return {"message": "If an account with that email exists, a password reset link has been sent"}

        token_data = {
            "email": user["email"],
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
        }
        token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        if isinstance(token, bytes):
            token = token.decode("utf-8")
            
        reset_link = f"http://localhost:3000/auth/reset-password?token={token}"
        
        # HTML email content with button
        email_content = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #111827; font-size: 24px; margin-bottom: 20px;">Password Reset Request</h2>
            <p style="margin: 10px 0;">We received a request to reset your password. If you didn't make this request, you can safely ignore this email.</p>
            
            <p style="margin: 20px 0 10px 0;">To reset your password, click the button below:</p>
            <div style="text-align: center; margin: 25px 0;">
                <a href="{reset_link}" style="display: inline-block; padding: 12px 24px; background-color: #4f46e5; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 500;">Reset Password</a>
            </div>
            
            <p style="color: #6b7280; font-size: 14px; margin: 20px 0 5px 0;">Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #4b5563; background-color: #f9fafb; padding: 10px; border-radius: 4px; font-size: 14px; margin: 5px 0 20px 0;">{reset_link}</p>
            
            <p style="color: #6b7280; font-size: 14px; margin: 20px 0;">This link will expire in 15 minutes.</p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">
                <p style="margin: 0;">Thanks,<br>The Support Team</p>
            </div>
        </div>
        """
        
        message = MessageSchema(
            subject="Password Reset Request",
            recipients=[user["email"]],
            body=email_content,
            subtype="html"
        )
        
        try:
            await fastmail.send_message(message)
            print(f"✅ Password reset email sent to {user['email']}")
            return {"message": "If an account with that email exists, a password reset link has been sent"}
        except ConnectionErrors as e:
            print(f"❌ Failed to send email: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to send reset email")
            
    except Exception as e:
        print(f"❌ Error in forgot_password: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your request")

@app.post("/api/reset-password")
async def reset_password(data: NewPassword):
    try:
        token_data = jwt.decode(data.token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = app.state.db.users.find_one({"email": token_data["email"]})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        hashed_password = bcrypt.hashpw(data.newPassword.encode("utf-8"), bcrypt.gensalt())
        app.state.db.users.update_one(
            {"email": token_data["email"]},
            {"$set": {"password": hashed_password}}
        )
        
        return {"message": "Password reset successful"}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid token")
    except Exception as e:
        print(f"❌ Error in reset_password: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid or expired token")
def serialize_article(article):
    return {
        "_id": str(article.get("_id")),
        "article_id": article.get("article_id"),
        "title": article.get("title"),
        "status": article.get("status"),
        "content": article.get("content"),
    }

@app.get("/article/list")
async def list_articles():
    print(f"Using collection: {collection.name}")
    print(f"Total documents in collection: {collection.count_documents({})}")
    # articles_cursor = collection.find()
    articles_cursor = article_card_collection.find()
    articles = [serialize_article(article) for article in articles_cursor]
    print(f"Fetched from DB: {articles}")
    return {"articles": articles}


@app.get("/article/{article_id}")
async def get_article(article_id: str):
    print(f"Fetching article with article_id: {article_id}")

    # Only fetch by article_id (not by _id)
    article = collection.find_one({"article_id": article_id})

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return serialize_article(article)



@app.post("/api/article/article_card")
async def create_article(
    title: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...)
):
    contents = await image.read()
    article = {
        "article_id": str(uuid.uuid4())[:8],
        "category": category,
        "title": title,
        "description": description,
        "image": contents,  # Binary image data (saved to Mongo)
        "filename": image.filename,
        "content_type": image.content_type,
    }
 
    result = article_card_collection.insert_one(article)
 
    return {
        "message": "Article created",
        "article_id": article["article_id"],
        "filename": image.filename,
        "content_type": image.content_type,
    }




@app.get("/get-all-articles/")
def get_all_articles():
    articles = list(article_card_collection.find({}, {"_id": 0}))

    for article in articles:
        if "image" in article and isinstance(article["image"], bytes):
            content_type = article.get("content_type", "image/jpeg")
            raw_base64 = base64.b64encode(article["image"]).decode("utf-8")
            article["image_raw"] = raw_base64
            article["image"] = f"data:{content_type};base64,{raw_base64}"

    return JSONResponse(content={"articles": articles})




# Protected route example
@app.get("/api/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
