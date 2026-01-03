import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Header, Depends
from app.core.config import settings

def create_access_token(username: str):
    expiry = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    return jwt.encode({"sub": username, "exp": expiry}, settings.JWT_SECRET, algorithm="HS256")

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: No token provided")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")