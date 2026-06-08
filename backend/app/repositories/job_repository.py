import uuid
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.dialects.postgresql import ARRAY
from app.repositories.base import BaseRepository
from app.models.job_posting import JobPosting, JobStatus, WorkModel, JobBoard
from app.schemas.job_posting import JobPostingFilter


class JobRepository(BaseRepository[JobPosting]):
    def __init__(self, db: AsyncSession):
        super().__init__(JobPosting, db)

    def _build_filters(self, f: JobPostingFilter) -> List:
        filters = []
        if f.status:
            filters.append(JobPosting.status == f.status)
        if f.job_board:
            filters.append(JobPosting.job_board == f.job_board)
        if f.work_model:
            filters.append(JobPosting.work_model == f.work_model)
        if f.tech_stack:
            filters.append(JobPosting.tech_stack.contains([f.tech_stack]))
        if f.location:
            filters.append(JobPosting.location.ilike(f"%{f.location}%"))
        if f.search:
            filters.append(
                or_(
                    JobPosting.company_name.ilike(f"%{f.search}%"),
                    JobPosting.job_title.ilike(f"%{f.search}%"),
                )
            )
        return filters

    async def get_filtered(
        self, f: JobPostingFilter
    ) -> Tuple[List[JobPosting], int]:
        filters = self._build_filters(f)
        total = await self.count(filters)
        skip = (f.page - 1) * f.page_size
        items = await self.get_all(
            skip=skip,
            limit=f.page_size,
            filters=filters,
            order_by=JobPosting.created_at.desc(),
        )
        return items, total

    async def get_by_url(self, job_url: str) -> Optional[JobPosting]:
        result = await self.db.execute(
            select(JobPosting).where(JobPosting.job_url == job_url)
        )
        return result.scalar_one_or_none()

    async def get_status_counts(self) -> dict:
        result = await self.db.execute(
            select(JobPosting.status, func.count(JobPosting.id))
            .group_by(JobPosting.status)
        )
        return {str(row[0].value): row[1] for row in result.all()}

    async def get_jobs_per_day(self, days: int = 30) -> List[dict]:
        result = await self.db.execute(
            text("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM job_postings
                WHERE created_at >= NOW() - INTERVAL ':days days'
                GROUP BY DATE(created_at)
                ORDER BY date
            """).bindparams(days=days)
        )
        return [{"date": str(row[0]), "count": row[1]} for row in result.all()]

    async def get_top_technologies(self, limit: int = 10) -> List[dict]:
        result = await self.db.execute(
            text("""
                SELECT unnest(tech_stack) as technology, COUNT(*) as count
                FROM job_postings
                WHERE tech_stack IS NOT NULL
                GROUP BY technology
                ORDER BY count DESC
                LIMIT :limit
            """).bindparams(limit=limit)
        )
        return [{"technology": row[0], "count": row[1]} for row in result.all()]

    async def get_top_locations(self, limit: int = 10) -> List[dict]:
        result = await self.db.execute(
            text("""
                SELECT location, COUNT(*) as count
                FROM job_postings
                WHERE location IS NOT NULL AND location != ''
                GROUP BY location
                ORDER BY count DESC
                LIMIT :limit
            """).bindparams(limit=limit)
        )
        return [{"location": row[0], "count": row[1]} for row in result.all()]
