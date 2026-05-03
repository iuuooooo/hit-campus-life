from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class LoginIn(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str
    name: str
    role: str = "student"
    college: str = ""
    grade: str = ""
    interests: str = ""
    location_preference: str = ""
    schedule_preference: str = ""


class UserOut(BaseModel):
    id: int
    username: str
    name: str
    role: str
    college: str = ""
    grade: str = ""
    avatar: str = "H"
    bio: str = ""
    interests: str = ""
    location_preference: str = ""
    schedule_preference: str = ""
    credit_score: int = 90

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    college: Optional[str] = None
    grade: Optional[str] = None
    bio: Optional[str] = None
    interests: Optional[str] = None
    location_preference: Optional[str] = None
    schedule_preference: Optional[str] = None


class PostCreate(BaseModel):
    user_id: int
    channel: str = "life"
    title: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1)
    tags: str = ""
    image_url: str = ""


class CommentCreate(BaseModel):
    user_id: int
    content: str = Field(min_length=1)


class ActivityCreate(BaseModel):
    creator_id: int
    club_id: Optional[int] = None
    title: str
    description: str = ""
    place: str = ""
    start_time: str = ""
    capacity: int = 30
    tags: str = ""


class JoinIn(BaseModel):
    user_id: int


class MarketItemCreate(BaseModel):
    seller_id: int
    title: str = Field(min_length=1, max_length=180)
    description: str = ""
    price: int = 0
    place: str = ""
    tags: str = ""


class ScheduleItemCreate(BaseModel):
    user_id: int
    weekday: str
    start_time: str = ""
    end_time: str = ""
    title: str = Field(min_length=1, max_length=180)
    place: str = ""
    note: str = ""


class DailyRecordCreate(BaseModel):
    user_id: int
    title: str = Field(min_length=1, max_length=180)
    content: str = ""
    mood: str = ""
    tags: str = ""


class ClubApplyIn(BaseModel):
    user_id: int
    message: str = ""


class ApplicationReviewIn(BaseModel):
    reviewer_id: int
    status: str


class BuddyTaskCreate(BaseModel):
    creator_id: int
    goal: str
    title: str
    description: str = ""
    place: str = ""
    time_slot: str = ""
    tags: str = ""
    max_members: int = 4


class MatchQuery(BaseModel):
    user_id: int
    goal: str = ""
    description: str = ""
    place: str = ""
    time_slot: str = ""
    tags: str = ""
    use_llm: bool = True
