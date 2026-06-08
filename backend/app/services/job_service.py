import uuid
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.repositories.job_repository import JobRepository
from app.repositories.log_repository import LogRepository
from app.models.job_posting import JobPosting, JobStatus
from app.models.log_entry import LogLevel
from app.schemas.job_posting import JobPostingCreate, JobPostingUpdate, JobPostingFilter
from app.services.analysis_service import AnalysisService


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_repo = JobRepository(db)
        self.log_repo = LogRepository(db)
        self.analysis = AnalysisService()

    async def get_jobs(self, f: JobPostingFilter):
        items, total = await self.job_repo.get_filtered(f)
        return items, total

    async def get_job(self, job_id: uuid.UUID) -> Optional[JobPosting]:
        return await self.job_repo.get_by_id(job_id)

    async def create_or_skip(self, job_in: JobPostingCreate) -> Tuple[Optional[JobPosting], bool]:
        existing = await self.job_repo.get_by_url(job_in.job_url)
        if existing:
            logger.debug(f"Duplicate job URL: {job_in.job_url}")
            return existing, False

        analysis = self.analysis.analyze_job(
            title=job_in.job_title,
            description=job_in.description,
            location_hint=job_in.location,
        )

        data = job_in.model_dump()
        data["tech_stack"] = analysis["tech_stack"]
        data["work_model"] = analysis["work_model"]
        data["score"] = analysis["score"]
        if analysis["location"]:
            data["location"] = analysis["location"]

        job = await self.job_repo.create(data)
        await self.log_repo.add_entry(
            level=LogLevel.INFO,
            message=f"New job found: {job.company_name} - {job.job_title}",
            source="job_service",
        )
        logger.info(f"Created job: {job.company_name} - {job.job_title} (score={job.score})")
        return job, True

    async def update_job(
        self, job_id: uuid.UUID, update_in: JobPostingUpdate
    ) -> Optional[JobPosting]:
        data = update_in.model_dump(exclude_none=True)
        return await self.job_repo.update(job_id, data)

    async def mark_as_ignored(self, job_id: uuid.UUID) -> Optional[JobPosting]:
        return await self.job_repo.update(job_id, {"status": JobStatus.IGNORED})

    async def mark_as_duplicate(self, job_id: uuid.UUID) -> Optional[JobPosting]:
        return await self.job_repo.update(job_id, {"status": JobStatus.DUPLICATE})

    async def get_status_counts(self) -> dict:
        return await self.job_repo.get_status_counts()
