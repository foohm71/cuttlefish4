#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Authentication routes for Cuttlefish4 FastAPI application.
Handles user registration, login, and management.
"""

import logging
from datetime import datetime, date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

try:
    from ..database.models import (
        User, ApiRequest, UserCreate, UserUpdate, UserResponse, 
        UserUsage, GoogleTokenPayload, AuthResponse, get_db
    )
    from .middleware import (
        verify_google_token, create_access_token, get_current_user, 
        get_admin_user, create_jwt_payload
    )
except ImportError:
    from database.models import (
        User, ApiRequest, UserCreate, UserUpdate, UserResponse, 
        UserUsage, GoogleTokenPayload, AuthResponse, get_db
    )
    from middleware import (
        verify_google_token, create_access_token, get_current_user, 
        get_admin_user, create_jwt_payload
    )

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])

class GoogleAuthRequest(BaseModel):
    token: str

@router.post("/google", response_model=AuthResponse)
async def google_auth(
    request: GoogleAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user with Google OAuth token.
    Creates new user if first time, returns JWT for API access.
    
    Args:
        google_token: Google OAuth ID token
        db: Database session
    
    Returns:
        JWT token and user information
    """
    try:
        # Verify Google token
        google_payload = await verify_google_token(request.token)
        
        # Check if user exists
        user = db.query(User).filter(User.email == google_payload.email).first()
        
        if not user:
            # Create new user
            user = User(
                email=google_payload.email,
                google_id=google_payload.sub,
                display_name=google_payload.name,
                profile_picture=google_payload.picture
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"✅ New user created: {user.email}")
        else:
            # Update existing user info
            user.google_id = google_payload.sub
            user.display_name = google_payload.name
            user.profile_picture = google_payload.picture
            user.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"✅ User updated: {user.email}")
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        # Create JWT token
        access_token = create_access_token(user.email)
        
        # Get usage info
        user.reset_daily_usage()
        usage = UserUsage(
            email=user.email,
            daily_limit=user.daily_limit,
            requests_used=user.requests_used,
            requests_remaining=user.daily_limit - user.requests_used if not user.unlimited_access else 999999,
            unlimited_access=user.unlimited_access,
            last_reset_date=user.last_reset_date,
            can_make_request=user.can_make_request()
        )
        
        return AuthResponse(
            access_token=access_token,
            user=UserResponse.from_orm(user),
            usage=usage
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Google auth failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information.
    
    Returns:
        Current user details
    """
    return UserResponse.from_orm(current_user)

@router.get("/usage", response_model=UserUsage)
async def get_user_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's usage statistics.
    
    Returns:
        User usage information
    """
    current_user.reset_daily_usage()
    db.commit()
    
    return UserUsage(
        email=current_user.email,
        daily_limit=current_user.daily_limit,
        requests_used=current_user.requests_used,
        requests_remaining=current_user.daily_limit - current_user.requests_used if not current_user.unlimited_access else 999999,
        unlimited_access=current_user.unlimited_access,
        last_reset_date=current_user.last_reset_date,
        can_make_request=current_user.can_make_request()
    )

# Admin routes

@router.get("/admin/users", response_model=List[UserResponse])
async def list_users(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only).
    
    Returns:
        List of all users
    """
    users = db.query(User).all()
    return [UserResponse.from_orm(user) for user in users]

@router.put("/admin/users/{user_email}", response_model=UserResponse)
async def update_user(
    user_email: str,
    user_update: UserUpdate,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update user settings (admin only).
    
    Args:
        user_email: Email of user to update
        user_update: Updated user settings
    
    Returns:
        Updated user information
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_update.daily_limit is not None:
        user.daily_limit = user_update.daily_limit
    if user_update.unlimited_access is not None:
        user.unlimited_access = user_update.unlimited_access
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    if user_update.is_admin is not None:
        user.is_admin = user_update.is_admin
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    logger.info(f"✅ User updated by admin: {user.email}")
    return UserResponse.from_orm(user)

@router.get("/admin/usage-stats")
async def get_usage_stats(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get system-wide usage statistics (admin only).
    
    Returns:
        Usage statistics across all users
    """
    today = date.today()
    
    # Get daily stats
    daily_requests = db.query(func.count(ApiRequest.id)).filter(
        func.date(ApiRequest.timestamp) == today
    ).scalar()
    
    # Get user stats
    total_users = db.query(func.count(User.email)).scalar()
    active_users = db.query(func.count(User.email)).filter(User.is_active == True).scalar()
    unlimited_users = db.query(func.count(User.email)).filter(User.unlimited_access == True).scalar()
    
    # Get top users by usage today
    top_users = db.query(
        User.email,
        User.requests_used,
        User.daily_limit
    ).filter(
        User.last_reset_date == today,
        User.requests_used > 0
    ).order_by(User.requests_used.desc()).limit(10).all()
    
    return {
        "date": today.isoformat(),
        "daily_requests": daily_requests,
        "total_users": total_users,
        "active_users": active_users,
        "unlimited_users": unlimited_users,
        "top_users": [
            {
                "email": email,
                "requests_used": requests_used,
                "daily_limit": daily_limit
            }
            for email, requests_used, daily_limit in top_users
        ]
    }

@router.post("/admin/reset-usage/{user_email}")
async def reset_user_usage(
    user_email: str,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Reset user's daily usage counter (admin only).
    
    Args:
        user_email: Email of user to reset
    
    Returns:
        Success message
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.requests_used = 0
    user.last_reset_date = date.today()
    user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"✅ Usage reset by admin: {user.email}")
    return {"message": f"Usage reset for {user.email}"}

# Helper function to validate request body for Google auth
class GoogleAuthRequest:
    """Request model for Google authentication."""
    
    def __init__(self, token: str):
        self.token = token