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
    CurrentUser
)

from auth.config import settings
import models


# Image imports...
from fastapi import UploadFile
from PIL import UnidentifiedImageError
from starlette.concurrency import run_in_threadpool
from image_utils import delete_profilepic, process_profile_pic
# from auth.config import settings


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
# async def get_current_loggedin_user(token: Annotated[str,  Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_db)]):
async def get_current_loggedin_user(current_user: CurrentUser):
    return current_user



@router.patch("/{user_id}", response_model=UserResponsePrivate)
async def update_partial_user(user_id: int,  current_user: CurrentUser, user_update: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):

    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized to update user",)
    
    # Check if the user exists, unnecessary...
    userr = await db.execute( select(models.User).where(models.User.id == user_id) )
    userr = userr.scalars().first()
    if not userr:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User does not exist?!",)

    # if the user provided a new username and its not a spinoff from existing username!
    if bool(user_update.username) and user_update.username.lower() != userr.username.lower():  # The db will not query for case changes, e.g. dorimon to dorimoN
        existing_username = await db.execute(select(models.User).where(func.lower(models.User.username) == user_update.username.lower()))
        existing_username = existing_username.scalars().first()
        print(existing_username)
        if existing_username is not None: # is not None
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="A user with this username already exists")

    # if the user provided a new email and its not a spinoff from existing email!
    if bool(user_update.email) and user_update.email.lower() != userr.email.lower():
        existing_emaill = await db.execute(select(models.User).where(func.lower(models.User.email) == user_update.email.lower()))
        existing_emaill = existing_emaill.scalars().first()
        if existing_emaill: # already exists??
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists")

    print("trynna update user_partial")

    current_user.username = user_update.username or current_user.username
    current_user.email = user_update.email or current_user.email

    await db.commit();
    await db.refresh(current_user)

    return current_user




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
async def delete_user(user_id: int, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    
    userr = await db.execute( select(models.User).where(models.User.id == user_id) )
    userr = userr.scalars().first()
    if not userr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"The user to delete was not found, user id:{user_id}.")

    image_file = userr.image_file
    await db.delete(userr)
    await db.commit()

    if image_file:
        delete_profilepic(image_file)



@router.patch("/{user_id}/picture", response_model=UserResponsePrivate)
async def upload_profile_picture(
    user_id: int, 
    file: UploadFile, # this object type is provided by FastAPI
    current_user:CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    content = await file.read()

    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    
    # we should not run CPU-heavy task in async manner, it will block the threadpool.
    # we could choose to run it the usual sync manner but we want the endpoint to by async
    # solution:  Use thread-pool
    try:
        new_filename = await run_in_threadpool(process_profile_pic,content)
    except UnidentifiedImageError as err: # pillow package detects the content type uploaded by user
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Image file, upload a valid one...") from err
        # "from err" preserves the original traceback, Python’s traceback will show: "The above exception (UnidentifiedImageError) was the direct cause of the following exception (HTTPException)."
    
    #saving the old file, incase DB update dont work
    old_filename = current_user.image_file

    current_user.image_file = new_filename
    await db.commit() 
    #gemini notes:
    # If you had updated a User, deleted a Post, and created a Comment all in the same route, a single await db.commit() would save all three actions. It doesn't take arguments because its job is to finalize the entire "transaction."
    # Note: If you wanted to tell the session about a brand new object that isn't in the 'shopping cart' yet, you would use db.add(new_object). But since current_user was already fetched from the DB, it's already being tracked.
    # 
    await db.refresh(current_user) # fetch the latest from the DB, making sure its showing the new DB value.

    if old_filename:
        delete_profilepic(old_filename)
    
    return current_user

@router.delete("/{user_id}/picture", response_model=UserResponsePrivate)
async def delete_user_picture(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user's picture",
        )

    old_filename = current_user.image_file

    if old_filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete",
        )

    current_user.image_file = None
    await db.commit()
    await db.refresh(current_user)

    delete_profilepic(old_filename)

    return current_user