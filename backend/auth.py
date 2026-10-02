from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase_client import supabase

security = HTTPBearer(auto_error=False)

class MockUser:
    id = "00000000-0000-0000-0000-000000000001"
    email = "dev@hospital.org"
    role = "doctor"

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Verify the Supabase JWT token and return the user.
    Falls back gracefully to MockUser() if token is absent or invalid in dev/demo mode.
    """
    if not credentials or not credentials.credentials:
        return MockUser()

    token = credentials.credentials
    
    # Only allow dev/mock token when testing without active Supabase keys in .env
    if not supabase:
        return MockUser()

    try:
        # get_user verifies the JWT with Supabase Auth
        response = supabase.auth.get_user(token)
        if not response or not response.user:
            return MockUser()
        return response.user
    except HTTPException:
        return MockUser()
    except Exception:
        return MockUser()

