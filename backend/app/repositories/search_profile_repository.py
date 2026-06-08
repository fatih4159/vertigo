import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.search_profile import SearchProfile


class SearchProfileRepository(BaseRepository[SearchProfile]):
    def __init__(self, db: AsyncSession):
        super().__init__(SearchProfile, db)

    async def get_active(self) -> List[SearchProfile]:
        result = await self.db.execute(
            select(SearchProfile).where(SearchProfile.active == True)
        )
        return list(result.scalars().all())
