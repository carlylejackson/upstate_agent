import hashlib
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AuditLog, KBChunk
from app.services.llm_service import LLMService


class KBService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.llm = LLMService()

    def reindex(self, urls: list[str] | None, updated_by: str) -> dict:
        urls_to_use = urls or self.settings.kb_source_urls_list
        version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        upserted = 0

        for url in urls_to_use:
            text, title = self._fetch_url(url)
            if not text:
                continue
            page_type = self._classify_page_type(url)
            approved = not (self.settings.manual_policy_approval and page_type == "policy")
            for idx, chunk in enumerate(self._chunk_text(text)):
                chunk_id = self._chunk_id(url, idx, chunk)
                embedding = self.llm.embed_text(chunk)
                upserted += self._upsert_chunk(
                    chunk_id=chunk_id,
                    source_url=url,
                    title=title,
                    content=chunk,
                    metadata={"topic": page_type, "page_type": page_type, "last_seen": version},
                    embedding=embedding,
                    approved=approved,
                    version=version,
                )

        self.db.add(
            AuditLog(actor=updated_by, action="kb_reindex", payload_json={"urls": urls_to_use, "version": version})
        )
        self.db.commit()
        return {"version": version, "upserted_chunks": upserted}

    def approve_chunks(self, chunk_ids: list[str], approved: bool, updated_by: str) -> int:
        rows = self.db.scalars(select(KBChunk).where(KBChunk.chunk_id.in_(chunk_ids))).all()
        for row in rows:
            row.approved = approved
        self.db.add(
            AuditLog(
                actor=updated_by,
                action="kb_approval",
                payload_json={"chunk_ids": chunk_ids, "approved": approved},
            )
        )
        self.db.commit()
        return len(rows)

    def _fetch_url(self, url: str) -> tuple[str, str]:
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
        except Exception:  # noqa: BLE001
            return "", ""

        soup = BeautifulSoup(response.text, "html.parser")
        title = (soup.title.string or "").strip() if soup.title else ""
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        text = "\n".join(part.strip() for part in soup.stripped_strings if part.strip())
        return text, title

    def _chunk_text(self, text: str, size: int = 800, overlap: int = 120) -> list[str]:
        text = re.sub(r"\s+", " ", text)
        if len(text) <= size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - overlap
        return chunks

    def _chunk_id(self, url: str, idx: int, chunk: str) -> str:
        raw = f"{url}:{idx}:{chunk[:80]}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _classify_page_type(self, url: str) -> str:
        lowered = url.lower()
        if "contact" in lowered or "insurance" in lowered:
            return "policy"
        if "service" in lowered:
            return "services"
        return "general"

    def _upsert_chunk(
        self,
        chunk_id: str,
        source_url: str,
        title: str,
        content: str,
        metadata: dict,
        embedding: list[float] | None,
        approved: bool,
        version: str,
    ) -> int:
        existing = self.db.scalar(select(KBChunk).where(KBChunk.chunk_id == chunk_id))
        if existing:
            existing.content = content
            existing.metadata_json = metadata
            existing.embedding_json = embedding
            existing.approved = approved
            existing.version = version
            return 1

        self.db.add(
            KBChunk(
                chunk_id=chunk_id,
                source_url=source_url,
                title=title,
                content=content,
                metadata_json=metadata,
                embedding_json=embedding,
                approved=approved,
                version=version,
            )
        )
        return 1
