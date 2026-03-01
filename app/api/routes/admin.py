from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import verify_admin_key
from app.db.models import AuditLog
from app.db.session import get_db
from app.schemas.policy import ApproveKBRequest, PolicyUpdateRequest, ReindexRequest, RetentionRunRequest
from app.services.kb_service import KBService
from app.services.policy_service import PolicyService
from app.services.retention_service import RetentionService

router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(verify_admin_key)])


@router.post("/policy")
def upsert_policy(payload: PolicyUpdateRequest, db: Session = Depends(get_db)) -> dict:
    PolicyService(db).update_policy(payload.policy_key, payload.policy_value, payload.updated_by)
    db.add(
        AuditLog(
            actor=payload.updated_by,
            action="policy_update",
            payload_json={"key": payload.policy_key, "value": payload.policy_value},
        )
    )
    db.commit()
    return {"status": "ok", "policy_key": payload.policy_key}


@router.post("/kb/reindex")
def reindex_kb(payload: ReindexRequest, db: Session = Depends(get_db)) -> dict:
    return KBService(db).reindex(payload.urls, payload.updated_by)


@router.post("/kb/approve")
def approve_kb(payload: ApproveKBRequest, db: Session = Depends(get_db)) -> dict:
    updated = KBService(db).approve_chunks(payload.chunk_ids, payload.approved, payload.updated_by)
    return {"status": "ok", "updated": updated}


@router.post("/privacy/retention-run")
def run_retention(payload: RetentionRunRequest, db: Session = Depends(get_db)) -> dict:
    return RetentionService(db).run_cleanup(updated_by=payload.updated_by, dry_run=payload.dry_run)
