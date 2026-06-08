import asyncio
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.repositories.search_profile_repository import SearchProfileRepository
from app.repositories.log_repository import LogRepository
from app.services.job_service import JobService
from app.models.log_entry import LogLevel
from app.schemas.job_posting import JobPostingCreate
from app.models.job_posting import JobBoard


class DiscoveryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.search_profile_repo = SearchProfileRepository(db)
        self.log_repo = LogRepository(db)
        self.job_service = JobService(db)

    async def run_discovery(self, profile_id: Optional[str] = None) -> dict:
        from app.core.redis import set_discovery_status

        await set_discovery_status({"status": "running", "started_at": datetime.now(timezone.utc).isoformat()})

        try:
            if profile_id:
                import uuid
                profiles = []
                p = await self.search_profile_repo.get_by_id(uuid.UUID(profile_id))
                if p:
                    profiles = [p]
            else:
                profiles = await self.search_profile_repo.get_active()

            if not profiles:
                logger.warning("No active search profiles found")
                await set_discovery_status({"status": "idle", "message": "No active profiles"})
                return {"status": "ok", "jobs_found": 0, "jobs_created": 0}

            total_found = 0
            total_created = 0

            for profile in profiles:
                logger.info(f"Running discovery for profile: {profile.name}")
                found, created = await self._run_profile(profile)
                total_found += found
                total_created += created

                await self.search_profile_repo.update(
                    profile.id, {"last_run_at": datetime.now(timezone.utc)}
                )

            await set_discovery_status({
                "status": "idle",
                "last_run": datetime.now(timezone.utc).isoformat(),
                "jobs_found": total_found,
                "jobs_created": total_created,
            })

            await self.log_repo.add_entry(
                level=LogLevel.INFO,
                message=f"Discovery completed: {total_found} found, {total_created} new",
                source="discovery_service",
            )

            return {"status": "ok", "jobs_found": total_found, "jobs_created": total_created}

        except Exception as e:
            logger.error(f"Discovery failed: {e}", exc_info=True)
            await set_discovery_status({"status": "error", "error": str(e)})
            await self.log_repo.add_entry(
                level=LogLevel.ERROR,
                message=f"Discovery error: {e}",
                source="discovery_service",
            )
            return {"status": "error", "message": str(e)}

    async def _run_profile(self, profile) -> tuple:
        from app.connectors import get_connector

        found = 0
        created = 0

        for source in profile.sources:
            try:
                connector = get_connector(source)
                if connector is None:
                    logger.warning(f"No connector for source: {source}")
                    continue

                jobs_data = await connector.fetch_jobs(
                    keywords=profile.keywords,
                    locations=profile.locations or [],
                    remote_only=profile.remote_only,
                )

                for job_data in jobs_data:
                    found += 1
                    try:
                        job_in = JobPostingCreate(**job_data)
                        _, is_new = await self.job_service.create_or_skip(job_in)
                        if is_new:
                            created += 1
                    except Exception as e:
                        logger.error(f"Failed to process job from {source}: {e}")

            except Exception as e:
                logger.error(f"Connector error for {source}: {e}", exc_info=True)
                await self.log_repo.add_entry(
                    level=LogLevel.ERROR,
                    message=f"Connector error [{source}]: {e}",
                    source="discovery_service",
                )

        return found, created
