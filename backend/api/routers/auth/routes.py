from fastapi import APIRouter, Depends, HTTPException, Request, status, Response, WebSocket
from datetime import timedelta
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from . import crud, utils
from .models import User, UserCreate, UserOut, UserListOut
from typing import List
from .database import get_db
import logging
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)
router = APIRouter()

# ------------------ SIGNUP ------------------ #
@router.post("/signup", response_model=UserOut)
async def signup(request: Request, response: Response, data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Validate email & password
    if not utils.is_email_valid(data.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if not utils.is_password_strong(data.password):
        raise HTTPException(
            status_code=400,
            detail="Password must be 8+ chars, include uppercase, lowercase, number, and special char"
        )

    email_normalized = data.email.strip().lower()
    existing = await crud.get_user_by_email(db, email_normalized)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    data.email = email_normalized
    user = await crud.create_user(db, data)

    access_token_expires = timedelta(minutes=request.app.state.access_token_expire_minutes)
    refresh_token_expires = timedelta(minutes=request.app.state.refresh_token_expire_minutes)


    access_token = utils.create_access_token(
        data={"sub": user.email, "user_id": str(user.id), "role":user.role},
        expires_delta=access_token_expires
    )
    refresh_token = utils.create_access_token(
        data={"sub": user.email, "type": "refresh", "role":user.role},
        expires_delta=refresh_token_expires
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # True in production
        samesite="Lax",  # or "None" if frontend & backend are on different domains
        max_age=int(access_token_expires.total_seconds()),
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="Lax",
        max_age=int(refresh_token_expires.total_seconds()),
        path="/",
    )

    return UserOut(id=str(user.id), email=user.email, full_name=user.full_name, role=user.role)


# ------------------ LOGIN ------------------ #
@router.post("/login", response_model=dict)
async def login(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user_email = form_data.username.strip().lower()

    user = await crud.get_user_by_email(db, user_email)
    if not user or not utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=request.app.state.access_token_expire_minutes)
    refresh_token_expires = timedelta(minutes=request.app.state.refresh_token_expire_minutes)

    access_token = utils.create_access_token(
        data={"sub": user.email, "user_id": str(user.id), "role": user.role},
        expires_delta=access_token_expires
    )
    refresh_token = utils.create_access_token(
        data={"sub": user.email, "type": "refresh", "role": user.role},
        expires_delta=refresh_token_expires
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # True in production
        samesite="Lax",  # or "None" if frontend & backend are on different domains
        max_age=int(access_token_expires.total_seconds()),
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="Lax",
        max_age=int(refresh_token_expires.total_seconds()),
        path="/",
    )

    return {"message": "Login successful", "user_id":str(user.id), "role":user.role}


# ------------------ LOGOUT ------------------ #
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}


# ------------------ GET CURRENT USER ------------------ #
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """Extract token from cookies instead of Authorization header"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        try :
            payload = jwt.decode(
                token,
                request.app.state.secret_key,
                algorithms=[request.app.state.algorithm],
            )
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid token")
        email: str = payload.get("sub")
        
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await crud.get_user_by_email(db, email)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    except JWTError as e:
        logger.error(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

class WebSocketAuthException(Exception):
    def __init__(self, code: int, reason: str):
        self.code = code
        self.reason = reason

#----------------------------Auth for websocket connections----------------------------#
async def get_current_user_ws(websocket: WebSocket, db: AsyncSession):
    token = websocket.cookies.get("access_token")
    
    if not token:
        raise WebSocketAuthException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Not authenticated"
        )

    try:
        payload = jwt.decode(
            token,
            websocket.app.state.secret_key,
            algorithms=[websocket.app.state.algorithm],
        )
        
        email: str = payload.get("sub")
        
        if email is None:
            raise WebSocketAuthException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid token"
            )

        user = await crud.get_user_by_email(db, email)
        
        if not user:
            raise WebSocketAuthException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="User not found"
            )

        return user

    except JWTError as e:
        logger.error(f"JWT Error: {e}")
        raise WebSocketAuthException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid token"
        )


# ------------------ REFRESH TOKEN ------------------ #
@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token found")

    try:
        payload = jwt.decode(
            refresh_token,
            request.app.state.secret_key,
            algorithms=[request.app.state.algorithm],
        )

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token type")

        email = payload.get("sub")
        user = await crud.get_user_by_email(db, email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_access_token = utils.create_access_token(
            data={"sub": user.email, "user_id": str(user.id), "role": user.role},
            expires_delta=timedelta(minutes=request.app.state.access_token_expire_minutes),
        )

        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=int(timedelta(minutes=request.app.state.access_token_expire_minutes).total_seconds()),
            path="/",
        )

        return {"message": "Token refreshed successfully"}

    except JWTError as e:
        logger.error(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# ------------------ ME ------------------ #
@router.get("/me", response_model=UserOut)
async def get_me(request: Request, current_user = Depends(get_current_user)):
    return UserOut(id=str(current_user.id), 
                   email=current_user.email, 
                   full_name=current_user.full_name,
                   role=current_user.role)


# ------------------ GET ALL USERS ------------------ #
@router.get(
    "/users",
    response_model=List[UserListOut],
    tags=["auth"],
    summary="Get all users",
    description="Retrieve a list of all active users from the PostgreSQL database. Requires authentication."
)
async def get_all_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all active users from PostgreSQL database.
    Only accessible to authenticated users.
    """
    try:
        users = await crud.get_all_users(db)
        return [
            UserListOut(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active
            )
            for user in users
        ]
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")


# ------------------ GET USER BY ID ------------------ #
@router.get(
    "/users/{user_id}",
    response_model=UserListOut,
    tags=["auth"],
    summary="Get user by ID",
    description="Retrieve user details by user ID from the PostgreSQL database. Requires authentication."
)
async def get_user_by_id(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user details by ID from PostgreSQL database.
    Only accessible to authenticated users.
    """
    try:
        user = await crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserListOut(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user")
