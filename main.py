from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status, Depends

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Annotated
import models
from database import Base, engine, get_db
from routers import users,posts



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


app.include_router(users.router, prefix="/api/users", tags=["users"]) 
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])

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
@app.get("/posts", include_in_schema=True, name="posts")
async def  home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):

    r = await db.execute(select(models.Post)
                         .order_by(models.Post.date_posted.desc())
                         .options(selectinload(models.Post.author)))
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


## API Endpoints are in routers directory


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


