import math
import re
from collections import Counter

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import KBChunk
from app.services.llm_service import LLMService


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.llm = LLMService()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    @staticmethod
    def _cosine(a: Counter, b: Counter) -> float:
        intersection = set(a.keys()) & set(b.keys())
        numerator = sum(a[t] * b[t] for t in intersection)
        a_mag = math.sqrt(sum(v * v for v in a.values()))
        b_mag = math.sqrt(sum(v * v for v in b.values()))
        if a_mag == 0 or b_mag == 0:
            return 0.0
        return numerator / (a_mag * b_mag)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            pgvector_results = self._search_postgres_pgvector(query, top_k)
            if pgvector_results:
                return pgvector_results

        rows = self.db.scalars(select(KBChunk).where(KBChunk.approved.is_(True))).all()
        q_count = Counter(self._tokenize(query))
        scored: list[tuple[float, KBChunk]] = []
        for row in rows:
            text = f"{row.title} {row.content}"
            score = self._cosine(q_count, Counter(self._tokenize(text)))
            if score <= 0:
                continue
            scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        output = []
        for score, row in scored[:top_k]:
            output.append(
                {
                    "source_url": row.source_url,
                    "title": row.title,
                    "snippet": row.content[:260],
                    "score": round(score, 4),
                }
            )
        return output

    def _search_postgres_pgvector(self, query: str, top_k: int) -> list[dict]:
        """
        pgvector scaffold for production Postgres.
        Uses SQL fallback if vector column exists; otherwise returns empty and caller falls back to lexical search.
        """
        query_embedding = self.llm.embed_text(query)
        vector_literal = self._to_pgvector_literal(query_embedding)
        if not vector_literal:
            return []

        # This assumes a future migration with `embedding vector` column. If missing, the query fails gracefully.
        statement = text(
            """
            SELECT source_url, title, content, 1 - (embedding <=> CAST(:embedding AS vector)) AS score
            FROM kb_chunks
            WHERE approved = true
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        )
        try:
            rows = self.db.execute(
                statement,
                {
                    "embedding": vector_literal,
                    "limit": top_k,
                },
            ).all()
        except Exception:  # noqa: BLE001
            return []

        return [
            {
                "source_url": row.source_url,
                "title": row.title or "",
                "snippet": (row.content or "")[:260],
                "score": round(float(row.score or 0), 4),
            }
            for row in rows
        ]

    @staticmethod
    def _to_pgvector_literal(embedding: list[float] | None) -> str | None:
        if not embedding:
            return None
        return "[" + ",".join(f"{value:.10f}" for value in embedding) + "]"
