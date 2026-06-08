import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.repositories.base import BaseRepository
from app.models.deal import Deal, DealStatus


class DealRepository(BaseRepository[Deal]):
    def __init__(self, db: AsyncSession):
        super().__init__(Deal, db)

    async def get_by_job_id(self, job_id: uuid.UUID) -> Optional[Deal]:
        result = await self.db.execute(
            select(Deal).where(Deal.job_id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_deals_per_day(self, days: int = 30) -> List[dict]:
        result = await self.db.execute(
            text("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM deals
                WHERE status = 'created' AND created_at >= NOW() - INTERVAL ':days days'
                GROUP BY DATE(created_at)
                ORDER BY date
            """).bindparams(days=days)
        )
        return [{"date": str(row[0]), "count": row[1]} for row in result.all()]
