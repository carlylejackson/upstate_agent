from pydantic import BaseModel, Field


class PolicyUpdateRequest(BaseModel):
    policy_key: str = Field(min_length=2, max_length=128)
    policy_value: str = Field(min_length=1)
    updated_by: str = "admin"


class ReindexRequest(BaseModel):
    urls: list[str] | None = None
    updated_by: str = "admin"


class ApproveKBRequest(BaseModel):
    chunk_ids: list[str]
    approved: bool = True
    updated_by: str = "admin"


class RetentionRunRequest(BaseModel):
    dry_run: bool = True
    updated_by: str = "admin"
