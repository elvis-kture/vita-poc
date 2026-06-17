import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import IdempotencyRecord


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> IdempotencyRecord | None:
        rows = await self.session.execute(
            select(IdempotencyRecord).where(IdempotencyRecord.key == key)
        )
        return rows.scalar_one_or_none()

    async def create(
        self,
        *,
        key: str,
        booking_id: int | None,
        status_code: int,
        response_body: dict[str, Any],
    ) -> IdempotencyRecord:
        record = IdempotencyRecord(
            key=key,
            booking_id=booking_id,
            status_code=status_code,
            response_body=json.dumps(response_body),
        )
        self.session.add(record)
        await self.session.flush()
        return record
