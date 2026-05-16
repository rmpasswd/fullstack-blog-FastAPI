
from database import get_db

from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from fastapi.templating import Jinja2Templates

from typing import Annotated

from schema import PostCreate, PostResponse, PostUpdate, PostResponsePaginated
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

import models
from auth.auth import CurrentUser
router = APIRouter()
templates = Jinja2Templates(directory="templates")


# These are API routes, not HTML

#  prefix="/api/posts"

# @router.get("", include_in_schema=True, response_model=list[PostResponse])
@router.get("", include_in_schema=True, response_model=PostResponsePaginated)
async def posts_all(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,

):
    
    # count the posts
    r = await db.execute(select(func.count()).select_from(models.Post))
    total = r.scalars().first() or 0
    posts = await db.execute(
                    select(models.Post)
                    .options(selectinload(models.Post.author))
                    .order_by(models.Post.date_posted.desc())
                    .offset(skip)
                    .limit(limit)
                    )
    posts = posts.scalars().all()
    # has_more = skip + limit < total # this is incorrect, because limit could be 10 but remaining post could be 5 only so (skip+limit) would not return the real value
    has_more = skip + len(posts) < total
    
    return PostResponsePaginated(
        posts = [PostResponse.model_validate(post) for post in posts],
        total = total, skip=skip, limit=limit, has_more=has_more
    )



@router.get("/{post_id}", response_model=PostResponse)
async def post_get(post_id: int , db: Annotated[AsyncSession, Depends(get_db)]):
    print("mistune here:..............")

    r  = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id==post_id))
    if post:= r.scalars().first():
        return post 

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {post_id} not found")


@router.post("/new", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def post_create(post: PostCreate,  current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):

    # From schema, we see that the request should have a title & content
    new_post_object  = models.Post(
        title= post.title,
        content= post.content,
        user_id= current_user.id,
    )

    db.add(new_post_object) # SQLAlchemy’s internal unit-of-work, "this is not a database operation", hence not 'await' 
    await db.commit()
    await db.refresh(new_post_object, attribute_names=["author"])
    # Only refreshes: id, title, content, user_id, date_posted
    # new_post_object.author is still NOT loaded
    return new_post_object


@router.put("/{post_id}", response_model=PostResponse)
async def post_update_full(post_id: int , post_data: PostCreate, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):

    existing_post  = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id==post_id))
    existing_post = existing_post.scalars().first()
    if not existing_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {post_id} not found")

    # the client sends post_data with all the attributes,  including user_id of the post. 
    # But if the existing post's user_id does not match with the post_data's user_id ? then we have to check if the new(post_data's) user_id actually exist in db.
    # (todo: the user_id must match the old one, because only the original user should be able to update their own posts!)

    if post_data.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN, detail="Not authorized to update post.")
        
    # no need to db.add() the new post. We already have the existing_post object, update that!
    existing_post.title = post_data.title
    existing_post.content = post_data.content

    await db.commit(); await db.refresh(existing_post, attribute_names=["author"])
    return existing_post

@router.patch( "/{post_id}", response_model=PostResponse )
async def post_update_partial( post_id: int, post_data: PostUpdate, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)] ):

    existing_post = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    existing_post = existing_post.scalars().first()
    if not existing_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {post_id} not found")

    if existing_post.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN, detail="Not authorized to update post.")
        

    # Update only the fields that were provided by the client
    update_data = post_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing_post, key, value)

    await db.commit()
    await db.refresh(existing_post, attribute_names=["author"])
    return existing_post

@router.delete("/{post_id}", status_code = status.HTTP_204_NO_CONTENT)
async def post_delete(post_id: int, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):

    post = await db.execute( select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id) )
    post = post.scalars().first()
    if not post:
        raise HTTPException( status_code = status.HTTP_404_NOT_FOUND, detail = "The post to delete does not exist" )
    
    if post.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN, detail="Not authorized to delete post.")
    
    await db.delete(post)
    await db.commit()
    # todo: only the existing user should be able to delete their own posts, no one else


@router.get("/{userid}/posts",  response_model=PostResponsePaginated,  status_code=status.HTTP_200_OK)
async def get_user_posts(userid: int, 
                         db: Annotated[AsyncSession, Depends(get_db)],
                         skip: Annotated[int, Query(ge=0)] = 0,
                         limit: Annotated[int, Query(ge=1, le=100)] = 10
                         ):
    # user exists?
    r = await db.execute(select(models.User).where(models.User.id==userid))
    if  not r.scalars().first(): # Does the user exist?
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find a user with userid {userid}." )


    # User-specific posts
    # count results first
    posts_count = await db.execute( select(func.count()).select_from(models.Post)
                        .where(models.Post.user_id == userid))
    total = posts_count.scalar() or 0 #  A user can have an empty list of posts, no problem

    print(f"inside /userid/posts, total counted: {total}, skip: {skip}")
    posts_partial = await db.execute( select(models.Post)
                        .options(selectinload(models.Post.author))
                        .where(models.Post.user_id == userid)
                        .order_by(models.Post.date_posted.desc())
                        .offset(skip)
                        .limit(limit)
                        ) 
    posts_partial = posts_partial.scalars().all() 
    has_more = skip + len(posts_partial) < total
    return   PostResponsePaginated(
        posts = [ PostResponse.model_validate(post) for post in posts_partial],
        total = total,  skip=skip, limit=limit,  has_more=has_more
    )


