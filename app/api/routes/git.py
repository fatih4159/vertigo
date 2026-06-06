"""Git API routes."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.integrations.git.client import GitClient
from app.core.exceptions import GitOperationError, GitConfirmationRequired, WorkspaceSecurityError
from app.storage.repositories import AgentRepository, GitActionRepository

router = APIRouter(prefix="/git", tags=["git"])


class GitStatusRequest(BaseModel):
    repo_path: str


class GitCommitRequest(BaseModel):
    repo_path: str
    message: str
    agent_id: Optional[str] = None
    author_name: str = "AAOS Agent"
    author_email: str = "agent@aaos.local"


class GitBranchRequest(BaseModel):
    repo_path: str
    branch_name: str
    checkout: bool = True


@router.post("/status")
async def git_status(body: GitStatusRequest) -> Dict[str, Any]:
    try:
        client = GitClient(body.repo_path)
        return client.status()
    except (GitOperationError, WorkspaceSecurityError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/log")
async def git_log(body: GitStatusRequest, n: int = 20) -> List[Dict[str, str]]:
    try:
        client = GitClient(body.repo_path)
        return client.log(n=n)
    except (GitOperationError, WorkspaceSecurityError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/commit")
async def git_commit(
    body: GitCommitRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    try:
        client = GitClient(body.repo_path)
        result = client.commit(
            message=body.message,
            author_name=body.author_name,
            author_email=body.author_email,
        )
        # Log git action if agent_id provided
        if body.agent_id:
            git_repo = GitActionRepository(db)
            await git_repo.create(
                agent_id=body.agent_id,
                action_type="commit",
                repository=body.repo_path,
                details={"message": body.message},
                requires_confirmation=False,
            )
            await db.commit()
        return {"success": True, "output": result}
    except GitConfirmationRequired as exc:
        raise HTTPException(status_code=202, detail={"requires_confirmation": True, "details": exc.details})
    except (GitOperationError, WorkspaceSecurityError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/branch")
async def create_branch(body: GitBranchRequest) -> Dict[str, Any]:
    try:
        client = GitClient(body.repo_path)
        result = client.create_branch(body.branch_name, checkout=body.checkout)
        return {"success": True, "branch": body.branch_name, "output": result}
    except (GitOperationError, WorkspaceSecurityError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/actions/{agent_id}")
async def list_git_actions(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    repo = AgentRepository(db)
    try:
        await repo.get_or_raise(agent_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    git_repo = GitActionRepository(db)
    actions = await git_repo.list_for_agent(agent_id)
    return [
        {
            "id": a.id,
            "action_type": a.action_type,
            "repository": a.repository,
            "details": a.details_json,
            "requires_confirmation": a.requires_confirmation,
            "confirmed": a.confirmed,
            "executed_at": a.executed_at.isoformat() if a.executed_at else None,
        }
        for a in actions
    ]
