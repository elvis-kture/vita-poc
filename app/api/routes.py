from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    build_booking_service,
    build_event_service,
    get_hold_minutes,
    get_session,
)
from app.schemas import (
    BookTicketRequest,
    BookTicketResponse,
    EventCreate,
    EventRead,
    PaymentRequest,
)
from app.services.bookings import BookingService
from app.services.events import EventService

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_session)]
HoldMinutesDep = Annotated[int, Depends(get_hold_minutes)]


async def event_service(session: SessionDep) -> EventService:
    return build_event_service(session)


async def booking_service(
    request: Request,
    session: SessionDep,
    hold_minutes: HoldMinutesDep,
) -> BookingService:
    _ = request
    return build_booking_service(session, hold_minutes)


@router.post("/events", status_code=201, response_model=EventRead)
async def create_event(
    payload: EventCreate,
    service: Annotated[EventService, Depends(event_service)],
) -> EventRead:
    return await service.create_event(payload)


@router.get("/events", response_model=list[EventRead])
async def list_events(service: Annotated[EventService, Depends(event_service)]) -> list[EventRead]:
    return await service.list_events()


@router.post("/events/{event_id}/book", response_model=BookTicketResponse)
async def book_ticket(
    event_id: int,
    payload: BookTicketRequest,
    service: Annotated[BookingService, Depends(booking_service)],
) -> BookTicketResponse:
    booking = await service.book_ticket(
        event_id=event_id,
        user_id=payload.user_id,
        quantity=payload.quantity,
    )
    return BookTicketResponse(booking_id=booking.id, quantity=booking.quantity)


@router.post("/bookings/{booking_id}/pay")
async def pay_booking(
    booking_id: int,
    payload: PaymentRequest,
    response: Response,
    idempotency_key: Annotated[str, Header(min_length=1, alias="Idempotency-Key")],
    service: Annotated[BookingService, Depends(booking_service)],
) -> dict:
    status_code, body = await service.pay_booking(
        booking_id=booking_id,
        idempotency_key=idempotency_key,
        payment_details=payload.model_dump(),
    )
    response.status_code = status_code
    return body
