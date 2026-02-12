from fastapi import FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from schema import PostCreate, PostResponse


app= FastAPI()

app.mount("/static",  StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
posts: list[dict] = [
    {
        "id": 1,
        "author": "Corey Schafer",
        "title": "FastAPI is Awesome",
        "content": "This framework is really easy to use and super fast.",
        "date_posted": "April 20, 2025",
    },
    {
        "id": 2,
        "author": "Jane Doe",
        "title": "Python is Great for Web Development",
        "content": "Python is a great language for web development, and FastAPI makes it even better.",
        "date_posted": "April 21, 2025",
    },
]

@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", name="posts")
def  home(request: Request):
    # return({"message": "hello world"})
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"posts": posts, "title": "Home"}
    )

@app.get("/posts/{post_id}")
def get_post_page(post_id: int, request: Request):
    for post in posts:
        if post.get("id") == post_id:
            print(request,dict.keys(post))
            return templates.TemplateResponse( 
                request=request,
                name="post.html",
                context={"post":post, "title": post["title"][:50]}
            )
    # return {"error": f"post with id {post_id} not found"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {post_id} not found")
 


## API Endpoints.....

@app.get("/api/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int):
    for post in posts:
        if post.get("id") == post_id:
            return post
    # return {"error": f"post with id {post_id} not found"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {post_id} not found")

@app.get("/api/posts/", include_in_schema=False, response_model=list[PostResponse])
def get_posts():
    return posts


@app.post("/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate):
    new_id = max(p["id"] for p in posts) + 1 if posts else 1
    print("trying to create a new post with id:",new_id)
    newpost = {
        "id": new_id,
        "author": post.author,
        "title": post.title,
        "content": post.content,
        "date_posted": "April 20, 2025",
    }
    posts.append(newpost)
    return newpost






@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail  if bool(exception.detail) else "An error occurred. Please check your request, try again"
    )
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message},
        )
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
def validation_exception_handler(request: Request, exception: RequestValidationError):
    # message = (
    #     exception.errors()[0]['msg']  if bool(exception.errors()) else "An error occurred. Please check your request, try again"
    # )
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )
    return templates.TemplateResponse(
        request, "error.html",
        context = {
            "status_code":status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request, check your input, try again :"  + " ".join(i['type']  for i in exception.errors()),
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
    )

