#!/usr/bin/env python3
"""
Authentication middleware for Cuttlefish4 FastAPI application.
Handles JWT validation, Google OAuth verification, and rate limiting.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy.orm import Session

try:
    from ..database.models import User, ApiRequest, GoogleTokenPayload, get_db
except ImportError:
    from database.models import User, ApiRequest, GoogleTokenPayload, get_db

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

# Security scheme
security = HTTPBearer()

class AuthError(HTTPException):
    """Custom authentication error."""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class RateLimitError(HTTPException):
    """Custom rate limit error."""
    
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail
        )

def create_access_token(user_email: str) -> str:
    """
    Create JWT access token for user.
    
    Args:
        user_email: User's email address
    
    Returns:
        JWT token string
    """
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode = {
        "sub": user_email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> str:
    """
    Verify JWT token and extract user email.
    
    Args:
        token: JWT token string
    
    Returns:
        User email if valid
    
    Raises:
        AuthError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_email: str = payload.get("sub")
        
        if user_email is None:
            raise AuthError("Invalid token payload")
        
        return user_email
        
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise AuthError("Invalid or expired token")

async def verify_google_token(token: str) -> GoogleTokenPayload:
    """
    Verify Google OAuth token and extract user info.
    
    Args:
        token: Google OAuth token
    
    Returns:
        Google token payload with user info
    
    Raises:
        AuthError: If token is invalid
    """
    try:
        if not GOOGLE_CLIENT_ID:
            raise AuthError("Google OAuth not configured")
        
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            token, requests.Request(), GOOGLE_CLIENT_ID
        )
        
        # Validate required fields
        if not idinfo.get('email_verified', False):
            raise AuthError("Email not verified by Google")
        
        return GoogleTokenPayload(
            sub=idinfo['sub'],
            email=idinfo['email'],
            name=idinfo.get('name'),
            picture=idinfo.get('picture'),
            email_verified=idinfo.get('email_verified', False)
        )
        
    except ValueError as e:
        logger.warning(f"Google token validation failed: {e}")
        raise AuthError("Invalid Google token")

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: Bearer token from request
        db: Database session
    
    Returns:
        User object if authenticated
    
    Raises:
        AuthError: If authentication fails
    """
    # Verify JWT token
    user_email = verify_jwt_token(credentials.credentials)
    
    # Get user from database
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise AuthError("User not found")
    
    if not user.is_active:
        raise AuthError("User account is disabled")
    
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user with rate limit check.
    
    Args:
        current_user: User from get_current_user dependency
    
    Returns:
        User object if authorized and within rate limits
    
    Raises:
        RateLimitError: If user has exceeded daily limit
    """
    # Check if user can make a request
    if not current_user.can_make_request():
        remaining_hours = 24 - datetime.now().hour
        raise RateLimitError(
            f"Daily limit of {current_user.daily_limit} requests exceeded. "
            f"Limit resets in {remaining_hours} hours."
        )
    
    return current_user

def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify admin privileges.
    
    Args:
        current_user: User from get_current_user dependency
    
    Returns:
        User object if user is admin
    
    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user

async def log_api_request(
    request: Request,
    user: User,
    endpoint: str,
    success: bool = True,
    error_message: Optional[str] = None,
    processing_time: Optional[float] = None,
    query_text: Optional[str] = None,
    user_can_wait: Optional[bool] = None,
    production_incident: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Log API request for analytics and auditing.
    
    Args:
        request: FastAPI request object
        user: User making the request
        endpoint: API endpoint called
        success: Whether request was successful
        error_message: Error message if failed
        processing_time: Request processing time in seconds
        query_text: User query text
        user_can_wait: User preference flag
        production_incident: Incident flag
        db: Database session
    """
    try:
        # Increment user usage
        user.increment_usage()
        
        # Create request log
        api_request = ApiRequest(
            user_email=user.email,
            endpoint=endpoint,
            method=request.method,
            query_text=query_text,
            user_can_wait=user_can_wait,
            production_incident=production_incident,
            processing_time=processing_time,
            success=success,
            error_message=error_message,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        db.add(api_request)
        db.commit()
        
        logger.info(f"API request logged: {user.email} -> {endpoint}")
        
    except Exception as e:
        logger.error(f"Failed to log API request: {e}")
        # Don't fail the main request if logging fails
        db.rollback()

def create_jwt_payload(user: User) -> Dict[str, Any]:
    """
    Create JWT payload with user information.
    
    Args:
        user: User object
    
    Returns:
        JWT payload dictionary
    """
    return {
        "sub": user.email,
        "email": user.email,
        "name": user.display_name,
        "admin": user.is_admin,
        "unlimited": user.unlimited_access,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }