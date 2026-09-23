"""Case Study 2 live demo — market comparison using retrieval-augmented generation.

Start with `streamlit run app.py` from this folder (or `python app.py`, which does the same).
The pipeline itself lives in pipeline.py; this file is only the step-by-step interface.
"""

from __future__ import annotations


# --- `python app.py` launcher shim ---------------------------------------------------------
def _is_running_under_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except Exception:
        return False
    return get_script_run_ctx(suppress_warning=True) is not None


if __name__ == "__main__" and not _is_running_under_streamlit():
    import os
    import sys
    from pathlib import Path

    from streamlit.web import cli as stcli

    os.chdir(Path(__file__).resolve().parent)  # so .streamlit/config.toml (the theme) is found
    sys.argv = ["streamlit", "run", str(Path(__file__).resolve()), *sys.argv[1:]]
    sys.exit(stcli.main())
# --- end shim ------------------------------------------------------------------------------


import hashlib
import html
import inspect
import json
import os
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path

import openai
import streamlit as st

# Make this folder's config.py and pipeline.py importable however the app is started.
_APP_DIR = str(Path(__file__).resolve().parent)
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import pipeline  # noqa: E402
from config import (  # noqa: E402
    ANNUAL_REPORT_URLS,
    CAPTIONS,
    CHUNK_SIZE,
    CHUNK_SIZE_RANGE,
    CSS,
    CUSTOM_QUERY_LABEL,
    CUSTOM_QUERY_TITLE,
    DEFAULT_EMBEDDINGS_MODEL,
    DEFAULT_LLM,
    EMBEDDINGS_DISPLAY_NAMES,
    EMBEDDINGS_MODELS,
    FreeFormAnswer,
    LLM_MODELS,
    OVERLAP,
    OVERLAP_RANGE,
    QUERY_RADIO_OPTIONS,
    QUERY_SPECS,
    SCHEMA_CLASSES,
    SEED,
    SIMILARITY_RAMP,
    SYSTEM_PROMPT,
    THRESHOLD,
    THRESHOLD_RANGE,
    TOP_N,
    TOP_N_RANGE,
    USER_PROMPT_TEMPLATE,
)


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Case Study 2 — Market Comparison with RAG",
    page_icon=":material/query_stats:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

SOURCE_OFFICIAL = "official"
SOURCE_UPLOAD = "upload"


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

STATE_TIERS: dict[int, list[str]] = {
    0: ["config_done", "_validated_config", "documents", "unavailable_models"],
    1: ["corpus", "cache_loaded_flag", "preview_company", "preview_start_idx", "step1_done",
        "_chunked_with"],
    2: ["step2_done", "query_label", "extraction_prompt_text", "_confirmed_query"],
    3: ["step3_done", "retrieved", "_retrieved_with"],
    4: ["step4_done", "user_prompts", "prompt_token_counts"],
    5: ["step5_done", "results", "_generated_with"],
}

_CONFIG_VERSION = "2026-09-22-seminar"  # bump when defaults change, to reset stale sessions

_RAG_PARAM_DEFAULTS = {
    "chunk_size": CHUNK_SIZE,
    "overlap": OVERLAP,
    "top_n": TOP_N,
    "threshold": THRESHOLD,
}


def _reset_from(start_tier: int) -> None:
    for tier, keys in STATE_TIERS.items():
        if tier >= start_tier:
            for key in keys:
                st.session_state.pop(key, None)


def _reset_demo() -> None:
    _reset_from(0)
    for key in ("uploaded_pdfs", "manual_key", "use_other_key", *_RAG_PARAM_DEFAULTS):
        st.session_state.pop(key, None)


def _init_state_defaults() -> None:
    if st.session_state.get("_config_version") != _CONFIG_VERSION:
        for key in _RAG_PARAM_DEFAULTS:
            st.session_state.pop(key, None)
        st.session_state["_config_version"] = _CONFIG_VERSION
    defaults = {
        "report_source": SOURCE_OFFICIAL,
        "embedding_model": DEFAULT_EMBEDDINGS_MODEL,
        "llm_choice": DEFAULT_LLM,
        "custom_query_text": "",
        "query_radio": QUERY_RADIO_OPTIONS[0][0],
        **_RAG_PARAM_DEFAULTS,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _ensure_rag_defaults() -> None:
    """Repair RAG parameters that are missing or out of range (e.g. from a stale session)."""
    checks = {
        "chunk_size": (int, CHUNK_SIZE_RANGE, CHUNK_SIZE),
        "overlap": (int, OVERLAP_RANGE, OVERLAP),
        "top_n": (int, TOP_N_RANGE, TOP_N),
        "threshold": ((int, float), THRESHOLD_RANGE, THRESHOLD),
    }
    for key, (types, (lo, hi, _), default) in checks.items():
        value = st.session_state.get(key)
        if not isinstance(value, types) or not lo <= value <= hi:
            st.session_state[key] = default


_init_state_defaults()

# The header's plain <a href="?restart=1"> link triggers a reset through the query string.
if st.query_params.get("restart") == "1":
    _reset_demo()
    try:
        del st.query_params["restart"]
    except KeyError:
        pass
    st.rerun()


# ---------------------------------------------------------------------------
# API key — environment, then .env in this folder, then the password field. Never shown.
# ---------------------------------------------------------------------------

def _stored_key() -> tuple[str | None, str | None]:
    """(key, where it came from) from the environment or the local .env file."""
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"].strip(), "environment variable"
    key = pipeline.find_api_key()
    return (key, ".env file in the app folder") if key else (None, None)


def _api_key() -> str | None:
    manual = (st.session_state.get("manual_key") or "").strip()
    stored, _ = _stored_key()
    if manual and (st.session_state.get("use_other_key") or not stored):
        return manual
    return stored


def _key_fingerprint() -> str:
    key = _api_key() or ""
    return hashlib.sha256(key.encode()).hexdigest()[:12] if key else ""


def _client():
    return pipeline.make_client(_api_key() or "")


_SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9_\-*]{4,}")


def _redact(message: str) -> str:
    """Strip anything that looks like an API key from an error message before showing it."""
    return _SECRET_PATTERN.sub("sk-(hidden)", message)


# ---------------------------------------------------------------------------
# Small UI helpers
# ---------------------------------------------------------------------------

_NOTICE_ICONS = {"success": "✓", "info": "i", "warning": "!", "error": "✕"}


def _notice(kind: str, body_html: str) -> None:
    st.markdown(
        f'<div class="notice-box notice-{kind}">'
        f'<span class="notice-icon">{_NOTICE_ICONS.get(kind, "i")}</span>'
        f'<span class="notice-text">{body_html}</span></div>',
        unsafe_allow_html=True,
    )


def _field_label(text: str, *, first: bool = False) -> None:
    cls = "field-label first-label" if first else "field-label"
    st.markdown(f'<div class="{cls}">{html.escape(text)}</div>', unsafe_allow_html=True)


@contextmanager
def step_card(step_number: int, title: str):
    """A step card: navy header glued onto a bordered container that holds the widgets."""
    with st.container(key=f"card_step_{step_number}"):
        st.markdown(
            f'<div class="demo-card-header">Step {step_number} — {html.escape(title)}</div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            caption = CAPTIONS.get(step_number)
            if caption:
                st.markdown(
                    f'<div class="edu-caption">{html.escape(caption)}</div>',
                    unsafe_allow_html=True,
                )
            yield


def render_header() -> None:
    st.html(
        '<div class="app-header-banner">'
        "<div>"
        '<div class="header-title">Advanced Applications of Generative AI in Actuarial '
        "Science — Case Study 2</div>"
        '<div class="header-subtitle">Market Comparison Using Retrieval-Augmented Generation'
        " · 2025 annual reports of AXA, Generali and Zurich</div>"
        "</div>"
        '<a class="restart-btn" href="?restart=1" target="_self">↻ Restart</a>'
        "</div>"
    )


def _schema_source(label: str) -> str:
    parts = []
    for cls in SCHEMA_CLASSES[label]:
        parts.append((inspect.getcomments(cls) or "") + inspect.getsource(cls).rstrip())
    return "\n\n".join(parts)


def _title_for_label(label: str) -> str:
    return CUSTOM_QUERY_TITLE if label == CUSTOM_QUERY_LABEL else QUERY_SPECS[label].title


def _schema_for_label(label: str):
    return FreeFormAnswer if label == CUSTOM_QUERY_LABEL else QUERY_SPECS[label].schema


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False, max_entries=32)
def _file_info(path_str: str, mtime_ns: int, size: int) -> tuple[str, int]:
    """(sha256, page count) of a file on disk; cached on path, mtime and size."""
    data = Path(path_str).read_bytes()
    return pipeline.sha256_bytes(data), pipeline.pdf_page_count(data)


def _official_documents() -> list[tuple[pipeline.Document, int]]:
    docs = []
    for company in ANNUAL_REPORT_URLS:
        path = pipeline.official_report_path(company)
        if path.is_file():
            stat = path.stat()
            sha, pages = _file_info(str(path), stat.st_mtime_ns, stat.st_size)
            docs.append(
                (pipeline.Document(company, path.name, sha, stat.st_size, path=path), pages)
            )
    return docs


