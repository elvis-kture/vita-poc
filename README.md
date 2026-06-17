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

This keeps the SQLite-specific details isolated. A PostgreSQL migration would mainly replace the transaction-locking strategy with row-level locks such as `SELECT ... FOR UPDATE` inside the repository/service transaction boundary 
with additional DB constraint for ticket amount value greater than 0.
