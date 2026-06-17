import asyncio
import contextlib

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.bookings import BookingService


async def expiration_worker(
    session_factory: async_sessionmaker,
    *,
    hold_minutes: int,
    interval_seconds: int,
) -> None:
    while True:
        try:
            async with session_factory() as session:
                service = BookingService(session, hold_minutes=hold_minutes)
                await service.expire_holds()
        except asyncio.CancelledError:
            raise
        except Exception:
            # A real deployment would wire structured logging here.
            pass
        await asyncio.sleep(interval_seconds)


async def stop_worker(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