def _uploaded_documents() -> list[tuple[pipeline.Document, int]]:
    info = st.session_state.setdefault("_upload_info", {})
    docs = []
    for f in st.session_state.get("uploaded_pdfs") or []:
        data = f.getvalue()
        if f.file_id not in info:
            try:
                pages = pipeline.pdf_page_count(data)
            except Exception:
                pages = -1
            info[f.file_id] = (pipeline.sha256_bytes(data), pages)
        sha, pages = info[f.file_id]
        docs.append((pipeline.Document(Path(f.name).stem, f.name, sha, len(data), data=data), pages))
    return docs


def _current_documents() -> list[tuple[pipeline.Document, int]]:
    if st.session_state.get("report_source") == SOURCE_UPLOAD:
        return _uploaded_documents()
    return _official_documents()


def _document_list_html(docs: list[tuple[pipeline.Document, int]]) -> str:
    items = []
    for doc, pages in docs:
        pages_str = f"{pages} pages" if pages >= 0 else "unreadable PDF"
        items.append(
            f"<li><strong>{html.escape(doc.company)}</strong> — {html.escape(doc.filename)}, "
            f"{doc.size_bytes / 1e6:.1f} MB · {pages_str}</li>"
        )
    return (
        "<ul style='margin:6px 0 4px 0; padding-left:18px; font-size:0.93rem;'>"
        + "".join(items) + "</ul>"
    )


# ---------------------------------------------------------------------------
# Step 0 — Configuration
# ---------------------------------------------------------------------------

def render_step0() -> None:
    with step_card(0, "Configuration"):
        col_docs, col_models, col_key = st.columns([0.50, 0.27, 0.23], gap="large")

        with col_docs:
            _field_label("Annual reports", first=True)
            st.radio(
                "Annual reports",
                [SOURCE_OFFICIAL, SOURCE_UPLOAD],
                format_func=lambda s: {
                    SOURCE_OFFICIAL: "The three official 2025 reports (AXA, Generali, Zurich)",
                    SOURCE_UPLOAD: "Upload PDFs",
                }[s],
                key="report_source",
                label_visibility="collapsed",
            )
            if st.session_state.report_source == SOURCE_OFFICIAL:
                _render_official_reports()
            else:
                st.file_uploader(
                    "Upload one or more PDF annual reports.",
                    type=["pdf"],
                    accept_multiple_files=True,
                    key="uploaded_pdfs",
                    label_visibility="collapsed",
                )
                docs = _uploaded_documents()
                if docs:
                    st.markdown(_document_list_html(docs), unsafe_allow_html=True)
                else:
                    st.caption("No files selected yet. The company name is taken from the file name.")

        with col_models:
            _field_label("Embedding model", first=True)
            st.radio(
                "Embedding model",
                EMBEDDINGS_MODELS,
                format_func=lambda m: EMBEDDINGS_DISPLAY_NAMES.get(m, m),
                key="embedding_model",
                label_visibility="collapsed",
            )
            st.caption("The generation model is chosen in Step 5.")

        with col_key:
            _render_key_input()

        current = _config_snapshot()
        if st.session_state.get("config_done") and st.session_state.get("_validated_config") != current:
            _reset_from(0)

        can_save = bool(_current_documents()) and bool(_api_key())
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("Save & continue", key="btn_save_config", disabled=not can_save):
            _validate_config()

        if st.session_state.get("config_done"):
            n = len(st.session_state.documents)
            msg = f"Configuration saved: {n} report{'s' if n != 1 else ''}, API key accepted."
            _notice("success", msg)
            missing = st.session_state.get("unavailable_models") or []
            if missing:
                _notice(
                    "warning",
                    "Not available to this key: "
                    + ", ".join(f"<code>{html.escape(m)}</code>" for m in missing),
                )


def _render_official_reports() -> None:
    docs = _official_documents()
    have = {doc.company for doc, _ in docs}
    missing = [c for c in ANNUAL_REPORT_URLS if c not in have]
    if docs:
        st.markdown(_document_list_html(docs), unsafe_allow_html=True)
    if missing:
        _notice(
            "info",
            "Not on this laptop yet: <strong>" + ", ".join(missing) + "</strong>. The button "
            "below downloads the official PDFs once from the insurers' own websites into the "
            "local <code>_local/reports/</code> folder (about 43 MB in total). No report is "
            "shipped with the repository.",
        )
        if st.button("Download the three official reports", key="btn_download"):
            with st.status("Downloading the annual reports ...", expanded=True) as status:
                try:
                    pipeline.download_official_reports(progress=lambda m: status.update(label=m))
                except Exception as exc:
                    status.update(label="Download failed", state="error")
                    _notice(
                        "error",
                        f"Download failed: {html.escape(_redact(str(exc)))}. Check the internet "
                        "connection, or switch to <em>Upload PDFs</em>.",
                    )
                    return
                status.update(label="All three reports downloaded.", state="complete")
            st.rerun()
    else:
        st.caption("Stored locally in _local/reports/ — downloaded from the insurers' websites.")
    with st.expander("Sources"):
        for company, url in ANNUAL_REPORT_URLS.items():
            st.markdown(f"- **{company}** — [{html.escape(url[:60])}...]({url})")


