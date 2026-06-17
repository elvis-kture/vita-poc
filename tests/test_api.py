import asyncio
from datetime import timedelta

from httpx import AsyncClient

from app.db.base import utcnow


def event_payload(total_tickets: int = 10) -> dict:
    return {
        "title": "Summer Festival",
        "date": (utcnow() + timedelta(days=30)).isoformat(),
        "total_tickets": total_tickets,
        "ticket_price": 42.5,
    }


async def create_event(client: AsyncClient, total_tickets: int = 10) -> int:
    response = await client.post("/events", json=event_payload(total_tickets))
    assert response.status_code == 201
    return int(response.json()["id"])


async def test_create_and_list_events_include_available_tickets(client: AsyncClient) -> None:
    event_id = await create_event(client, total_tickets=3)

    booking_response = await client.post(
        f"/events/{event_id}/book",
        json={"user_id": "user-1", "quantity": 2},
    )
    assert booking_response.status_code == 200
    assert booking_response.json()["quantity"] == 2

    response = await client.get("/events")

    assert response.status_code == 200
    assert response.json()[0]["available_tickets"] == 1


async def test_booking_sold_out_returns_conflict(client: AsyncClient) -> None:
    event_id = await create_event(client, total_tickets=3)

    first = await client.post(
        f"/events/{event_id}/book",
        json={"user_id": "user-1", "quantity": 2},
    )
    second = await client.post(
        f"/events/{event_id}/book",
        json={"user_id": "user-2", "quantity": 2},
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "No tickets available"


async def test_payment_is_idempotent_for_retried_key(client: AsyncClient) -> None:
    event_id = await create_event(client, total_tickets=1)
    booking = await client.post(f"/events/{event_id}/book", json={"user_id": "user-1"})
    booking_id = booking.json()["booking_id"]
    headers = {"Idempotency-Key": "payment-attempt-1"}

    first = await client.post(
        f"/bookings/{booking_id}/pay",
        json={"card_token": "tok_123"},
        headers=headers,
    )
    retry = await client.post(
        f"/bookings/{booking_id}/pay",
        json={"card_token": "tok_123"},
        headers=headers,
    )

    assert first.status_code == 200
    assert retry.status_code == 200
    assert retry.json() == first.json()


async def test_book_then_pay_existing_booking_id(client: AsyncClient) -> None:
    event_id = await create_event(client, total_tickets=5)
    booking = await client.post(
        f"/events/{event_id}/book",
        json={"user_id": "user-1", "quantity": 3},
    )
    booking_id = booking.json()["booking_id"]

    response = await client.post(
        f"/bookings/{booking_id}/pay",
        json={"card_token": "tok_123"},
        headers={"Idempotency-Key": "payment-existing-booking"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "booking_id": booking_id,
        "status": "PAID",
        "quantity": 3,
    }


async def test_payment_requires_idempotency_key(client: AsyncClient) -> None:
    event_id = await create_event(client, total_tickets=1)
    booking = await client.post(f"/events/{event_id}/book", json={"user_id": "user-1"})

    response = await client.post(
        f"/bookings/{booking.json()['booking_id']}/pay",
        json={"card_token": "tok_123"},
    )

    assert response.status_code == 422


async def test_concurrent_booking_requests_do_not_overbook(client: AsyncClient) -> None:
    event_id = await create_event(client, total_tickets=5)

    async def book(index: int):
        return await client.post(
            f"/events/{event_id}/book",
            json={"user_id": f"user-{index}", "quantity": 2},
        )

    responses = await asyncio.gather(*(book(index) for index in range(100)))
    successes = [response for response in responses if response.status_code == 200]
    conflicts = [response for response in responses if response.status_code == 409]

    assert len(successes) == 2
    assert len(conflicts) == 98

    events = await client.get("/events")
    assert events.json()[0]["available_tickets"] == 1
