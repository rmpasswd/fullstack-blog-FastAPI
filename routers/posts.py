
from database import get_db

from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.templating import Jinja2Templates

from typing import Annotated

from schema import PostCreate, PostResponse, PostUpdate
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")



@router.get("", include_in_schema=True, response_model=list[PostResponse])
async def posts_all(db: Annotated[AsyncSession, Depends(get_db)]):
    posts = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    return posts.scalars().all()

@router.get("/{post_id}", response_model=PostResponse)
async def post_get(post_id: int , db: Annotated[AsyncSession, Depends(get_db)]):

    r  = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id==post_id))
    if post:= r.scalars().first():
        return post

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {post_id} not found")


@router.post("/new", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def post_create(post: PostCreate,  db: Annotated[AsyncSession, Depends(get_db)]):

    # From schema, we see that the request should have a title, content and user_id

    # First get the User ID
    r = await db.execute(select(models.User.id).where(models.User.id== post.user_id))
    user_id = r.scalars().first()

    if not user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    new_post_object  = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )

    db.add(new_post_object) # SQLAlchemy’s internal unit-of-work, "this is not a database operation", hence not 'await'
    await db.commit()
    await db.refresh(new_post_object, attribute_names=["author"])
    # Only refreshes: id, title, content, user_id, date_posted
    # new_post_object.author is still NOT loaded
    return new_post_object

@router.put("/{post_id}", response_model=PostResponse)
async def post_update_full(post_id: int , post_data: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):

    existing_post  = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id==post_id))
    existing_post = existing_post.scalars().first()
    if not existing_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {post_id} not found")

    # the client sends post_data with all the attributes,  including user_id of the post. 
    # But if the existing post's user_id does not match with the post_data's user_id ? then we have to check if the new(post_data's) user_id actually exist in db.
    # (todo: the user_id must match the old one, because only the original user should be able to update their own posts!)

    if post_data.user_id != existing_post.user_id:
        userr = await db.execute( select(models.User.id).where(models.User.id == post_data.user_id) )
        if not userr.scalars().all():
            raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # no need to db.add() the new post. We already have the existing_post object, update that!
        existing_post.title = post_data.title
        existing_post.content = post_data.content
        existing_post.user_id = post_data.user_id

        await db.commit(); await db.refresh(existing_post, attribute_names=["author"])
        return existing_post

@router.patch( "/{post_id}", response_model=PostResponse )
async def post_update_partial( post_id: int, post_data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)] ):

    existing_post = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    existing_post = existing_post.scalars().first()
    if not existing_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {post_id} not found")

    # Update only the fields that were provided by the client
    update_data = post_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing_post, key, value)

    await db.commit()
    await db.refresh(existing_post, attribute_names=["author"])
    return existing_post

@router.delete("/{post_id}", status_code = status.HTTP_204_NO_CONTENT)
async def post_delete(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    post = await db.execute( select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id) )
    post = post.scalars().first()
    if not post:
        raise HTTPException( status_code = status.HTTP_404_NOT_FOUND, detail = "The post to delete does not exist" )
    
    await db.delete(post)
    await db.commit()
    # todo: only the existing user should  be able to delete their own posts, no one else


@router.get("/{userid}/posts",  response_model=list[PostResponse],  status_code=status.HTTP_200_OK)
async def get_user_posts(userid: int, db: Annotated[AsyncSession, Depends(get_db)]):
    
    r = await db.execute(select(models.User).where(models.User.id==userid))
    if  r.scalars().first(): # Does the user exist?

        # User-specific posts
        r= await db.execute( select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == userid))
        return r.scalars().all() #  A user can have an empty list of posts, no problem

    raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find a user with userid {userid}." )