def _render_key_input() -> None:
    _field_label("OpenAI API key", first=True)
    stored, origin = _stored_key()
    if stored:
        _notice("success", f"Found in the {html.escape(origin)}. The value is never shown.")
        st.checkbox("Use a different key for this session", key="use_other_key")
        if not st.session_state.get("use_other_key"):
            return
    st.text_input(
        "OpenAI API key",
        type="password",
        key="manual_key",
        placeholder="sk-...",
        label_visibility="collapsed",
        help="Kept only in this browser session; never written to disk or shown.",
    )


def _config_snapshot() -> tuple:
    return (
        st.session_state.get("report_source"),
        tuple(sorted(doc.sha256 for doc, _ in _current_documents())),
        st.session_state.get("embedding_model"),
        _key_fingerprint(),
    )


def _validate_config() -> None:
    """Check the key with free model look-ups (no tokens are spent)."""
    embedding_model = st.session_state.embedding_model
    with st.spinner("Checking the API key ..."):
        client = _client()
        try:
            client.models.retrieve(embedding_model)
        except openai.AuthenticationError:
            _reset_from(0)
            _notice("error", "The API key was rejected (401). Check it and try again.")
            return
        except Exception as exc:
            _reset_from(0)
            _notice("error", f"Validation failed: {html.escape(_redact(str(exc)))}")
            return
        unavailable = []
        for model_id in LLM_MODELS:
            try:
                client.models.retrieve(model_id)
            except Exception:
                unavailable.append(model_id)

    _reset_from(1)
    st.session_state.documents = [doc for doc, _ in _current_documents()]
    st.session_state.unavailable_models = unavailable
    st.session_state.config_done = True
    st.session_state._validated_config = _config_snapshot()
    st.rerun()


# ---------------------------------------------------------------------------
# Step 1 — Load and chunk
# ---------------------------------------------------------------------------

