from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bookings import BookingService
from app.services.events import EventService


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_hold_minutes(request: Request) -> int:
    return request.app.state.settings.hold_minutes


def build_event_service(session: AsyncSession) -> EventService:
    return EventService(session)


def build_booking_service(session: AsyncSession, hold_minutes: int) -> BookingService:
    return BookingService(session, hold_minutes=hold_minutes)
