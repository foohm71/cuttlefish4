#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
SQLAlchemy models for Cuttlefish4 authentication system.
"""

from datetime import datetime, date
from typing import Optional
import os
import logging
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Date, Float, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel

logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    """User model for authenticated users."""
    
    __tablename__ = "users"
    
    email = Column(String, primary_key=True)
    google_id = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    profile_picture = Column(String)
    daily_limit = Column(Integer, default=50)
    requests_used = Column(Integer, default=0)
    last_reset_date = Column(Date, default=date.today)
    unlimited_access = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to API requests
    api_requests = relationship("ApiRequest", back_populates="user", cascade="all, delete-orphan")
    
    def reset_daily_usage(self):
        """Reset daily usage counter if needed."""
        today = date.today()
        if self.last_reset_date != today:
            self.requests_used = 0
            self.last_reset_date = today
            self.updated_at = datetime.utcnow()
    
    def can_make_request(self) -> bool:
        """Check if user can make another request."""
        self.reset_daily_usage()
        return self.unlimited_access or self.requests_used < self.daily_limit
    
    def increment_usage(self):
        """Increment the user's request usage."""
        self.reset_daily_usage()
        if not self.unlimited_access:
            self.requests_used += 1
        self.updated_at = datetime.utcnow()

class ApiRequest(Base):
    """API request logging model."""
    
    __tablename__ = "api_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String, ForeignKey("users.email"), nullable=False)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    query_text = Column(Text)
    user_can_wait = Column(Boolean)
    production_incident = Column(Boolean)
    processing_time = Column(Float)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    user_agent = Column(String)
    
    # Relationship to user
    user = relationship("User", back_populates="api_requests")

# Pydantic models for API requests/responses

class UserCreate(BaseModel):
    """Model for creating a new user."""
    email: str
    google_id: str
    display_name: Optional[str] = None
    profile_picture: Optional[str] = None

class UserUpdate(BaseModel):
    """Model for updating user settings."""
    daily_limit: Optional[int] = None
    unlimited_access: Optional[bool] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

class UserResponse(BaseModel):
    """Model for user API responses."""
    email: str
    display_name: Optional[str]
    profile_picture: Optional[str]
    daily_limit: int
    requests_used: int
    unlimited_access: bool
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserUsage(BaseModel):
    """Model for user usage statistics."""
    email: str
    daily_limit: int
    requests_used: int
    requests_remaining: int
    unlimited_access: bool
    last_reset_date: date
    can_make_request: bool

class GoogleTokenPayload(BaseModel):
    """Model for Google OAuth token payload."""
    sub: str  # Google user ID
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: bool

class AuthResponse(BaseModel):
    """Model for authentication response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    usage: UserUsage

# Database connection management

class DatabaseManager:
    """Database connection and session management."""
    
    def __init__(self, database_url: str = None):
        if database_url is None:
            # Auto-detect database URL from environment
            if os.getenv("DATABASE_URL"):
                # Use provided PostgreSQL URL (for production/Supabase)
                self.database_url = os.getenv("DATABASE_URL")
                logger.info(f"Using DATABASE_URL: {self.database_url[:50]}...")
            elif os.getenv("SUPABASE_URL"):
                # Construct PostgreSQL URL from Supabase config
                supabase_url = os.getenv("SUPABASE_URL")
                # Extract project ref from URL: https://projectref.supabase.co
                project_ref = supabase_url.replace("https://", "").replace(".supabase.co", "")
                db_password = os.getenv("SUPABASE_DB_PASSWORD")
                
                logger.info(f"Supabase URL: {supabase_url}")
                logger.info(f"Project ref: {project_ref}")
                logger.info(f"Password set: {'Yes' if db_password else 'No'}")
                
                if not db_password or db_password == "your-db-password":
                    raise ValueError(
                        "SUPABASE_DB_PASSWORD environment variable is required for database connection. "
                        "Please set this in your deployment environment (Render dashboard)."
                    )
                
                self.database_url = f"postgresql://postgres:{db_password}@db.{project_ref}.supabase.co:5432/postgres"
                logger.info(f"Constructed DB URL: postgresql://postgres:***@db.{project_ref}.supabase.co:5432/postgres")
            else:
                # Fallback to SQLite for development
                database_path = os.getenv("DATABASE_PATH", "./users.db") 
                self.database_url = f"sqlite:///{database_path}"
                logger.info(f"Using SQLite: {self.database_url}")
        else:
            self.database_url = database_url
            logger.info(f"Using provided URL: {database_url[:50]}...")
            
        # Configure engine based on database type
        if "sqlite" in self.database_url:
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False}
            )
        else:
            # PostgreSQL configuration
            self.engine = create_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=300
            )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def test_connection(self):
        """Test database connection without creating tables."""
        try:
            # Just test if we can connect and run a simple query
            with self.engine.connect() as connection:
                from sqlalchemy import text
                result = connection.execute(text("SELECT 1 AS test"))
                result.fetchone()  # Consume the result
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise
    
    def get_session(self):
        """Get a database session."""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

# Global database manager instance
db_manager = DatabaseManager()

def get_db():
    """Dependency to get database session."""
    db = db_manager.SessionLocal()
    try:
        yield db
    finally:
        db.close()