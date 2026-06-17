from datetime import datetime

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    date: datetime
    total_tickets: int = Field(gt=0)
    ticket_price: float = Field(ge=0)


class EventRead(BaseModel):
    id: int
    title: str
    date: datetime
    total_tickets: int
    ticket_price: float
    available_tickets: int


class BookTicketRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)
    quantity: int = Field(default=1, gt=0)


class BookTicketResponse(BaseModel):
    booking_id: int
    quantity: int


class PaymentRequest(BaseModel):
    card_token: str = Field(min_length=1, max_length=255)


class PaymentResponse(BaseModel):
    booking_id: int
    status: str
    quantity: int
