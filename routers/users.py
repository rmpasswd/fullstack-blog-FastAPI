from database import get_db
from datetime import timedelta

from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from typing import Annotated

from schema import UserCreate, UserResponse, UserResponsePrivate, UserUpdate, Token
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
from auth.auth import (
    create_access_token,
    hashify_password,
    oauth2_scheme,
    verify_access_token,
    verify_password,
)
from auth.config import settings
import models

router = APIRouter()

# prefix="/api/users"

@router.post("/new", response_model=UserResponsePrivate, status_code=status.HTTP_201_CREATED)
async def create_user(userr: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    
    existing_user = await db.execute(select(models.User).where(func.lower(models.User.username) == userr.username.lower()))
    
    if existing_user.scalars().first(): # is not None
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    
    existing_email = await db.execute(select(models.User).where(func.lower(models.User.email) == userr.email.lower()))
    
    if existing_email.scalars().first(): # is not None
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    new_user = models.User(username=userr.username, email=userr.email.lower(), password_hash=hashify_password(userr.password))  # in pydantic User schema it is 'password_hash' and in db model its 'password'
   
    db.add(new_user);    await db.commit();
    await db.refresh(new_user) # It's a good habit when you have server-side defaults, triggers, etc. refresh() Fetches the latest state from the database to ensure your object reflects what's actually stored.

    return new_user

# Receives login information, verifying and returns a session token
@router.post("/token", response_model=Token) 
async def create_token_from_loginfo(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db:Annotated[AsyncSession,  Depends(get_db)]):

    result = await db.execute( select(models.User).where(func.lower(models.User.email)== form_data.username.lower() ))
    existing_user = result.scalars().first()
    
    if (not existing_user) or (not verify_password(form_data.password, existing_user.password_hash)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail = "Username or password invalid", headers={"WWW_Authenticate": "Bearer"})
    
    # Login & Create access token
    access_token = create_access_token(data={"sub": str(existing_user.id)}) # expires_delta has default value of = timedelta(minutes=settings.access_token_expire_minutes)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponsePrivate)
async def get_current_loggedin_user(token: Annotated[str,  Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_db)]):

    # first decode the jwt token, get the userID
    userID= verify_access_token(token=token)
    if userID is None: # means InvalidTokenError error was raised, check the definition
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid/Expired token", headers={"WWW-Authenticate": "Bearer"})
    
    try:
        userID_int =  int(userID)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid/Expired token", headers={"WWW-Authenticate": "Bearer"})
    
    # search in db for the user ID
    userr = await db.execute(select(models.User).where(func.lower(models.User.id == userID_int)))
    userr = userr.scalars().first()

    if not userr:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found!", headers={"WWW-Authenticate": "Bearer"})

    return userr
        
    


@router.patch("/{user_id}", response_model=UserResponsePrivate)
async def update_partial_user(user_id: int, user_update: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):

    try:    # Assumption: the user_id already exists and wants to change to a new  username "user_update.username".

        existing_user = await db.execute(select(models.User).where(func.lower(models.User.username) == user_update.username.lower()))
        existing_user = existing_user.scalars().first()
        if not  existing_user: # is not None
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="A user with this username already exists")

        existing_emaill = await db.execute(select(models.User).where(func.lower(models.User.email) == user_update.email.lower()))
        emaill = emaill.scalars().first()
        if emaill: # already exists??
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists")

        existing_user.username = user_update.username or existing_user.username
        existing_user.email = user_update.email or existing_user.email

        await db.commit();
        await db.refresh(existing_user)

        return existing_user
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)



@router.get("/",  response_model=list[UserResponse],  status_code=status.HTTP_200_OK)
async def get_users_all(db: Annotated[AsyncSession, Depends(get_db)]):
    r = await db.execute( select(models.User))
    r = r.scalars().all()
    if r:
        return r
    else:
        return []

        # region Trying to send 404 here, 'raise'  would  stop  execution
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content = {"detail": "No user found", "data":[]}
        )
        #endregion

@router.get("/{userid}",  response_model=UserResponse,  status_code=status.HTTP_200_OK)
async def get_user(userid: int, db: Annotated[AsyncSession, Depends(get_db)]):
  
    dbquery = await db.execute( select(models.User).where(models.User.id == userid) )
    if user_result:=dbquery.scalars().first():
        return user_result
    else:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find a user with userid {userid}." )

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    userr = await db.execute( select(models.User).where(models.User.id == user_id) )
    userr = userr.scalars().first()
    if not userr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"The user to delete was not found, user id:{user_id}.")

    await db.delete(userr)
    await db.commit();  



