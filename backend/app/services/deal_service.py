import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.repositories.job_repository import JobRepository
from app.repositories.deal_repository import DealRepository
from app.repositories.log_repository import LogRepository
from app.models.job_posting import JobStatus
from app.models.deal import Deal, DealStatus
from app.models.log_entry import LogLevel
from app.services.pipedrive_service import PipedriveService, PipedriveError
from app.core.config import get_settings

settings = get_settings()

REQUIRED_FIELDS = ["company_name", "company_website", "job_title", "job_board", "job_url"]


class DealService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_repo = JobRepository(db)
        self.deal_repo = DealRepository(db)
        self.log_repo = LogRepository(db)
        self.pipedrive = PipedriveService()

    def _validate_job(self, job) -> Optional[str]:
        for field in REQUIRED_FIELDS:
            val = getattr(job, field, None)
            if not val:
                return f"Missing required field: {field}"
        return None

    async def create_deal_for_job(self, job_id: uuid.UUID) -> Deal:
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        existing_deal = await self.deal_repo.get_by_job_id(job_id)
        if existing_deal and existing_deal.status == DealStatus.CREATED:
            logger.info(f"Deal already created for job {job_id}")
            return existing_deal

        error = self._validate_job(job)
        if error:
            raise ValueError(error)

        if not settings.PIPEDRIVE_API_TOKEN:
            raise ValueError("Pipedrive API token not configured")

        deal_record = await self.deal_repo.create({
            "job_id": job_id,
            "status": DealStatus.PENDING,
        })

        try:
            org = await self.pipedrive.create_organization(
                name=job.company_name,
                website=job.company_website,
            )
            org_id = org.get("id")

            tech_str = ", ".join(job.tech_stack or [])
            note_fields = {
                "source_url": job.job_url,
                "job_board": str(job.job_board.value) if job.job_board else "",
                "location": job.location or "",
                "work_model": str(job.work_model.value) if job.work_model else "",
                "tech_stack": tech_str,
                "score": str(job.score),
            }
            deal_title = f"{job.company_name} - {job.job_title}"
            pd_deal = await self.pipedrive.create_deal(
                title=deal_title,
                org_id=org_id,
            )

            await self.deal_repo.update(
                deal_record.id,
                {
                    "pipedrive_deal_id": pd_deal["id"],
                    "pipedrive_org_id": org_id,
                    "status": DealStatus.CREATED,
                },
            )
            await self.job_repo.update(job_id, {"status": JobStatus.DEAL_CREATED})
            await self.log_repo.add_entry(
                level=LogLevel.INFO,
                message=f"Deal created in Pipedrive for {job.company_name}: deal_id={pd_deal['id']}",
                source="deal_service",
            )
            logger.info(f"Deal created: {deal_title} -> Pipedrive ID {pd_deal['id']}")

        except PipedriveError as e:
            await self.deal_repo.update(
                deal_record.id,
                {"status": DealStatus.FAILED, "error_message": str(e)},
            )
            await self.job_repo.update(job_id, {"status": JobStatus.FAILED})
            await self.log_repo.add_entry(
                level=LogLevel.ERROR,
                message=f"Failed to create Pipedrive deal for {job.company_name}: {e}",
                source="deal_service",
            )
            logger.error(f"Pipedrive deal creation failed: {e}")
            raise

        finally:
            await self.pipedrive.close()

        return await self.deal_repo.get_by_id(deal_record.id)
