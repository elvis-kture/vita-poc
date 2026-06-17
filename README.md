# Ticket Booking API

FastAPI backend for event ticket holds, payment confirmation, SQLite persistence, and hold expiration.

## Run locally

```bash
make install
make run
```

The API will be available at `http://127.0.0.1:8000`.

## Run with Docker

```bash
docker compose up --build
```

## Run tests and linting

```bash
make test
make lint
```

## API

### Create an event

```bash
curl -X POST http://127.0.0.1:8000/events \
  -H 'Content-Type: application/json' \
  -d '{"title":"Summer Festival","date":"2026-07-20T20:00:00","total_tickets":100,"ticket_price":49.99}'
```

### List events

```bash
curl http://127.0.0.1:8000/events
```

Each event includes `available_tickets`, calculated as total tickets minus the quantity of active held or paid tickets.

### Hold one ticket

```bash
curl -X POST http://127.0.0.1:8000/events/1/book \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"user-123","quantity":1}'
```

### Hold several tickets

```bash
curl -X POST http://127.0.0.1:8000/events/1/book \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"user-123","quantity":3}'
```

### Pay for a booking

```bash
curl -X POST http://127.0.0.1:8000/bookings/1/pay \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: payment-attempt-123' \
  -d '{"card_token":"tok_123"}'
```

## Architecture

The application uses a layered structure:

- `app/api`: FastAPI routes and dependency wiring.
- `app/services`: business rules for event listing, booking, payment, expiration, and idempotency.
- `app/repositories`: SQLAlchemy query objects for persistence.
- `app/db`: database models, engine/session setup, and schema creation.

This keeps the SQLite-specific details isolated. A PostgreSQL migration would mainly replace the transaction-locking strategy with row-level locks such as `SELECT ... FOR UPDATE` inside the repository/service transaction boundary.

## Concurrency

SQLite allows only one writer at a time, but read-then-write application logic can still overbook if the availability check is not protected by the write lock. The booking service starts its critical section with `BEGIN IMMEDIATE`, which obtains SQLite's reserved write lock before expired holds are canceled, availability is counted, and a new hold is inserted. Concurrent booking requests serialize at that point, so only requests that observe enough remaining capacity for their requested `quantity` can create a hold.

The test suite includes `test_concurrent_booking_requests_do_not_overbook`, which sends 100 simultaneous hold attempts for two tickets each against an event with five tickets and verifies that only two bookings succeed.

## Idempotency

`POST /bookings/{booking_id}/pay` requires an `Idempotency-Key` header. The payment service checks for an existing record under the same transaction lock. If the key was already processed, it returns the original stored status code and body. This makes client retries safe after network timeouts and prevents a repeated payment attempt from changing state twice.

## Hold expiration

The app starts an in-process background task that runs periodically and cancels expired `HELD` bookings. Booking and payment paths also handle expired holds inside their own transaction so correctness does not depend on the worker running at an exact second.
