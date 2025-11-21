from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Dict
import os
from dotenv import load_dotenv
from models.users import User   # <-- Updated for your project

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "mysecret")
ALGORITHM = "HS256"

class JWTBearer(HTTPBearer):
    def __init__(self, check_token_limit: bool = False, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.check_token_limit = check_token_limit

    async def __call__(self, request: Request) -> Dict:
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)

        if not credentials:
            raise HTTPException(status_code=403, detail="Invalid authorization token.")

        if credentials.scheme != "Bearer":
            raise HTTPException(status_code=403, detail="Invalid authentication scheme.")

        token = credentials.credentials
        return await self.verify_jwt(token)

    async def verify_jwt(self, token: str) -> Dict:
        try:
            # Decode JWT
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_email = payload.get("sub")

            if not user_email:
                raise HTTPException(status_code=401, detail="Invalid token payload.")

            # Fetch user from Beanie
            user = await User.find_one(User.email == user_email)

            if not user:
                raise HTTPException(status_code=404, detail="User not found.")

            # Check tokens if enabled
            if self.check_token_limit and getattr(user, "tokens_left", None) is not None:
                if user.tokens_left <= 0:
                    raise HTTPException(status_code=403, detail="Token exhausted")

            return {
                "user_id": str(user.id),
                "user_type": user.user_type,
                "user": user
            }

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired.")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token.")
