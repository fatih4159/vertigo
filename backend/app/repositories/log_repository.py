from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.repositories.base import BaseRepository
from app.models.log_entry import LogEntry, LogLevel
from app.schemas.log_entry import LogFilter


class LogRepository(BaseRepository[LogEntry]):
    def __init__(self, db: AsyncSession):
        super().__init__(LogEntry, db)

    async def get_filtered(
        self, f: LogFilter
    ) -> Tuple[List[LogEntry], int]:
        filters = []
        if f.level:
            filters.append(LogEntry.level == f.level)
        if f.source:
            filters.append(LogEntry.source == f.source)
        if f.search:
            filters.append(LogEntry.message.ilike(f"%{f.search}%"))

        total = await self.count(filters)
        skip = (f.page - 1) * f.page_size
        items = await self.get_all(
            skip=skip,
            limit=f.page_size,
            filters=filters,
            order_by=LogEntry.created_at.desc(),
        )
        return items, total

    async def add_entry(
        self, level: LogLevel, message: str, source: str = None, extra_data: str = None
    ) -> LogEntry:
        return await self.create({
            "level": level,
            "message": message,
            "source": source,
            "extra_data": extra_data,
        })
