from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ItemCreate(BaseModel):
    name: str
    description: str
    total_count: int
    available_count: int
    status: str


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    total_count: Optional[int] = None
    available_count: Optional[int] = None
    status: Optional[str] = None


class ReservationCreate(BaseModel):
    rental_id: int
    reserved_count: int


class ItemResponse(BaseModel):
    id: int
    name: str
    description: str
    total_count: int
    available_count: int
    status: str
    created_at: datetime
