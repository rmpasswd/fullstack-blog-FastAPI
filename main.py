
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status, Depends

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Annotated
import models
from database import engine, get_db
from routers import users,posts
from auth.config import settings

import  mistune
from markupsafe import Markup
# Base.metadata.create_all(bind=engine)  # create_all is a sync function.
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all,) 
    # create_all  is problematic as it will not re-create the table (and also interfere with alembic migration) if in future we change the table's design(eg. another column)
    yield
    # Shutdown
    await engine.dispose()

    

app= FastAPI(lifespan=lifespan) # The lifespan feature is just FastAPI saying: “If you need to initialize something when the app starts, do it here.”
app.mount("/static",  StaticFiles(directory="static"), name="static")
app.mount("/media",  StaticFiles(directory="media"), name="media")


app.include_router(users.router, prefix="/api/users", tags=["users"]) 
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])

templates = Jinja2Templates(directory="templates")

markdown_parser = mistune.create_markdown(escape=False)
templates.env.filters["markdown_mistune"] = markdown_parser


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=True, name="posts")
async def  home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):

    r = await db.execute(select(models.Post)
                         .order_by(models.Post.date_posted.desc())
                         .options(selectinload(models.Post.author))
                         .limit(settings.posts_per_page))
    posts = r.scalars().all()
    # print([i for i in posts]) #  Iterators in Python are single-pass i.e. post becomes empty after this. So this line doesn't work
    
    # count total posts
    r = await db.execute(select(func.count()).select_from(models.Post))
    total = r.scalar() or 0
    has_more =len(posts) < total

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"posts": posts, "has_more": has_more, "limit":settings.posts_per_page, "title": "All Posts"}
    )



@app.get("/posts/{post_id}", include_in_schema=False, name='get_post_page')
async def post_page(post_id: int, request: Request, db: Annotated[AsyncSession, Depends(get_db)]):

    r = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id==post_id))
    post = r.scalars().first()    #  .first() is not required becuase post_id is supposed to be unique for a specific post ?

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {post_id} not found")

    post.content = Markup(mistune.html(post.content)) # to convince {{jinja}} to parse HTML tags.

    return templates.TemplateResponse( 
        request=request,
        name="post.html",
        context={"post":post, "title": post.title[:50]}
    )
 
@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts_page")
async def user_posts_page(user_id: int, request: Request, db:  Annotated[AsyncSession, Depends(get_db)]):
    
    user = await db.execute( select(models.User).where(models.User.id == user_id) )
    user = user.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail= "User not found")

    posts = await db.execute( select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == user_id).limit(settings.posts_per_page) )
    posts = posts.scalars().all()
    
    # count total posts
    r = await db.execute(select(func.count()).select_from(models.Post).where(models.Post.user_id==user_id))
    total = r.scalar() or 0
    has_more =len(posts) < total

    return templates.TemplateResponse(
    request, "user_posts.html", context= { "posts": posts, "has_more": has_more, "user": user, "limit": settings.posts_per_page, "title": f"{user.username.upper()}'s Posts" }          
    )


@app.get("/login", include_in_schema=False)
async def login_page(req: Request):
    return templates.TemplateResponse(
        request=req, name= "login.html", context={"title": "Login"}
    )

@app.get("/register", include_in_schema=False)
async def register_page(req: Request):
    return templates.TemplateResponse(
        request=req, name="register.html", context={"title": "Register"}
    )

@app.get('/account', include_in_schema=False)
async def account_page(req: Request):
    return templates.TemplateResponse(
        request=req, name="account.html", context={"title": "Account"}
    )


@app.get('/health')
async def health_check(db:Annotated[AsyncSession, Depends(get_db)]):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            # detail="Database no responding..."
            detail= f"Database not responding: { type (e).__name__} : {e} " ,
        ) from e
    try:
        # Temporary debug lines
        current_db = await db.scalar(text("SELECT current_database();"))
        print(f"DEBUG: SQLAlchemy is actually connected to: {current_db}")
    except Exception as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            # detail="Database no responding..."
            detail= f"And:\n { type (e).__name__} : {e} " ,
        ) from e    
    return {"status": "healthy", "connected_Database": current_db}

@app.middleware("http")
async def add_security_headers(request: Request, call_next):

    response = await call_next(request)
    # letting the req. pass on and before returning it to the client, add these:

    
    response.headers["X-Frame-Option"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Option"] = "nosniff"

    if "Referrer-Policy" not in response.headers:
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    if request.url.hostname not in ("localhost", "127.0.0.1"):
        response.headers["Strict-Transport-Security"] = ("max-age=63072000, includeSubDomains")

    return response
## API Endpoints are in routers directory moved to dir. /routers 


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


