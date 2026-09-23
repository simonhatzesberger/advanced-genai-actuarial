# Case Study 2 — live demo: market comparison with retrieval-augmented generation

A step-by-step Streamlit app that runs the article's three-stage RAG pipeline in front of the
room. It extracts three aspects from the 2025 annual reports of AXA, Generali and Zurich:

- the group solvency capital ratio;
- the EUR discount curve;
- the insurer financial strength ratings.

It is the interactive companion to the notebook
[`notebooks/04_cs2_rag_market_comparison`](../../notebooks/04_cs2_rag_market_comparison/04_cs2_rag_market_comparison.ipynb).
Both use the same extraction prompts and Pydantic schemas: the article's, copied verbatim. They also use the same retrieval settings:

| Setting | Value |
|---|---|
| Chunk size | 2,000 characters |
| Overlap | 300 characters |
| Chunks retrieved per company | top 10 |
| Similarity threshold | 0.30 |
| Embedding model | `text-embedding-3-large` |

---

## What the app shows, step by step

| Step | What happens on screen |
|---|---|
| **0 — Configuration** | Pick the reports: either **download the three official 2025 reports** with one click, or upload your own PDFs. The app confirms that an OpenAI key is available. |
| **1 — Load & chunk** *(Stage 1, preprocessing)* | PDF → cleaned text → overlapping 2,000-character chunks → one embedding vector per chunk. Two consecutive chunks are shown side by side, so the overlap and the first vector dimensions are visible. Embeddings come from a local cache when one exists, so this takes a second. |
| **2 — Select query** | Choose one of the article's three aspects, or type your own question. The extraction prompt and its Pydantic schema are shown side by side. |
| **3 — Retrieve** *(Stage 2, prompt augmenting)* | The prompt is embedded and compared with every chunk by cosine similarity. The top 10 chunks per company above 0.30 are shown, with a similarity bar for each. The sliders let you change top-N and the threshold live. |
| **4 — Augmented prompt** | Shows exactly what goes to the model: the system prompt, the instruction and the retrieved context, with a token count. |
| **5 — Generate** *(Stage 3, response generation)* | Pick the generation model and run one Structured Outputs call per company, all three in parallel. Each company gets a card with a one-line summary, the raw JSON, the tokens used and the time taken. Switching the model re-runs only this step, on the same retrieved context. |

**Generation models offered.** Pick one in Step 5:

| Model | Temperature |
|---|---|
| `gpt-6-luna` (default) | None sent. The app leaves the model at its default reasoning effort, `medium`, at which it rejects the parameter; it accepts one only at effort `none`. |
| `gpt-5.4-mini-2026-03-17` | 0, the article's setting |
| `gpt-5.4-2026-03-05` | 0, the article's setting |

---

## Setup (once, before the session)

From this folder:

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` holds only what this app needs. Its pins match the repository's root
`requirements.txt`, plus `streamlit`, so you can also install it into the repository's
environment.

### One key: `OPENAI_API_KEY`

The app needs **one OpenAI key and nothing else**: the same key serves the embeddings and the
generation model. This matches the seminar notebooks.

The app looks for the key in this order:

1. The environment variable `OPENAI_API_KEY`.
2. A `.env` file in this folder. Copy `.env.example` to `.env` and fill it in. `.env` is
   git-ignored.
3. A password field in Step 0. Whatever you type there lives only in the browser session.

The key is never displayed, logged or written to disk by the app. Step 0 checks the key with
free model look-ups, so the check spends no tokens.

### Optional: prepare the laptop in advance

```bash
python pipeline.py
```

This downloads the three reports into `_local/reports/` and builds the embeddings cache in
`_local/embeddings_cache/`. It takes about a minute and costs roughly USD 0.20 in embeddings.
Afterwards Step 1 loads instantly. You can do the same from inside the app instead: use the
download button in Step 0, then **Load & Chunk** in Step 1.

---

## Starting it in the room

```bash
cd apps/cs2_market_comparison
streamlit run app.py
```

The app opens at <http://localhost:8501>. `python app.py` works too: it changes into this folder
and starts Streamlit for you.

Start it **from this folder**. Streamlit reads the seminar theme from `.streamlit/config.toml`
in the folder it is started from.

**Restart** in the header resets the demo. The downloaded reports, the cache and the key are
kept, so you do not need to download or embed again.

**Cost of one full live run** (three companies, one aspect, `gpt-6-luna`): about 15,000 input
tokens, i.e. well under one US cent.

---

## The annual reports are not redistributed

This repository contains **no annual report**, in PDF or any other form. With the download
option, your laptop fetches each report directly from the insurer's own website, using the same
URLs as the article's research notebook. The files are stored only in the local `_local/`
folder, which is git-ignored. The URLs are listed in `config.py` (`ANNUAL_REPORT_URLS`) and under
**Sources** in Step 0.

If a URL stops working, download the PDF by hand and use **Upload PDFs** in Step 0. The company
name is taken from the file name.

---

## Files

```
app.py              Streamlit interface (Steps 0-5)
pipeline.py         the RAG pipeline itself: plain openai SDK, no Streamlit; `python pipeline.py` prepares the cache
config.py           retrieval constants, report URLs, models, the article's prompts and schemas, CSS
requirements.txt    pinned dependencies for this app only
.streamlit/         the seminar theme
.env.example        template for the local key file
.gitignore          keeps _local/, .env and __pycache__/ out of git
_local/             created on first use: reports/ and embeddings_cache/ (never committed)
```

The embeddings cache is a NumPy `.npz` file of vectors plus a `.json` file of chunk texts; it
does not use pickle. Its file name is a hash of:

- the reports' contents;
- the embedding model;
- the chunk size and overlap.

A different setting builds a new cache and leaves the existing one untouched. To clear the
cache, delete `_local/embeddings_cache/`.

---

## Troubleshooting

- **"The API key was rejected"**: check `OPENAI_API_KEY`, or tick *Use a different key for this
  session* in Step 0.
- **A model shows "not available to this key"**: the key's project has no access to that model.
  Pick another model in Step 5.
- **The download fails**: check the network. If a URL has moved, download the report by hand and
  upload it.
- **A step shows nothing after you changed an earlier one**: this is expected. Later steps are
  cleared whenever an earlier input changes; click that step's button again.
- **The theme is red instead of cyan**: Streamlit was started from another folder. Start it from
  this folder.
