from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Booking, BookingStatus


class BookingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_hold(
        self,
        *,
        event_id: int,
        user_id: str,
        quantity: int,
        expires_at: datetime,
    ) -> Booking:
        booking = Booking(
            event_id=event_id,
            user_id=user_id,
            quantity=quantity,
            expires_at=expires_at,
        )
        self.session.add(booking)
        await self.session.flush()
        return booking

    async def get(self, booking_id: int) -> Booking | None:
        return await self.session.get(Booking, booking_id)

    async def cancel_expired_holds(self, now: datetime) -> int:
        statement = (
            update(Booking)
            .where(Booking.status == BookingStatus.HELD, Booking.expires_at <= now)
            .values(status=BookingStatus.CANCELED, canceled_at=now)
        )
        result = await self.session.execute(statement)
        return int(result.rowcount or 0)

    async def expired_held_bookings(self, now: datetime) -> list[Booking]:
        rows = await self.session.execute(
            select(Booking).where(Booking.status == BookingStatus.HELD, Booking.expires_at <= now)
        )
        return list(rows.scalars().all())
