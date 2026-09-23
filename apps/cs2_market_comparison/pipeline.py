"""The three-stage RAG pipeline behind the Case Study 2 live demo — no Streamlit in here.

Stage 1  preprocessing   PDF -> clean text -> overlapping chunks -> embeddings
Stage 2  augmenting      embed the extraction prompt, cosine similarity, top-N above threshold
Stage 3  generation      one Structured Outputs call per company (openai.responses.parse)

Only the plain `openai` SDK is used, as in the seminar notebooks. Run this file directly to
download the three official reports and pre-build the embeddings cache before the session:

    python pipeline.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pymupdf
import numpy as np
import openai
from openai import OpenAI
from pydantic import BaseModel

from config import (
    ANNUAL_REPORT_URLS,
    APP_DIR,
    BROWSER_USER_AGENT,
    CACHE_DIR,
    CHUNK_SIZE,
    CUSTOM_QUERY_LABEL,
    DEFAULT_EMBEDDINGS_MODEL,
    LLM_MODELS,
    OVERLAP,
    REPORTS_DIR,
    SYSTEM_PROMPT,
    TEMPERATURE,
    THRESHOLD,
    TOP_N,
    USER_PROMPT_TEMPLATE,
)

Progress = Callable[[str], None]


def _no_progress(_: str) -> None:
    pass


# ---------------------------------------------------------------------------
# API key and client — environment first, then a local .env, then (in the app) a form field
# ---------------------------------------------------------------------------

def find_api_key(name: str = "OPENAI_API_KEY") -> str | None:
    """Return the key from the environment, else from the app folder's .env. Never prints it."""
    value = os.environ.get(name)
    if value:
        return value.strip()
    env_file = APP_DIR / ".env"
    if env_file.is_file():
        try:
            from dotenv import dotenv_values

            value = dotenv_values(env_file).get(name)
        except Exception:
            value = None
        if value:
            return value.strip()
    return None


def make_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, max_retries=4, timeout=180.0)


# ---------------------------------------------------------------------------
# Reports: download the three official PDFs on demand (never bundled)
# ---------------------------------------------------------------------------

def official_report_path(company: str) -> Path:
    return REPORTS_DIR / f"{company}.pdf"


def download_report(company: str, url: str, dest: Path | None = None, timeout: float = 180.0) -> Path:
    """Download one report with a browser User-Agent; write atomically; check it is a PDF."""
    dest = dest or official_report_path(company)
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url, headers={"User-Agent": BROWSER_USER_AGENT, "Accept": "application/pdf,*/*"}
    )
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(request, timeout=timeout) as response, tmp.open("wb") as fh:
        while block := response.read(1 << 20):
            fh.write(block)
    with tmp.open("rb") as fh:
        if fh.read(5) != b"%PDF-":
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"{company}: the server did not return a PDF ({url})")
    tmp.replace(dest)
    return dest


def download_official_reports(progress: Progress = _no_progress, force: bool = False) -> dict[str, Path]:
    """Download whichever of the three official reports are not on disk yet."""
    paths: dict[str, Path] = {}
    for company, url in ANNUAL_REPORT_URLS.items():
        path = official_report_path(company)
        if force or not path.is_file():
            progress(f"Downloading the {company} report ...")
            download_report(company, url, path)
        paths[company] = path
    return paths


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@dataclass
class Document:
    company: str
    filename: str
    sha256: str
    size_bytes: int
    path: Path | None = None       # official reports on disk
    data: bytes | None = None      # uploaded files, held in memory

    def read_bytes(self) -> bytes:
        if self.data is not None:
            return self.data
        assert self.path is not None
        return self.path.read_bytes()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def document_from_path(path: Path, company: str | None = None) -> Document:
    data = path.read_bytes()
    return Document(company or path.stem, path.name, sha256_bytes(data), len(data), path=path)


def document_from_bytes(filename: str, data: bytes) -> Document:
    return Document(Path(filename).stem, filename, sha256_bytes(data), len(data), data=data)


