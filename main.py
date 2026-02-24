from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status, Depends

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from sqlalchemy import select, Column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Annotated
import models
from database import Base, engine, get_db
from schema import PostCreate, PostResponse, PostUpdate
from schema import UserCreate, UserResponse, UserUpdate


# Base.metadata.create_all(bind=engine)  # create_all is a sync function.
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app= FastAPI(lifespan=lifespan) # The lifespan feature is just FastAPI saying: “If you need to initialize something when the app starts, do it here.”
app.mount("/static",  StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# region old code post list
# posts: list[dict] = [
#     {
#         "id": 1,
#         "user_id": 1,
#         "author": {
#             "id": 1,
#             "username": "corey_schafer",
#             "email": "corey@example.com",
#             "image_file": "default.jpg",
#             "image_path": "/static/profile_pics/default.jpg"
#         },
#         "title": "FastAPI is Awesome",
#         "content": "This framework is really easy to use and super fast.",
#         "date_posted": "2025-04-20T00:00:00",
#     },
#     {
#         "id": 2,
#         "user_id": 2,
#         "author": {
#             "id": 2,
#             "username": "jane_doe",
#             "email": "jane@example.com",
#             "image_file": "default.jpg",
#             "image_path": "/static/profile_pics/default.jpg"
#         },
#         "title": "Python is Great for Web Development",
#         "content": "Python is a great language for web development, and FastAPI makes it even better.",
#         "date_posted": "2025-04-21T00:00:00",
#     },
# ]

# endregion



@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def  home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):

    r = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = r.scalars()
    # print([i for i in posts]) #  Iterators in Python are single-pass i.e. post becomes empty after this. So this line should stay commented
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"posts": posts, "title": "All Posts"}
    )



@app.get("/posts/{post_id}", include_in_schema=False, name='get_post_page')
async def post_page(post_id: int, request: Request, db: Annotated[AsyncSession, Depends(get_db)]):

    r = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id==post_id))
    post = r.scalars().first()    #  .first() is not required becuase post_id is supposed to be unique for a specific post ?

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {post_id} not found")

    return templates.TemplateResponse( 
        request=request,
        name="post.html",
        context={"post":post, "title": post.title[:50]}
    )
 
@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts_page")
async def user_posts_page(user_id: int, request: Request, db:  Annotated[AsyncSession, Depends(get_db)]):
    
    user = await db.execute( select(models.User).where(models.User.id == user_id) )
    user = user.scalars().first()

    if user:
        r = await db.execute( select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == user_id) )
        return templates.TemplateResponse(
            request, "user_posts.html", context= { "posts": r.scalars().all(), "user": user, "title": f"{user.username.upper()}'s Posts" }          
        )
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail= "User not found")


## API Endpoints.....

@app.get("/api/posts", include_in_schema=True, response_model=list[PostResponse])
async def posts_all(db: Annotated[AsyncSession, Depends(get_db)]):
    posts = await db.execute(select(models.Post)).scalars().all()
    return posts

@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def post_get(post_id: int , db: Annotated[AsyncSession, Depends(get_db)]):

    r  = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id==post_id))
    if post:= r.scalars().first():
        return post

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {post_id} not found")


@app.post("/api/posts/new", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
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

@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def post_update_full(post_id: int , post_data: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):

    existing_post  = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id==post_id))
    existing_post = existing_post.scalars().first()
    if not existing_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {post_id} not found")

    # the client sends post_data with all the attributes,  including user_id of the post. 
    # But if the existing post's user_id does not match with the post_data's user_id ? then we have to check if the new(post_data's) user_id actually exist in db.
    # (todo: the user_id must match the old one, because only the original user should be able to update their own posts!)

    if post_data.user_id != existing_post.user_id:
        userr = await db.execute( select(models.User.id).where(models.User.id == post_data.user_id) ).scalars().all()
        if not userr:
            raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # no need to db.add() the new post. We already have the existing_post object, update that!
        existing_post.title = post_data.title
        existing_post.content = post_data.content
        existing_post.user_id = post_data.user_id

        await db.commit(); await db.refresh(existing_post, attribute_names=["author"])
        return existing_post

@app.patch( "/api/posts/{post_id}", response_model=PostResponse )
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

@app.delete("/api/posts/{post_id}", status_code = status.HTTP_204_NO_CONTENT)
async def post_delete(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    post = await db.execute( select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id) )
    post = post.scalars().first()
    if not post:
        raise HTTPException( status_code = status.HTTP_404_NOT_FOUND, detail = "The post to delete does not exist" )
    
    await db.delete(post)
    await db.commit()
    # todo: only the existing user should  be able to delete their own posts, no one else



@app.post("/api/users/new", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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

@app.patch("/api/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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


@app.get("/api/users/",  response_model=list[UserResponse],  status_code=status.HTTP_200_OK)
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

@app.get("/api/users/{userid}",  response_model=UserResponse,  status_code=status.HTTP_200_OK)
async def get_user(userid: int, db: Annotated[AsyncSession, Depends(get_db)]):
    
    dbquery = await db.execute( select(models.User).where(models.User.id == userid) )
    if user_result:=dbquery.scalars().first():
        return user_result
    else:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find a user with userid {userid}." )

@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    userr = await db.execute( select(models.User).where(models.User.id == user_id) )
    userr = userr.scalars().first()
    if not userr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"The user to delete was not found, user id:{user_id}.")

    await db.delete(userr)
    await db.commit();  



@app.get("/api/users/{userid}/posts",  response_model=list[PostResponse],  status_code=status.HTTP_200_OK)
async def get_user_posts(userid: int, db: Annotated[AsyncSession, Depends(get_db)]):
    
    r = await db.execute(select(models.User).where(models.User.id==userid))
    if  r.scalars().first(): # Does the user exist?

        # User-specific posts
        r= await db.execute( select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == userid))
        return r.scalars().all() #  A user can have an empty list of posts, no problem

    raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find a user with userid {userid}." )


@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail  if bool(exception.detail) else "An error occurred. Please check your request, try again"
    )
    if request.url.path.startswith("/api/"):
        return await http_exception_handler(request, exception) 
        # return JSONResponse(
        #     status_code=exception.status_code, 
        #     content={"detail": message},
        # )
    return templates.TemplateResponse(
        request, "error.html",
        context = {
            "status_code":exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code
    )


@app.exception_handler(RequestValidationError)  # if user types /hello instead of integer /2
async def validation_exception_handler(request: Request, exception: RequestValidationError):

    if request.url.path.startswith("/api/"):
        return await request_validation_exception_handler(request, exception) 
        # return JSONResponse(
        #         status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        #         content={"detail": exception.errors()},
        #     )
    return templates.TemplateResponse(
        request, "error.html",
        context = {
            "status_code":status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request, check your input, try again :"  + " ".join(i['type']  for i in exception.errors()),
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
    )


