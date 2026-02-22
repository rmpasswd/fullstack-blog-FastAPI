from datetime import datetime

from  pydantic import BaseModel, ConfigDict, Field, EmailStr


# newer sql-alchemy schema
class UserBase(BaseModel):
    username:str  =  Field(min_length=1, max_length=45)
    email: EmailStr = Field(max_length=120)

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    username: str | None = Field(default=None, min_length=1, max_length=45)
    email: EmailStr | None =  Field(default=None,max_length=120)
    image_file: str | None =  Field(default=None,min_length=1, max_length=222)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True) # 'True' allows the use of . notation for dictionary objects
    id: int
    image_file: str | None
    image_path: str



# existing pydantic schema
class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=10_000_000)
    # author: str = Field(min_length=1, max_length=1000) # comes from database(sqlalchemdy model)


class PostCreate(PostBase):   
    user_id: int 
    # temporary, in future we will get current userid from browser session.

class PostUpdate(PostBase): # for http patch request
    title: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None= Field(min_length=1, max_length=10_000_000)


class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True) # 'True' allows the use of . notation for dictionary objects
    
    id: int
    user_id: int
    date_posted: datetime  #  going to  get serialized  ISO 8601 format
    author: UserResponse

    


