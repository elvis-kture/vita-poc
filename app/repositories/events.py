from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Booking, BookingStatus, Event


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        title: str,
        date: datetime,
        total_tickets: int,
        ticket_price: float,
    ) -> Event:
        event = Event(
            title=title,
            date=date,
            total_tickets=total_tickets,
            ticket_price=ticket_price,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def get(self, event_id: int) -> Event | None:
        return await self.session.get(Event, event_id)

    async def list_with_reserved_quantities(self, now: datetime) -> list[tuple[Event, int]]:
        reserved_quantity = (
            select(func.coalesce(func.sum(Booking.quantity), 0))
            .where(
                Booking.event_id == Event.id,
                (Booking.status == BookingStatus.PAID)
                | ((Booking.status == BookingStatus.HELD) & (Booking.expires_at > now)),
            )
            .correlate(Event)
            .scalar_subquery()
        )
        statement: Select[tuple[Event, int]] = select(Event, reserved_quantity).order_by(Event.id)
        rows = await self.session.execute(statement)
        return list(rows.all())

    async def reserved_quantity_for_event(self, event_id: int, now: datetime) -> int:
        statement = select(func.coalesce(func.sum(Booking.quantity), 0)).where(
            Booking.event_id == event_id,
            (Booking.status == BookingStatus.PAID)
            | ((Booking.status == BookingStatus.HELD) & (Booking.expires_at > now)),
        )
        return int(await self.session.scalar(statement) or 0)
