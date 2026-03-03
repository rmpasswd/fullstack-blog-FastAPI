import jwt
from fastapi.security import OAuth2PasswordBearer
from datetime import UTC, datetime, timedelta
from auth.config import settings
from pwdlib import PasswordHash
password_hash_object  = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/token")

def hashify_password(password: str) -> str:
    return password_hash_object.hash(password)

def  verify_password(plain_password: str, hashed_password: str) -> str:
    return password_hash_object.verify( plain_password, hashed_password )


# A JWT has 3 parts: header(algorithm and type), payload(contains data and expiration) and signature(proves that it has not been tampered with). All aare base64 encoded and seperated by a period.
def create_access_token(data: dict, expires_delta: timedelta | None= None) -> str:

    """ Create a JWT access token"""
    expire = datetime.now(UTC) + ( expires_delta or timedelta(minutes=settings.access_token_expire_minutes) ) # the or operation must take precedence, hence extra paranthesis.

    to_encode = data.copy()
    to_encode.update({"exp": expire})
    
    return jwt.encode(payload= to_encode, key= settings.secret_key.get_secret_value(), algorithm=settings.algorithm)

def verify_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=[settings.algorithm], options={"require":["exp", "sub"]})

    except jwt.InvalidTokenError: # The access token provided is expired, revoked, malformed, or invalid for other reasons. https://auth0.github.io/node-oauth2-jwt-bearer/classes/InvalidTokenError.html
        return None
    else:
        return payload.get("sub") # Return the user_id which is stored in the 'sub' field as a value



