#!/usr/bin/env python3
"""
FastAPI application module for Cuttlefish authentication system.
"""

# Import auth test app instead of main app
from .main_auth_test import app

__all__ = ['app']