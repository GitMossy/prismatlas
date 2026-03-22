"""
Authentication Middleware

Validates Supabase JWT tokens and extracts user information.
Shared JWT secret with the Prism platform — both apps use the same Supabase project.
"""

from typing import Optional
from fastapi import HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.config import settings

security = HTTPBearer()


def verify_token(token: str) -> dict:
    """
    Verify a Supabase JWT token and return its claims.

    Supabase uses HS256 (symmetric) signing with the JWT secret.
    """
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: JWT secret not configured",
        )

    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
        return claims

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token audience",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token verification failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """FastAPI dependency — returns the Supabase user ID (sub claim)."""
    token = credentials.credentials
    claims = verify_token(token)

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """FastAPI dependency — returns user ID or None if no/invalid token."""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]
    try:
        claims = verify_token(token)
        return claims.get("sub")
    except HTTPException:
        return None


class UserContext:
    """Structured access to user claims from the JWT token."""

    def __init__(self, claims: dict):
        self.claims = claims
        self.user_id = claims.get("sub")
        self.email = claims.get("email")
        self.role = claims.get("role", "authenticated")
        self.app_metadata = claims.get("app_metadata", {})
        self.user_metadata = claims.get("user_metadata", {})

    @property
    def is_admin(self) -> bool:
        return self.role == "service_role" or self.app_metadata.get("admin", False)


async def get_user_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserContext:
    """FastAPI dependency — returns full UserContext with all claims."""
    token = credentials.credentials
    claims = verify_token(token)

    if not claims.get("sub"):
        raise HTTPException(
            status_code=401,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserContext(claims)
