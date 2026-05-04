from __future__ import annotations # forward reference support for python versions older than 3.14
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from  auth.config  import settings
class  User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash :  Mapped[str]  = mapped_column(String(200), nullable=False)

    image_file: Mapped[str|None] = mapped_column(String(200), nullable=True, default=None)
    posts: Mapped[list[Post]] = relationship(back_populates="author", cascade="all, delete-orphan")

    @property
    def image_path(self) -> str:
        if self.image_file: # "image_file" part of the  string is stored in the database,  but need to build the full path as  in file explorer or aws s3
            # return f"/media/profile_pics/{self.image_file}"
            return f"https://{settings.s3_bucket_name}.s3.{settings.s3_region}.amazonaws.com/profile_pics/{self.image_file}"
            # example: https://blog-fastapi-2026.s3.us-east-2.amazonaws.com/profile_pics/c880b79513384fa4bccd5ca852300f5e.jpg
        return f"/static/profile_pics/default.jpg"


class Post(Base):
    __tablename__ = 'posts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date_posted: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC)+timedelta(hours=6))
    author: Mapped[User] = relationship(back_populates="posts")

    likes: Mapped[int] = mapped_column(Integer, default=0, server_default="0") 
            # server_defaults exists because database usually  tries to put null value to a new column of existing table.


