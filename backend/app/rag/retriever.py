import numpy as np
from sqlalchemy import select, text
from app.db.models import Chunk, Document
from app.db.repository import Session, engine
from app.rag.embeddings import embed


def search_knowledge(query: str, top_k: int = 6, trusted_only: bool = False):
    vector = embed([query])[0]
    with Session() as s:
        if engine.dialect.name == "postgresql":
            rows = s.execute(
                text(
                    "SELECT c.id,1-(v.embedding <=> CAST(:q AS vector)) AS score FROM chunk_vectors v JOIN chunks c ON c.id=v.chunk_id JOIN documents d ON d.id=c.document_id WHERE (:trusted=0 OR d.trusted=1) ORDER BY v.embedding <=> CAST(:q AS vector) LIMIT :k"
                ),
                {"q": str(vector), "k": top_k, "trusted": int(trusted_only)},
            ).all()
            ranked = [(s.get(Chunk, cid), float(score)) for cid, score in rows if score is not None]
        else:
            chunks = list(
                s.scalars(
                    select(Chunk).join(Document).where(Document.trusted == 1)
                    if trusted_only
                    else select(Chunk)
                )
            )
            ranked = sorted(
                [(c, float(np.dot(vector, c.embedding))) for c in chunks],
                key=lambda item: item[1],
                reverse=True,
            )[:top_k]
        return [
            {
                "chunk_id": c.id,
                "document_id": c.document_id,
                "document_name": s.get(Document, c.document_id).name,
                "section": c.section,
                "text": c.text,
                "score": round(score, 5),
                "trusted": bool(s.get(Document, c.document_id).trusted),
            }
            for c, score in ranked
            if score > 0.025
        ]
