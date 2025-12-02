from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import models
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_session_token(user_id: int) -> str:
    """Create a session token for Better-Auth compatibility"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(user_id), "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.better_auth_secret, algorithm=ALGORITHM)
    return encoded_jwt

def verify_session_token(token: str) -> Optional[int]:
    """Verify session token and return user_id"""
    try:
        payload = jwt.decode(token, settings.better_auth_secret, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except JWTError:
        return None

def create_session(db: Session, user_id: int) -> models.Session:
    """Create a new session in the database"""
    session_token = create_session_token(user_id)
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    db_session = models.Session(
        session_token=session_token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_user_from_session(db: Session, session_token: str) -> Optional[models.User]:
    """Get user from session token"""
    user_id = verify_session_token(session_token)
    if not user_id:
        return None
    
    # Check if session exists and is not expired
    session = db.query(models.Session).filter(
        models.Session.session_token == session_token,
        models.Session.expires_at > datetime.utcnow()
    ).first()
    
    if not session:
        return None
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return user

def delete_session(db: Session, session_token: str):
    """Delete a session (logout)"""
    db.query(models.Session).filter(
        models.Session.session_token == session_token
    ).delete()
    db.commit()
