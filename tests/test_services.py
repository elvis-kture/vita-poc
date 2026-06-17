from datetime import timedelta

from sqlalchemy import select

from app.db.base import Booking, BookingStatus, utcnow
from app.services.bookings import BookingService


async def test_expire_holds_cancels_due_bookings(client) -> None:
    app = client._transport.app
    async with app.state.session_factory() as session:
        service = BookingService(session, hold_minutes=15)
        event_response = await client.post(
            "/events",
            json={
                "title": "Late Night Show",
                "date": (utcnow() + timedelta(days=1)).isoformat(),
                "total_tickets": 1,
                "ticket_price": 25,
            },
        )
        booking_id = (
            await client.post(
                f"/events/{event_response.json()['id']}/book",
                json={"user_id": "user-1"},
            )
        ).json()["booking_id"]

        booking = await session.get(Booking, booking_id)
        booking.expires_at = utcnow() - timedelta(minutes=1)
        await session.commit()

        expired_count = await service.expire_holds()
        refreshed = (
            await session.execute(select(Booking).where(Booking.id == booking_id))
        ).scalar_one()

    assert expired_count == 1
    assert refreshed.status == BookingStatus.CANCELED