def pdf_page_count(data: bytes) -> int:
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        return doc.page_count


# ---------------------------------------------------------------------------
# Stage 1 — preprocessing
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Normalise whitespace while keeping the content."""
    cleaned = re.sub(r"[ \t]+", " ", text)
    cleaned = "\n".join(line.strip() for line in cleaned.splitlines())
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
    return cleaned.strip()


def extract_pdf_text(data: bytes) -> str:
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        text = "\n".join(page.get_text() for page in doc)
    return clean_text(text)


def create_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """Sliding window over characters: chunks of at most chunk_size, overlapping by overlap."""
    step = chunk_size - overlap
    if step <= 0:
        raise ValueError("chunk_size must be greater than overlap")
    return [text[i : i + chunk_size] for i in range(0, len(text), step)]


def embed_texts(
    client: OpenAI,
    model: str,
    texts: list[str],
    batch_size: int = 128,
    progress: Progress = _no_progress,
) -> np.ndarray:
    """Embed texts in batches; returns a float32 matrix with one row per text."""
    rows: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        progress(f"{start + len(batch)} / {len(texts)} chunks")
        response = client.embeddings.create(model=model, input=batch)
        rows.extend(item.embedding for item in sorted(response.data, key=lambda d: d.index))
    return np.asarray(rows, dtype=np.float32)


def embed_query(client: OpenAI, model: str, text: str) -> np.ndarray:
    response = client.embeddings.create(model=model, input=[text])
    return np.asarray(response.data[0].embedding, dtype=np.float32)


@dataclass
class Corpus:
    """Chunks (company, chunk_id, text) and their embeddings, row-aligned."""

    chunks: list[dict[str, str]]
    embeddings: np.ndarray
    meta: dict[str, Any] = field(default_factory=dict)

    def companies(self) -> list[str]:
        seen: dict[str, None] = {}
        for chunk in self.chunks:
            seen.setdefault(chunk["company"], None)
        return list(seen)

    def chunks_for(self, company: str) -> list[dict[str, Any]]:
        return [
            {**chunk, "embedding": self.embeddings[i]}
            for i, chunk in enumerate(self.chunks)
            if chunk["company"] == company
        ]


def build_corpus(
    client: OpenAI,
    documents: list[Document],
    embedding_model: str = DEFAULT_EMBEDDINGS_MODEL,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = OVERLAP,
    progress: Progress = _no_progress,
) -> Corpus:
    chunks: list[dict[str, str]] = []
    matrices: list[np.ndarray] = []
    doc_meta = []
    for n, doc in enumerate(documents, start=1):
        progress(f"Reading {doc.filename} ({n}/{len(documents)}) ...")
        text = extract_pdf_text(doc.read_bytes())
        pieces = create_chunks(text, chunk_size=chunk_size, overlap=overlap)
        doc_meta.append(
            {"company": doc.company, "filename": doc.filename, "sha256": doc.sha256,
             "characters": len(text), "chunks": len(pieces)}
        )
        if not pieces:
            continue
        matrices.append(
            embed_texts(
                client, embedding_model, pieces,
                progress=lambda msg, c=doc.company, n=n: progress(
                    f"Embedding {c} ({n}/{len(documents)}): {msg}"
                ),
            )
        )
        chunks.extend(
            {"company": doc.company, "chunk_id": f"{doc.company}-{i:03d}", "text": piece}
            for i, piece in enumerate(pieces, start=1)
        )
    embeddings = np.vstack(matrices) if matrices else np.zeros((0, 0), dtype=np.float32)
    meta = {
        "format": 1,
        "embedding_model": embedding_model,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "documents": doc_meta,
        "created_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    return Corpus(chunks, embeddings, meta)


# ---------------------------------------------------------------------------
# Embeddings cache in _local/embeddings_cache/: <key>.npz (vectors) + <key>.json (chunks, meta)
# No pickle, so loading a cache file can never execute code.
# ---------------------------------------------------------------------------

def cache_key(documents: list[Document], embedding_model: str, chunk_size: int, overlap: int) -> str:
    """Keyed on file *contents*, so a re-download or an identical upload hits the same cache."""
    ident = sorted((d.company, d.sha256) for d in documents)
    raw = json.dumps([ident, embedding_model, chunk_size, overlap]).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def cache_paths(key: str) -> tuple[Path, Path]:
    return CACHE_DIR / f"{key}.npz", CACHE_DIR / f"{key}.json"


def cache_exists(key: str) -> bool:
    return all(p.is_file() for p in cache_paths(key))


def save_corpus(corpus: Corpus, key: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    npz_path, json_path = cache_paths(key)
    tmp_npz = npz_path.with_name(npz_path.stem + ".part.npz")
    np.savez(tmp_npz, embeddings=corpus.embeddings)
    tmp_npz.replace(npz_path)
    json_path.write_text(
        json.dumps({"meta": corpus.meta, "chunks": corpus.chunks}, ensure_ascii=False),
        encoding="utf-8",
    )


def read_cache_meta(key: str) -> dict[str, Any]:
    try:
        return json.loads(cache_paths(key)[1].read_text(encoding="utf-8"))["meta"]
    except Exception:
        return {}


def load_corpus(key: str) -> Corpus:
    npz_path, json_path = cache_paths(key)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    with np.load(npz_path, allow_pickle=False) as npz:
        embeddings = npz["embeddings"]
    if len(payload["chunks"]) != len(embeddings):
        raise RuntimeError("Embeddings cache is inconsistent — recompute it.")
    return Corpus(payload["chunks"], embeddings, payload["meta"])


# ---------------------------------------------------------------------------
# Stage 2 — retrieval and prompt augmenting
# ---------------------------------------------------------------------------

def cosine_similarities(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    q = query / (np.linalg.norm(query) or 1.0)
    norms = np.linalg.norm(matrix, axis=1)
    norms[norms == 0] = 1.0
    return (matrix @ q) / norms


def retrieve_top_chunks(
    corpus: Corpus,
    company: str,
    query_embedding: np.ndarray,
    top_n: int = TOP_N,
    threshold: float = THRESHOLD,
) -> list[dict[str, Any]]:
    """Chunks of one company with cosine similarity >= threshold, best first, at most top_n."""
    idx = [i for i, chunk in enumerate(corpus.chunks) if chunk["company"] == company]
    if not idx:
        return []
    sims = cosine_similarities(query_embedding, corpus.embeddings[idx])
    scored = [
        {**corpus.chunks[i], "similarity": float(s)}
        for i, s in zip(idx, sims)
        if s >= threshold
    ]
    scored.sort(key=lambda row: row["similarity"], reverse=True)
    return scored[:top_n]


def render_context(chunks: list[dict[str, Any]]) -> str:
    blocks = []
    for rank, chunk in enumerate(chunks, start=1):
        blocks.append(
            f"[Context {rank}]\n"
            f"Company: {chunk['company']}\n"
            f"Chunk ID: {chunk['chunk_id']}\n"
            f"Similarity: {chunk['similarity']:.3f}\n"
            f"Text:\n{chunk['text']}"
        )
    return "\n\n".join(blocks)


def build_user_prompt(company: str, topic: str, extraction_prompt: str, chunks: list[dict]) -> str:
    return USER_PROMPT_TEMPLATE.format(
        company=company, topic=topic, extraction_prompt=extraction_prompt,
        context=render_context(chunks),
    )


_ENCODER = None


def count_tokens(text: str) -> tuple[int, bool]:
    """Token count with the o200k_base tokeniser; falls back to chars/4 if tiktoken fails.

    Returns (count, exact).
    """
    global _ENCODER
    try:
        if _ENCODER is None:
            import tiktoken

            _ENCODER = tiktoken.get_encoding("o200k_base")
        return len(_ENCODER.encode(text)), True
    except Exception:
        return max(1, len(text) // 4), False


# ---------------------------------------------------------------------------
# Stage 3 — generation with Structured Outputs
# ---------------------------------------------------------------------------

@dataclass
class Generation:
    parsed: BaseModel | None
    model: str
    seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    temperature: float | None = None
    note: str = ""
    error: str | None = None


def generate_structured(
    client: OpenAI,
    model_id: str,
    schema: type[BaseModel],
    user_prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
) -> Generation:
    """One Structured Outputs call. Temperature 0 is sent only to models that accept it."""
    spec = LLM_MODELS.get(model_id)
    kwargs: dict[str, Any] = dict(
        model=model_id, instructions=system_prompt, input=user_prompt, text_format=schema
    )
    temperature = TEMPERATURE if (spec is None or spec.accepts_temperature) else None
    if temperature is not None:
        kwargs["temperature"] = temperature
    note = ""
    start = time.perf_counter()
    try:
        response = client.responses.parse(**kwargs)
    except openai.BadRequestError as exc:
        # Safety net for the live demo: a model that unexpectedly rejects temperature is
        # retried once without it, and the card says so.
        if temperature is None or "temperature" not in str(exc).lower():
            raise
        kwargs.pop("temperature")
        temperature = None
        note = "model rejected temperature; retried without it"
        response = client.responses.parse(**kwargs)
    seconds = time.perf_counter() - start

    usage = getattr(response, "usage", None)
    parsed = response.output_parsed
    error = None
    if parsed is None:
        status = getattr(response, "status", "?")
        error = f"No structured output returned (status: {status}; possibly a refusal)."
    return Generation(
        parsed=parsed,
        model=getattr(response, "model", model_id),
        seconds=seconds,
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        temperature=temperature,
        note=note,
        error=error,
    )


def summarise_result(query_label: str, parsed: BaseModel) -> str:
    """A one-line, business-facing summary of a structured result."""
    if query_label == "solvency_ratio":
        return f"{parsed.capital_ratio}% under {parsed.regulatory_framework}"
    if query_label == "discount_rates":
        if not parsed.rates:
            return f"{parsed.currency} curve: no rate points extracted"
        points = ", ".join(
            f"{p.duration_year}y: {p.discount_rate_percent:.2f}%"
            for p in sorted(parsed.rates, key=lambda p: p.duration_year)
        )
        return f"{parsed.currency} curve: {points}"
    if query_label == "financial_strength_ratings":
        if not parsed.ratings:
            return "No insurer financial strength ratings extracted"
        return "; ".join(
            f"{r.rater}: {r.rating}" + (f" / {r.outlook}" if r.outlook else "")
            for r in parsed.ratings
        )
    if query_label == CUSTOM_QUERY_LABEL:
        return parsed.answer
    return json.dumps(parsed.model_dump(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Command line: prepare the laptop before the session
# ---------------------------------------------------------------------------

def official_documents() -> list[Document]:
    return [
        document_from_path(official_report_path(c), company=c)
        for c in ANNUAL_REPORT_URLS
        if official_report_path(c).is_file()
    ]


def prepare(force: bool = False) -> str:
    """Download the three reports (if missing) and build the default embeddings cache."""
    api_key = find_api_key()
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set (environment or .env in this folder).")
    download_official_reports(progress=print)
    documents = official_documents()
    key = cache_key(documents, DEFAULT_EMBEDDINGS_MODEL, CHUNK_SIZE, OVERLAP)
    if cache_exists(key) and not force:
        print(f"Embeddings cache already present: {cache_paths(key)[0].name}")
        return key
    corpus = build_corpus(make_client(api_key), documents, progress=print)
    save_corpus(corpus, key)
    print(f"Saved {len(corpus.chunks)} chunks to {cache_paths(key)[0]}")
    return key


if __name__ == "__main__":
    import sys

    prepare(force="--force" in sys.argv)
