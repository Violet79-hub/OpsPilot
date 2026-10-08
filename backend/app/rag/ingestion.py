import hashlib
import io
import re
from pathlib import Path
from pypdf import PdfReader
from sqlalchemy import select, text
from app.config import MAX_UPLOAD
from app.db.models import Document, Chunk
from app.db.repository import Session, engine, new_id
from app.rag.embeddings import embed


def extract(name: str, data: bytes) -> str:
    if len(data) > MAX_UPLOAD:
        raise ValueError("Maximum file size is 5 MB")
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        if len(reader.pages) > 100:
            raise ValueError("Maximum PDF length is 100 pages")
        content = "\n".join(p.extract_text() or "" for p in reader.pages)
    elif suffix in {".txt", ".md"}:
        content = data.decode("utf-8")
    else:
        raise ValueError("Supported formats: PDF, TXT, Markdown")
    content = content.replace("\x00", "").strip()
    if len(content) < 20:
        raise ValueError("Document has insufficient extractable text; OCR is not supported")
    return content


def chunk_text(content: str):
    section = "Overview"
    for block in re.split(r"(?m)^##\s+", content):
        lines = block.strip().splitlines()
        if not lines:
            continue
        if not lines[0].startswith("#"):
            section = lines[0][:150]
            body = "\n".join(lines[1:]).strip() or lines[0]
        else:
            body = block.strip()
        words = body.split()
        for start in range(0, len(words), 180):
            chunk = " ".join(words[start : start + 220])
            if len(chunk) >= 20:
                yield section, chunk


def ingest(name, data, trusted=False, document_id=None):
    content = extract(name, data)
    digest = hashlib.sha256(data).hexdigest()
    with Session.begin() as s:
        existing = s.scalar(select(Document).where(Document.content_hash == digest))
        if existing:
            return {"id": existing.id, "name": existing.name, "duplicate": True}
        did = document_id or new_id()
        if s.get(Document, did):
            raise ValueError(
                "Seed policy changed. Use a fresh database or explicit policy migration."
            )
        s.add(Document(id=did, name=Path(name).name, content_hash=digest, trusted=int(trusted)))
        s.flush()
        chunks = list(chunk_text(content))
        vectors = embed([section + " " + body for section, body in chunks])
        for i, ((section, body), vec) in enumerate(zip(chunks, vectors)):
            cid = f"{did}:{i}"
            s.add(
                Chunk(
                    id=cid,
                    document_id=did,
                    section=section,
                    text=body,
                    embedding=vec,
                    meta={"embedding_model": "hashing-512-v1", "trusted": trusted},
                )
            )
            s.flush()
            if engine.dialect.name == "postgresql":
                s.execute(
                    text(
                        "INSERT INTO chunk_vectors(chunk_id,embedding) VALUES (:id,CAST(:vec AS vector))"
                    ),
                    {"id": cid, "vec": str(vec)},
                )
        return {"id": did, "name": Path(name).name, "chunks": len(chunks), "duplicate": False}
