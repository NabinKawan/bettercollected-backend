import logging

from backend.app.exceptions import HTTPException
from backend.config import settings

from common.models.user import User

import jwt

from starlette.requests import Request


def get_logged_user(request: Request) -> User:
    token = get_user_token(request)
    try:
        jwt_response = jwt.decode(
            token,
            key=settings.auth_settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        user = User(**jwt_response)
        return user
    # TODO : Handle specific exceptions
    except Exception as e:
        logging.error(e)
        raise HTTPException(401, "No user logged in.")


def get_user_if_logged_in(request: Request) -> User | None:
    try:
        return get_logged_user(request=request)
    except HTTPException:
        return None


def get_user_token(request: Request) -> str:
    access_token = request.cookies.get("Authorization")
    if not access_token:
        raise HTTPException(401, "Authorization token is missing.")
    return access_token


def get_logged_admin(request: Request):
    user = get_logged_user(request)
    if user.is_admin():
        return user
    else:
        raise HTTPException(403, "You are not authorized to perform this action.")
