from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.repositories.events import EventRepository
from app.schemas import EventCreate, EventRead


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self.events = EventRepository(session)
        self.session = session

    async def create_event(self, payload: EventCreate) -> EventRead:
        event = await self.events.create(**payload.model_dump())
        await self.session.commit()
        return EventRead(
            id=event.id,
            title=event.title,
            date=event.date,
            total_tickets=event.total_tickets,
            ticket_price=float(event.ticket_price),
            available_tickets=event.total_tickets,
        )

    async def list_events(self) -> list[EventRead]:
        now = utcnow()
        rows = await self.events.list_with_reserved_quantities(now)
        return [
            EventRead(
                id=event.id,
                title=event.title,
                date=event.date,
                total_tickets=event.total_tickets,
                ticket_price=float(event.ticket_price),
                available_tickets=max(event.total_tickets - reserved_count, 0),
            )
            for event, reserved_count in rows
        ]
