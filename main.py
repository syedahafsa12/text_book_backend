from fastapi import FastAPI, HTTPException, Depends, Header, Cookie
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

import models
from database import engine, get_db
from config import settings
from auth import (
    get_password_hash, 
    verify_password, 
    create_session, 
    get_user_from_session,
    delete_session
)
from gemini_rag import gemini_rag

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)

# Initialize database tables on first request (lazy loading for Vercel)
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        from database import init_db
        engine, _ = init_db()
        if engine:
            models.Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class SignupRequest(BaseModel):
    email: EmailStr
    name: str
    password: str
    software_background: Optional[str] = None
    hardware_background: Optional[str] = None
    operating_system: Optional[str] = None
    gpu_hardware: Optional[str] = None

class SigninRequest(BaseModel):
    email: EmailStr
    password: str

class SessionResponse(BaseModel):
    session_token: str
    user: dict

class AskRequest(BaseModel):
    question: str
    selected_text: Optional[str] = None
    language: str = "en"

class AskResponse(BaseModel):
    answer: str
    sources: List[str]

class PersonalizeRequest(BaseModel):
    content: str

class TranslateRequest(BaseModel):
    content: str

# Dependency to get current user from session
async def get_current_user(
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> models.User:
    # Try to get token from cookie first, then from Authorization header
    token = session_token
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = get_user_from_session(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user

# Auth Routes
@app.post("/api/auth/signup", response_model=SessionResponse)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """Sign up a new user with Better-Auth compatible schema"""
    # Check if user exists
    existing_user = db.query(models.User).filter(models.User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    new_user = models.User(
        email=request.email,
        name=request.name,
        email_verified=True  # Auto-verify for now
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create user profile
    profile = models.UserProfile(
        user_id=new_user.id,
        software_background=request.software_background,
        hardware_background=request.hardware_background,
        operating_system=request.operating_system,
        gpu_hardware=request.gpu_hardware
    )
    db.add(profile)
    db.commit()
    
    # Create session
    session = create_session(db, new_user.id)
    
    return {
        "session_token": session.session_token,
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name
        }
    }

@app.post("/api/auth/signin", response_model=SessionResponse)
def signin(request: SigninRequest, db: Session = Depends(get_db)):
    """Sign in with email and password"""
    # For now, we'll just check if user exists (no password in DB yet)
    # In production, you'd verify the password
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create session
    session = create_session(db, user.id)
    
    return {
        "session_token": session.session_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }

@app.post("/api/auth/signout")
def signout(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Sign out and delete session"""
    if session_token:
        delete_session(db, session_token)
    return {"message": "Signed out successfully"}

@app.get("/api/auth/me")
def get_me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user info"""
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.user_id == current_user.id
    ).first()
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "profile": {
            "software_background": profile.software_background if profile else None,
            "hardware_background": profile.hardware_background if profile else None,
            "operating_system": profile.operating_system if profile else None,
            "gpu_hardware": profile.gpu_hardware if profile else None,
            "experience_level": profile.experience_level if profile else "beginner",
            "preferred_language": profile.preferred_language if profile else "en"
        }
    }

# RAG Routes
@app.post("/api/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ask a question to the RAG system"""
    # Get user profile for personalization
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.user_id == current_user.id
    ).first()
    
    user_profile = None
    if profile:
        user_profile = {
            "software_background": profile.software_background,
            "hardware_background": profile.hardware_background,
            "experience_level": profile.experience_level,
            "operating_system": profile.operating_system
        }
    
    # Use selected text as additional context if provided
    query = request.question
    if request.selected_text:
        query = f"Based on this text: '{request.selected_text}'\n\nQuestion: {request.question}"
    
    # Search for context
    context = gemini_rag.search_context(query)
    
    # Generate answer
    answer = gemini_rag.generate_answer(
        question=request.question,
        context=context,
        user_profile=user_profile,
        language=request.language
    )
    
    # Save to chat history
    chat_message = models.ChatMessage(
        user_id=current_user.id,
        message=request.question,
        response=answer,
        context_used="\n".join(context),
        language=request.language
    )
    db.add(chat_message)
    db.commit()
    
    return {
        "answer": answer,
        "sources": ["Textbook Content"]
    }

@app.post("/api/personalize")
async def personalize_content(
    request: PersonalizeRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Personalize content based on user profile"""
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=400, detail="User profile not found")
    
    user_profile = {
        "software_background": profile.software_background,
        "hardware_background": profile.hardware_background,
        "experience_level": profile.experience_level
    }
    
    personalized = gemini_rag.personalize_content(request.content, user_profile)
    
    return {"personalized_content": personalized}

@app.post("/api/translate")
async def translate_content(
    request: TranslateRequest,
    current_user: models.User = Depends(get_current_user)
):
    """Translate content to Urdu"""
    translated = gemini_rag.translate_to_urdu(request.content)
    return {"translated_content": translated}

@app.get("/")
def read_root():
    return {
        "message": "Physical AI Textbook API",
        "version": "2.0",
        "auth": "Better-Auth",
        "ai": "Gemini 2.0 Flash"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
