import json
from datetime import timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Booking, BookingStatus, utcnow
from app.errors import NotFoundError, SoldOutError
from app.repositories.bookings import BookingRepository
from app.repositories.events import EventRepository
from app.repositories.idempotency import IdempotencyRepository


class BookingService:
    def __init__(self, session: AsyncSession, *, hold_minutes: int = 15) -> None:
        self.session = session
        self.hold_minutes = hold_minutes
        self.bookings = BookingRepository(session)
        self.events = EventRepository(session)
        self.idempotency = IdempotencyRepository(session)

    async def book_ticket(self, *, event_id: int, user_id: str, quantity: int) -> Booking:
        await self._begin_immediate()
        now = utcnow()
        await self.bookings.cancel_expired_holds(now)

        event = await self.events.get(event_id)
        if event is None:
            await self.session.rollback()
            raise NotFoundError("Event not found")

        reserved_quantity = await self.events.reserved_quantity_for_event(event_id, now)
        available_tickets = event.total_tickets - reserved_quantity
        if quantity > available_tickets:
            await self.session.rollback()
            raise SoldOutError()

        booking = await self.bookings.create_hold(
            event_id=event.id,
            user_id=user_id,
            quantity=quantity,
            expires_at=now + timedelta(minutes=self.hold_minutes),
        )
        await self.session.commit()
        return booking

    async def pay_booking(
        self,
        *,
        booking_id: int,
        idempotency_key: str,
        payment_details: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        _ = payment_details
        await self._begin_immediate()

        existing = await self.idempotency.get(idempotency_key)
        if existing is not None:
            status_code = existing.status_code
            response_body = json.loads(existing.response_body)
            await self.session.rollback()
            return status_code, response_body

        now = utcnow()
        booking = await self.bookings.get(booking_id)
        if booking is None:
            body = {"detail": "Booking not found"}
            await self.idempotency.create(
                key=idempotency_key,
                booking_id=booking_id,
                status_code=404,
                response_body=body,
            )
            await self.session.commit()
            return 404, body

        if booking.status == BookingStatus.PAID:
            body = {"detail": "Booking is already paid"}
            await self.idempotency.create(
                key=idempotency_key,
                booking_id=booking.id,
                status_code=409,
                response_body=body,
            )
            await self.session.commit()
            return 409, body

        if booking.status == BookingStatus.CANCELED:
            body = {"detail": "Booking cannot be paid"}
            await self.idempotency.create(
                key=idempotency_key,
                booking_id=booking.id,
                status_code=409,
                response_body=body,
            )
            await self.session.commit()
            return 409, body

        if booking.expires_at <= now:
            booking.status = BookingStatus.CANCELED
            booking.canceled_at = now
            body = {"detail": "Booking hold has expired"}
            await self.idempotency.create(
                key=idempotency_key,
                booking_id=booking.id,
                status_code=409,
                response_body=body,
            )
            await self.session.commit()
            return 409, body

        booking.status = BookingStatus.PAID
        booking.paid_at = now
        body = {
            "booking_id": booking.id,
            "status": BookingStatus.PAID.value,
            "quantity": booking.quantity,
        }
        await self.idempotency.create(
            key=idempotency_key,
            booking_id=booking.id,
            status_code=200,
            response_body=body,
        )
        await self.session.commit()
        return 200, body

    async def expire_holds(self) -> int:
        await self._begin_immediate()
        count = await self.bookings.cancel_expired_holds(utcnow())
        await self.session.commit()
        return count

    async def _begin_immediate(self) -> None:
        await self.session.execute(text("BEGIN IMMEDIATE"))
