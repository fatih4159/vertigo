import httpx
from typing import Optional, Dict, Any
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import get_settings

settings = get_settings()


class PipedriveError(Exception):
    pass


class PipedriveService:
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or settings.PIPEDRIVE_API_TOKEN
        self.base_url = settings.PIPEDRIVE_BASE_URL
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    def _params(self, extra: Optional[dict] = None) -> dict:
        p = {"api_token": self.api_token}
        if extra:
            p.update(extra)
        return p

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def create_organization(self, name: str, website: Optional[str] = None) -> Dict:
        client = await self._get_client()
        payload: Dict[str, Any] = {"name": name}
        if website:
            payload["website"] = website
        resp = await client.post(
            f"{self.base_url}/organizations",
            params=self._params(),
            json=payload,
        )
        if resp.status_code not in (200, 201):
            raise PipedriveError(f"Create org failed: {resp.status_code} {resp.text}")
        data = resp.json()
        if not data.get("success"):
            raise PipedriveError(f"Pipedrive error: {data}")
        return data["data"]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def create_deal(
        self,
        title: str,
        org_id: Optional[int] = None,
        pipeline_id: Optional[int] = None,
        stage_id: Optional[int] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        client = await self._get_client()
        payload: Dict[str, Any] = {
            "title": title,
            "pipeline_id": pipeline_id or settings.PIPEDRIVE_PIPELINE_ID,
            "stage_id": stage_id or settings.PIPEDRIVE_STAGE_ID,
        }
        if org_id:
            payload["org_id"] = org_id
        if custom_fields:
            payload.update(custom_fields)

        resp = await client.post(
            f"{self.base_url}/deals",
            params=self._params(),
            json=payload,
        )
        if resp.status_code not in (200, 201):
            raise PipedriveError(f"Create deal failed: {resp.status_code} {resp.text}")
        data = resp.json()
        if not data.get("success"):
            raise PipedriveError(f"Pipedrive error: {data}")
        return data["data"]

    async def get_deal(self, deal_id: int) -> Optional[Dict]:
        client = await self._get_client()
        resp = await client.get(
            f"{self.base_url}/deals/{deal_id}",
            params=self._params(),
        )
        if resp.status_code == 404:
            return None
        data = resp.json()
        return data.get("data")

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
