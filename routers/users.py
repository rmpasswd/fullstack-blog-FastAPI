from database import get_db

from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.templating import Jinja2Templates

from typing import Annotated

from schema import UserCreate, UserResponse, UserUpdate
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/new", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(userr: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    
    existing_user = await db.execute(select(models.User).where(models.User.username == userr.username))
    if existing_user.scalars().first(): # is not None
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    
    existing_email = await db.execute(select(models.User).where(models.User.email == userr.email))
    if existing_email.scalars().first(): # is not None
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    new_user = models.User(username=userr.username, email=userr.email)
    db.add(new_user);    await db.commit();
    await db.refresh(new_user) # It's a good habit when you have server-side defaults, triggers, etc. refresh() Fetches the latest state from the database to ensure your object reflects what's actually stored.

    return new_user


@router.patch("/{user_id}", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def update_partial_user(user_id: int, user_update: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    
    existing_user = await db.execute(select(models.User).where(models.User.username == userr.username))
    existing_user = existing_user.scalars().first()
    if not  existing_user: # is not None
       raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Username does not exists, nothing to update.")

    emaill = await db.execute(select(models.User).where(models.User.email == user_update.email))
    emaill = emaill.scalars().first()
    if emaill: # already exists??
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists")

    existing_user.username = user_update.username or existing_user.username
    existing_user.email = user_update.email or existing_user.email

    await db.commit();
    await db.refresh(existing_user)
       
    return existing_user


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