def render_step1() -> None:
    with step_card(1, "Load & Chunk Documents"):
        _ensure_rag_defaults()
        documents = st.session_state.documents
        embedding_model = st.session_state.embedding_model

        _field_label("Chunking parameters (article: 2,000 characters, 300 overlap)", first=True)
        size_col, overlap_col = st.columns(2, gap="large")
        with size_col:
            st.session_state["chunk_size"] = st.slider(
                "Chunk size (characters)",
                min_value=CHUNK_SIZE_RANGE[0], max_value=CHUNK_SIZE_RANGE[1],
                value=int(st.session_state["chunk_size"]), step=CHUNK_SIZE_RANGE[2],
            )
        with overlap_col:
            st.session_state["overlap"] = st.slider(
                "Overlap (characters)",
                min_value=OVERLAP_RANGE[0], max_value=OVERLAP_RANGE[1],
                value=int(st.session_state["overlap"]), step=OVERLAP_RANGE[2],
            )
        chunk_size, overlap = int(st.session_state.chunk_size), int(st.session_state.overlap)
        invalid = overlap >= chunk_size
        if invalid:
            _notice("warning", "The overlap must be smaller than the chunk size.")

        snapshot = (chunk_size, overlap, embedding_model)
        if st.session_state.get("step1_done") and st.session_state.get("_chunked_with") != snapshot:
            _reset_from(1)

        key = pipeline.cache_key(documents, embedding_model, chunk_size, overlap)

        if not st.session_state.get("step1_done"):
            if pipeline.cache_exists(key):
                meta = pipeline.read_cache_meta(key)
                n_chunks = sum(d.get("chunks", 0) for d in meta.get("documents", []))
                _notice(
                    "info",
                    f"<strong>Embeddings already computed</strong> for these reports with "
                    f"<code>{html.escape(str(meta.get('embedding_model', '?')))}</code>, "
                    f"{meta.get('chunk_size', '?')} / {meta.get('overlap', '?')} characters "
                    f"({n_chunks:,} chunks, {html.escape(str(meta.get('created_at', '?')))}). "
                    "Loading them takes a second; recomputing takes a few minutes and costs "
                    "roughly USD 0.20.",
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Load cached embeddings", key="btn_load_cache", disabled=invalid):
                        _load_from_cache(key, snapshot)
                        st.rerun()
                with c2:
                    if st.button("Recompute fresh", key="btn_recompute", disabled=invalid):
                        if _compute_corpus(documents, embedding_model, chunk_size, overlap, key, snapshot):
                            st.rerun()
            else:
                st.caption(
                    "No embeddings cached for these settings yet: the first run embeds every "
                    "chunk (a few minutes for the three reports, roughly USD 0.20)."
                )
                if st.button("Load & Chunk", key="btn_load_chunk", disabled=invalid):
                    if _compute_corpus(documents, embedding_model, chunk_size, overlap, key, snapshot):
                        st.rerun()

        if st.session_state.get("step1_done"):
            _render_step1_output()


def _load_from_cache(key: str, snapshot: tuple) -> None:
    corpus = pipeline.load_corpus(key)
    st.session_state.corpus = corpus
    st.session_state.cache_loaded_flag = True
    st.session_state._chunked_with = snapshot
    _pick_chunk_preview(corpus)
    st.session_state.step1_done = True


def _compute_corpus(documents, embedding_model, chunk_size, overlap, key, snapshot) -> bool:
    with st.status("Reading PDFs and computing embeddings ...", expanded=True) as status:
        try:
            corpus = pipeline.build_corpus(
                _client(), documents, embedding_model, chunk_size, overlap,
                progress=lambda msg: status.update(label=msg),
            )
        except Exception as exc:
            status.update(label="Embedding failed", state="error")
            _notice("error", f"Embedding failed: {html.escape(_redact(str(exc)))}")
            return False
        status.update(label=f"Done — {len(corpus.chunks):,} chunks embedded.", state="complete")
    try:
        pipeline.save_corpus(corpus, key)
    except Exception as exc:
        _notice("warning", f"Could not save the embeddings cache: {html.escape(str(exc))}")
    st.session_state.corpus = corpus
    st.session_state.cache_loaded_flag = False
    st.session_state._chunked_with = snapshot
    _pick_chunk_preview(corpus)
    st.session_state.step1_done = True
    return True


def _pick_chunk_preview(corpus: pipeline.Corpus) -> None:
    """A fixed (seeded) pair of consecutive chunks from one company."""
    rng = random.Random(SEED)
    companies = sorted(corpus.companies())
    if not companies:
        return
    company = rng.choice(companies)
    n = sum(1 for c in corpus.chunks if c["company"] == company)
    st.session_state.preview_company = company
    st.session_state.preview_start_idx = rng.randint(1, max(1, n - 2)) if n >= 2 else 0


def _render_step1_output() -> None:
    corpus: pipeline.Corpus = st.session_state.corpus
    per_company: dict[str, int] = {}
    for chunk in corpus.chunks:
        per_company[chunk["company"]] = per_company.get(chunk["company"], 0) + 1

    st.markdown(
        f"**Loaded {len(per_company)} reports, {len(corpus.chunks):,} chunks in total** — "
        + " · ".join(f"{c}: {n:,}" for c, n in per_company.items())
    )
    st.caption(
        "Loaded from the local cache (no API calls)." if st.session_state.get("cache_loaded_flag")
        else "Fresh embeddings computed and cached for next time."
    )

    company = st.session_state.get("preview_company")
    rows = [i for i, c in enumerate(corpus.chunks) if c["company"] == company]
    if len(rows) < 2:
        return
    start = min(st.session_state.get("preview_start_idx", 0), len(rows) - 2)
    st.markdown("&nbsp;", unsafe_allow_html=True)
    st.markdown(
        "#### Chunk preview <span style='font-weight:400; font-size:0.95rem;'>&mdash; two "
        f"consecutive chunks from <code>{html.escape(company)}</code>; note the 300-character "
        "overlap</span>",
        unsafe_allow_html=True,
    )
    cols = st.columns(2, gap="large")
    for col, i in zip(cols, rows[start : start + 2]):
        chunk, vector = corpus.chunks[i], corpus.embeddings[i]
        with col:
            st.markdown(f"**Chunk ID:** `{chunk['chunk_id']}` · {len(chunk['text']):,} characters")
            st.markdown(
                f'<div class="chunk-text-box">{html.escape(chunk["text"])}</div>',
                unsafe_allow_html=True,
            )
            first6 = ", ".join(f"{v:+.4f}" for v in vector[:6])
            st.markdown(
                f'<div class="embedding-label">Embedding (first 6 of {len(vector):,} dimensions):</div>'
                f'<div class="embedding-row">[{first6}, ...]</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Step 2 — Select query
# ---------------------------------------------------------------------------

def render_step2() -> None:
    with step_card(2, "Select Query"):
        labels = [opt[0] for opt in QUERY_RADIO_OPTIONS]
        option_to_label = dict(QUERY_RADIO_OPTIONS)
        choice = st.radio("Target aspect", labels, key="query_radio", label_visibility="collapsed")
        selected = option_to_label[choice]

        prompt_col, schema_col = st.columns([0.36, 0.64], gap="large")
        with prompt_col:
            st.markdown("**Extraction prompt**")
            if selected == CUSTOM_QUERY_LABEL:
                st.text_area(
                    "Your query", key="custom_query_text", height=220,
                    placeholder="Describe in plain language what to extract ...",
                    label_visibility="collapsed",
                )
            else:
                st.text_area(
                    "Extraction prompt", value=QUERY_SPECS[selected].extraction_prompt,
                    height=220, disabled=True, label_visibility="collapsed",
                )
        with schema_col:
            st.markdown("**Pydantic output schema**")
            st.code(_schema_source(selected), language="python")
            if selected == CUSTOM_QUERY_LABEL:
                st.caption("Custom queries return a free-text `answer`, still via Structured Outputs.")

        with st.expander("Show system prompt"):
            st.code(SYSTEM_PROMPT, language="text")

        current = (selected, st.session_state.get("custom_query_text", ""))
        if st.session_state.get("step2_done") and st.session_state.get("_confirmed_query") != current:
            _reset_from(2)

        custom_empty = selected == CUSTOM_QUERY_LABEL and not st.session_state.custom_query_text.strip()
        if st.button("Confirm query", key="btn_confirm_query", disabled=custom_empty):
            st.session_state.query_label = selected
            st.session_state.extraction_prompt_text = (
                st.session_state.custom_query_text.strip() if selected == CUSTOM_QUERY_LABEL
                else QUERY_SPECS[selected].extraction_prompt
            )
            st.session_state.step2_done = True
            st.session_state._confirmed_query = current
            _reset_from(3)
            st.rerun()

        if st.session_state.get("step2_done"):
            _notice("success", "Query confirmed.")


# ---------------------------------------------------------------------------
# Step 3 — Retrieve
# ---------------------------------------------------------------------------

def render_step3() -> None:
    with step_card(3, "Retrieve Relevant Chunks"):
        _ensure_rag_defaults()
        _field_label("Retrieval parameters (article: top 10, threshold 0.30)", first=True)
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.session_state["top_n"] = st.slider(
                "Top-N chunks per company",
                min_value=TOP_N_RANGE[0], max_value=TOP_N_RANGE[1],
                value=int(st.session_state["top_n"]), step=TOP_N_RANGE[2],
            )
        with c2:
            st.session_state["threshold"] = st.slider(
                "Similarity threshold",
                min_value=float(THRESHOLD_RANGE[0]), max_value=float(THRESHOLD_RANGE[1]),
                value=float(st.session_state["threshold"]), step=float(THRESHOLD_RANGE[2]),
            )
        params = (int(st.session_state.top_n), round(float(st.session_state.threshold), 4))
        if st.session_state.get("step3_done") and st.session_state.get("_retrieved_with") != params:
            st.caption("Retrieval parameters changed — click **Re-retrieve** to refresh.")

        label = "Re-retrieve" if st.session_state.get("step3_done") else "Retrieve"
        if st.button(label, key="btn_retrieve"):
            if _run_retrieval(*params):
                st.rerun()

        if st.session_state.get("step3_done"):
            _render_retrieval_output()


def _run_retrieval(top_n: int, threshold: float) -> bool:
    corpus: pipeline.Corpus = st.session_state.corpus
    with st.spinner("Embedding the query and scoring every chunk ..."):
        try:
            query_embedding = pipeline.embed_query(
                _client(), st.session_state.embedding_model, st.session_state.extraction_prompt_text
            )
        except Exception as exc:
            _notice("error", f"Query embedding failed: {html.escape(_redact(str(exc)))}")
            return False
        retrieved = {
            company: pipeline.retrieve_top_chunks(corpus, company, query_embedding, top_n, threshold)
            for company in corpus.companies()
        }
    _reset_from(3)
    st.session_state.retrieved = retrieved
    st.session_state._retrieved_with = (top_n, threshold)
    st.session_state.step3_done = True
    return True


def _ramp_colour(t: float) -> str:
    t = max(0.0, min(1.0, t))
    pos = t * (len(SIMILARITY_RAMP) - 1)
    i = min(int(pos), len(SIMILARITY_RAMP) - 2)
    frac = pos - i
    c1 = [int(SIMILARITY_RAMP[i][j : j + 2], 16) for j in (1, 3, 5)]
    c2 = [int(SIMILARITY_RAMP[i + 1][j : j + 2], 16) for j in (1, 3, 5)]
    r, g, b = (int(a + (b - a) * frac) for a, b in zip(c1, c2))
    return f"#{r:02x}{g:02x}{b:02x}"


PREVIEW_CHAR_LIMIT = 750
_TD = "padding:8px 10px; vertical-align:top;"
_TH = "padding:8px 10px; text-align:left; font-weight:700; border-bottom:1px solid #D5DEEA;"


def _retrieval_table_html(chunks: list[dict], threshold: float) -> str:
    span = max(0.05, 1.0 - threshold)
    rows = []
    for rank, c in enumerate(chunks, start=1):
        t = max(0.0, min(1.0, (c["similarity"] - threshold) / span * 2.0))
        text_colour = "#FFFFFF" if t >= 0.5 else "#0F2B72"
        snippet = html.escape(c["text"][:PREVIEW_CHAR_LIMIT]) + (
            " ..." if len(c["text"]) > PREVIEW_CHAR_LIMIT else ""
        )
        rows.append(
            "<tr>"
            f'<td style="{_TD} font-weight:600; width:50px;">{rank}</td>'
            f'<td style="{_TD} font-family:monospace; white-space:nowrap; width:130px;">'
            f'{html.escape(c["chunk_id"])}</td>'
            f'<td style="{_TD} width:20%;"><div style="background:{_ramp_colour(t)}; '
            f"width:{max(18, int(t * 100))}%; min-width:60px; padding:4px 8px; "
            f'color:{text_colour}; font-weight:600; font-size:0.85rem;">{c["similarity"]:.3f}'
            "</div></td>"
            f'<td style="{_TD} font-size:0.85rem; line-height:1.4; white-space:pre-wrap;">{snippet}</td>'
            "</tr>"
        )
    return (
        '<table class="retrieval-table" style="width:100%; border-collapse:collapse; '
        'font-size:0.9rem; border:1px solid #D5DEEA; color:#0F2B72;">'
        '<thead><tr style="background:#F3F6FA;">'
        f'<th style="{_TH}">Rank</th><th style="{_TH}">Chunk ID</th>'
        f'<th style="{_TH}">Similarity</th><th style="{_TH}">Preview</th>'
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def _render_retrieval_output() -> None:
    retrieved = st.session_state.retrieved
    threshold = st.session_state._retrieved_with[1]
    companies = list(retrieved)
    for tab, company in zip(st.tabs(companies), companies):
        with tab:
            chunks = retrieved[company]
            if not chunks:
                _notice("warning", "No chunk passed the similarity threshold.")
                continue
            st.html(_retrieval_table_html(chunks, threshold))
            with st.expander("Show full chunk texts"):
                for rank, chunk in enumerate(chunks, start=1):
                    st.markdown(f"**[{rank}] {chunk['chunk_id']}** — similarity {chunk['similarity']:.3f}")
                    st.markdown(
                        f'<div class="chunk-text-box">{html.escape(chunk["text"])}</div>',
                        unsafe_allow_html=True,
                    )


# ---------------------------------------------------------------------------
# Step 4 — Augmented prompt
# ---------------------------------------------------------------------------

def render_step4() -> None:
    with step_card(4, "Preview Augmented Prompt"):
        if not st.session_state.get("step4_done"):
            if st.button("Assemble prompt", key="btn_assemble"):
                _assemble_prompts()
                st.rerun()
        else:
            _render_step4_output()


def _assemble_prompts() -> None:
    label = st.session_state.query_label
    topic = _title_for_label(label)
    prompts, tokens = {}, {}
    for company, chunks in st.session_state.retrieved.items():
        user_prompt = pipeline.build_user_prompt(
            company, topic, st.session_state.extraction_prompt_text, chunks
        )
        prompts[company] = user_prompt
        tokens[company] = pipeline.count_tokens(SYSTEM_PROMPT + "\n\n" + user_prompt)
    _reset_from(4)
    st.session_state.user_prompts = prompts
    st.session_state.prompt_token_counts = tokens
    st.session_state.step4_done = True


def _section_block(label: str, body: str) -> str:
    return (
        f'<div class="prompt-section-bar">{html.escape(label)}</div>'
        f'<pre class="prompt-section-body">{html.escape(body)}</pre>'
    )


def _render_step4_output() -> None:
    label = st.session_state.query_label
    topic = _title_for_label(label)
    companies = list(st.session_state.user_prompts)
    for tab, company in zip(st.tabs(companies), companies):
        with tab:
            chunks = st.session_state.retrieved.get(company, [])
            instruction = USER_PROMPT_TEMPLATE.split("{context}")[0].format(
                company=company, topic=topic,
                extraction_prompt=st.session_state.extraction_prompt_text,
            ).rstrip()
            st.html(
                _section_block("SYSTEM PROMPT", SYSTEM_PROMPT)
                + _section_block("USER PROMPT — INSTRUCTION", instruction)
                + _section_block(
                    f"USER PROMPT — RETRIEVED CONTEXT ({len(chunks)} CHUNKS)",
                    pipeline.render_context(chunks) or "(no chunk passed the threshold)",
                )
            )
            count, exact = st.session_state.prompt_token_counts[company]
            c1, c2 = st.columns(2)
            c1.metric(
                "Prompt size in tokens" + ("" if exact else " (rough estimate)"),
                f"{count:,}",
                help="Counted with the o200k_base tokeniser; the exact count is reported "
                "by the API in Step 5.",
            )
            c2.metric("Retrieved chunks", f"{len(chunks)}")


# ---------------------------------------------------------------------------
# Step 5 — Generate
# ---------------------------------------------------------------------------

def render_step5() -> None:
    with step_card(5, "Generate Structured Answer"):
        unavailable = set(st.session_state.get("unavailable_models") or [])
        _field_label("Generation model", first=True)
        st.radio(
            "Generation model",
            list(LLM_MODELS),
            format_func=lambda m: (
                f"{LLM_MODELS[m].label} ({m}) — {LLM_MODELS[m].note}"
                + ("  [not available to this key]" if m in unavailable else "")
            ),
            key="llm_choice",
            label_visibility="collapsed",
        )
        model_id = st.session_state.llm_choice
        if st.button(f"Generate with {LLM_MODELS[model_id].label}", key="btn_generate"):
            _run_generation(model_id)
            st.rerun()
        if st.session_state.get("step5_done"):
            _render_step5_output()


def _generate_one(api_key: str, model_id: str, schema, user_prompt: str) -> pipeline.Generation:
    """Runs in a worker thread — no Streamlit calls in here."""
    return pipeline.generate_structured(pipeline.make_client(api_key), model_id, schema, user_prompt)


def _run_generation(model_id: str) -> None:
    label = st.session_state.query_label
    schema = _schema_for_label(label)
    prompts: dict[str, str] = st.session_state.user_prompts
    api_key = _api_key() or ""
    results: dict[str, dict] = {}

    progress = st.progress(0.0, text=f"Calling {model_id} for {len(prompts)} companies in parallel ...")
    with ThreadPoolExecutor(max_workers=max(1, len(prompts))) as pool:
        futures = {
            pool.submit(_generate_one, api_key, model_id, schema, prompt): company
            for company, prompt in prompts.items()
        }
        for done, future in enumerate(as_completed(futures), start=1):
            company = futures[future]
            try:
                gen = future.result()
                results[company] = {
                    "summary": pipeline.summarise_result(label, gen.parsed) if gen.parsed else None,
                    "raw_json": json.dumps(gen.parsed.model_dump(), indent=2, ensure_ascii=False)
                    if gen.parsed else None,
                    "error": gen.error,
                    "seconds": gen.seconds,
                    "input_tokens": gen.input_tokens,
                    "output_tokens": gen.output_tokens,
                    "temperature": gen.temperature,
                    "note": gen.note,
                }
            except Exception as exc:
                results[company] = {"error": _redact(f"{type(exc).__name__}: {exc}")}
            progress.progress(done / len(futures), text=f"{company} done ({done}/{len(futures)})")
    progress.empty()

    st.session_state.results = {c: results[c] for c in prompts}  # keep the corpus order
    st.session_state._generated_with = (model_id, label)
    st.session_state.step5_done = True


def _render_step5_output() -> None:
    model_id, _ = st.session_state._generated_with
    spec = LLM_MODELS.get(model_id)
    st.markdown(f"#### Results — {html.escape(spec.label if spec else model_id)} ({html.escape(model_id)})")
    if model_id != st.session_state.llm_choice:
        st.caption("These results are from the previously selected model; click Generate to run the new one.")
    results = st.session_state.results
    companies = list(results)
    per_row = min(len(companies), 3) or 1
    for start in range(0, len(companies), per_row):
        cols = st.columns(per_row, gap="large")
        for col, company in zip(cols, companies[start : start + per_row]):
            r = results[company]
            with col:
                st.markdown(f"### {company}")
                if r.get("error") and not r.get("summary"):
                    _notice("error", html.escape(r["error"]))
                    continue
                st.markdown(f'<div class="summary-line">{html.escape(r["summary"])}</div>',
                            unsafe_allow_html=True)
                temp = "temperature 0" if r.get("temperature") is not None else "no temperature sent"
                usage = (
                    f"{r['input_tokens']:,} tokens in, {r['output_tokens']:,} out · "
                    if r.get("input_tokens") is not None else ""
                )
                st.caption(f"{usage}{r['seconds']:.1f} s · {temp}"
                           + (f" · {r['note']}" if r.get("note") else ""))
                with st.expander("Show raw JSON"):
                    st.code(r["raw_json"], language="json")


# ---------------------------------------------------------------------------
# Main flow — each step appears once the previous one is done
# ---------------------------------------------------------------------------

render_header()
render_step0()
if st.session_state.get("config_done"):
    render_step1()
if st.session_state.get("step1_done"):
    render_step2()
if st.session_state.get("step2_done"):
    render_step3()
if st.session_state.get("step3_done"):
    render_step4()
if st.session_state.get("step4_done"):
    render_step5()
