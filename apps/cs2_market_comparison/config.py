"""Static configuration for the Case Study 2 live demo (market comparison with RAG).

Holds the retrieval constants, the report sources, the model registry, the prompts, the
Pydantic output schemas, the step captions and the page CSS.

The three extraction prompts and the five Pydantic schemas are copied verbatim from the
article (Hatzesberger & Nonneman 2026, European Actuarial Journal, Case Study 2), which is
also what the seminar notebook `04_cs2_rag_market_comparison` uses.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Paths — everything machine-local lives in _local/, which is git-ignored
# ---------------------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
LOCAL_DIR = APP_DIR / "_local"
REPORTS_DIR = LOCAL_DIR / "reports"
CACHE_DIR = LOCAL_DIR / "embeddings_cache"


# ---------------------------------------------------------------------------
# Retrieval constants (article, Stages 1 and 2)
# ---------------------------------------------------------------------------

CHUNK_SIZE = 2000          # maximum characters per chunk
OVERLAP = 300              # characters of overlap between consecutive chunks
TOP_N = 10                 # chunks retrieved per company
THRESHOLD = 0.30           # minimum cosine similarity
SEED = 42                  # fixes which two chunks the Step 1 preview shows

# Slider ranges exposed in the UI (min, max, step).
CHUNK_SIZE_RANGE = (500, 4000, 100)
OVERLAP_RANGE = (0, 800, 50)
TOP_N_RANGE = (1, 25, 1)
THRESHOLD_RANGE = (0.0, 1.0, 0.05)

DEFAULT_EMBEDDINGS_MODEL = "text-embedding-3-large"
EMBEDDINGS_MODELS = ["text-embedding-3-large", "text-embedding-3-small"]
EMBEDDINGS_DISPLAY_NAMES = {
    "text-embedding-3-large": "text-embedding-3-large (as in the article)",
    "text-embedding-3-small": "text-embedding-3-small (needs a fresh embedding run)",
}


# ---------------------------------------------------------------------------
# The three official 2025 annual reports — downloaded on demand, never bundled
# (same URLs as the article's research notebook)
# ---------------------------------------------------------------------------

ANNUAL_REPORT_URLS = {
    "AXA": "https://www-axa-com.cdn.prismic.io/www-axa-com/ab1gEB5fn6DF3CqE_axa_urd2025_accessible_va.pdf",
    "Generali": "https://www.generali.com/doc/jcr:b569c750-290c-4868-9b6f-655e0349451c/Annual%20Integrated%20Report%20and%20Consolidated%20Financial%20Statements%202025_Generali%20Group_final.pdf/lang:en/Annual_Integrated_Report_and_Consolidated_Financial_Statements_2025_Generali_Group_final.pdf",
    "Zurich": "https://edge.sitecorecloud.io/zurichinsur6934-zwpcorp-prod-ae5e/media/project/zurich/dotcom/investor-relations/docs/financial-reports/2025/annual-report-2025-en.pdf",
}

# Some of these hosts refuse requests without a browser-like User-Agent.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Generation models — one OpenAI key covers everything
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    label: str
    accepts_temperature: bool
    note: str


TEMPERATURE = 0.0  # the article's setting, sent only to models that accept it

LLM_MODELS: dict[str, ModelSpec] = {
    spec.model_id: spec
    for spec in (
        ModelSpec(
            "gpt-6-luna",
            "GPT-6 Luna",
            accepts_temperature=False,  # at the app's setting: default reasoning effort, medium
            note="default · rejects temperature at its default reasoning effort, so none is sent",
        ),
        ModelSpec(
            "gpt-5.4-mini-2026-03-17",
            "GPT-5.4 mini",
            accepts_temperature=True,
            note="temperature 0, as in the article",
        ),
        ModelSpec(
            "gpt-5.4-2026-03-05",
            "GPT-5.4",
            accepts_temperature=True,
            note="temperature 0, as in the article",
        ),
    )
}
DEFAULT_LLM = "gpt-6-luna"


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an AI assistant specialized in extracting and structuring key financial\n"
    "and risk insights from annual reports of European insurance companies. Use RAG\n"
    "to retrieve precise text segments and apply Structured Outputs to format data\n"
    "consistently. Identify and extract regulatory ratios, discount rates, and cyber\n"
    "risk strategies with exact numerical formats and contextual clarity. Ensure all\n"
    "outputs follow the specified schema for seamless integration into actuarial\n"
    "workflows and to support robust comparative analysis."
)

USER_PROMPT_TEMPLATE = (
    "Company: {company}\n"
    "Target topic: {topic}\n"
    "\n"
    "Extraction instruction:\n"
    "{extraction_prompt}\n"
    "\n"
    "Additional guidance:\n"
    "- Use only the retrieved context below.\n"
    "- If the information is not clearly stated, do not guess.\n"
    "- Return the requested schema only.\n"
    "\n"
    "Retrieved context:\n"
    "{context}"
)


def _one_paragraph(text: str) -> str:
    """Collapse the article listing's page-width line breaks into one paragraph."""
    return " ".join(text.split())


# The three extraction prompts, verbatim from the article's listing. Each prompt is used
# twice: embedded to retrieve context, and sent to the model as the extraction instruction.

# Prompt for solvency capital ratios
prompt_solvency = _one_paragraph("""
    Extract the group's solvency capital ratio in percentage for 2025, together with the regulatory
    framework (Solvency II or SST).
""")

# Prompt for discount rates
prompt_discount_rates = _one_paragraph("""
    Extract the discount rates for financial or insurance contract liabilities in 2025, using only
    currency EUR. For each duration (e.g., 1 year, 5 years, 10 years, 20 years, 40 years, etc.),
    extract the corresponding discount rate in percentage. Ensure that the data reflects the rates
    as of December 31, 2025. If no specific approach is mentioned, assume non-VFA, unit-linked
    contracts, or liquid products.
""")

# Prompt for insurer financial strength ratings
prompt_ratings = _one_paragraph("""
    Extract insurer financial strength ratings (IFSR) as a list of entries with rater (e.g., AM
    Best, Fitch, Moody's, and S&P), rating, and outlook (stable, positive, or negative).
""")


# ---------------------------------------------------------------------------
# Pydantic output schemas — verbatim from the article's listing
# ---------------------------------------------------------------------------

# Solvency capital ratio schema: percentage and regulatory framework
class SolvencyResult(BaseModel):
    capital_ratio: int          # solvency ratio in %
    regulatory_framework: Literal["Solvency II", "SST"]

# Discount rate for a specific duration
class DiscountRatePoint(BaseModel):
    duration_year: int            # duration in years
    discount_rate_percent: float  # rate in percentage (e.g., 2.47)

# Aggregate discount rates across durations
class DiscountCurveResult(BaseModel):
    currency: Literal["EUR"]
    rates: List[DiscountRatePoint]  # list by duration

# Individual financial strength rating entry
class FinancialStrengthRating(BaseModel):
    rater: str                  # e.g., "S&P Global Ratings", "Moody's"
    rating: str                 # e.g., "AA-", "Aa3", "A+ Superior"
    outlook: Optional[str]      # e.g., "Stable", "Positive"

# Aggregate financial strength ratings
class FinancialStrengthRatingsResult(BaseModel):
    ratings: List[FinancialStrengthRating]


# Fallback schema for the demo's free-text "custom query" option (not part of the article).
class FreeFormAnswer(BaseModel):
    answer: str = Field(
        description="A direct answer to the user's query, grounded in the retrieved context."
    )


# ---------------------------------------------------------------------------
# Query registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QuerySpec:
    label: str
    title: str
    extraction_prompt: str
    schema: type[BaseModel]


QUERY_SPECS: dict[str, QuerySpec] = {
    "solvency_ratio": QuerySpec(
        "solvency_ratio", "2025 solvency position", prompt_solvency, SolvencyResult
    ),
    "discount_rates": QuerySpec(
        "discount_rates",
        "EUR discount curve used for liabilities",
        prompt_discount_rates,
        DiscountCurveResult,
    ),
    "financial_strength_ratings": QuerySpec(
        "financial_strength_ratings",
        "Insurer financial strength ratings by agency",
        prompt_ratings,
        FinancialStrengthRatingsResult,
    ),
}

# The schema classes shown next to each query in Step 2.
SCHEMA_CLASSES: dict[str, list[type[BaseModel]]] = {
    "solvency_ratio": [SolvencyResult],
    "discount_rates": [DiscountRatePoint, DiscountCurveResult],
    "financial_strength_ratings": [FinancialStrengthRating, FinancialStrengthRatingsResult],
}

CUSTOM_QUERY_LABEL = "custom"
CUSTOM_QUERY_TITLE = "Custom user query"
SCHEMA_CLASSES[CUSTOM_QUERY_LABEL] = [FreeFormAnswer]

QUERY_RADIO_OPTIONS = [
    ("Aspect 1: Solvency capital ratio (2025)", "solvency_ratio"),
    ("Aspect 2: EUR discount curve (31 Dec 2025)", "discount_rates"),
    ("Aspect 3: Insurer financial strength ratings", "financial_strength_ratings"),
    ("Custom query ...", CUSTOM_QUERY_LABEL),
]


# ---------------------------------------------------------------------------
# Captions shown under each step header
# ---------------------------------------------------------------------------

CAPTIONS = {
    0: (
        "Choose the annual reports to compare and supply one OpenAI API key. The same key "
        "covers the embeddings (Stages 1 and 2) and the generation model (Stage 3)."
    ),
    1: (
        "Stage 1 — Preprocessing. Each PDF is read with PyMuPDF, its whitespace is cleaned, "
        "the text is cut into overlapping character chunks, and every chunk is turned into a "
        "high-dimensional vector by the embedding model. The result is a searchable index of "
        "company, chunk and vector, kept in memory."
    ),
    2: (
        "Each aspect has one extraction prompt and one Pydantic schema. The prompt is used "
        "twice: embedded to find relevant context, then sent to the model as the instruction. "
        "The schema is the contract the answer must satisfy — Structured Outputs guarantees "
        "that the reply validates against it."
    ),
    3: (
        "Stage 2 — Prompt augmenting. The extraction prompt is embedded with the same model, "
        "compared with every chunk of each report by cosine similarity, and the top-N chunks "
        "above the threshold are kept. Darker bars mean a stronger semantic match."
    ),
    4: (
        "The system prompt sets the role, the user prompt restates what to find, and the "
        "retrieved chunks are the only evidence the model may use. This is exactly what is sent, "
        "with an estimate of its size in tokens (a proxy for cost and context-window use)."
    ),
    5: (
        "Stage 3 — Response generation. Only this stage depends on the model you pick; the "
        "retrieval above stays fixed. Each company's augmented prompt goes to the model with "
        "Structured Outputs, so the reply is JSON that validates against the schema — no "
        "regular expressions or string parsing downstream."
    ),
}


# ---------------------------------------------------------------------------
# Colours — seminar palette
# ---------------------------------------------------------------------------

COLOR_CYAN = "#009CDB"         # EAA cyan (primary accent)
COLOR_NAVY = "#0F2B72"         # EAA navy (text, header)
COLOR_CYAN_LIGHT = "#E6F5FB"
COLOR_BORDER = "#D5DEEA"
COLOR_PRIMARY = COLOR_CYAN
COLOR_PRIMARY_DARK = COLOR_NAVY

# Similarity-bar colour ramp: pale cyan -> cyan -> navy.
SIMILARITY_RAMP = ["#F2FAFD", "#B3E1F4", COLOR_CYAN, "#0A63A8", COLOR_NAVY]


# ---------------------------------------------------------------------------
# CSS — injected once per run
# ---------------------------------------------------------------------------

CSS = f"""
/* ---------- Global: navy text on white ---------- */
html, body, [class*="css"] {{
    font-size: 15px;
}}
.stApp {{
    background-color: #FFFFFF;
    color: {COLOR_NAVY};
}}
.stApp p, .stApp span, .stApp label, .stApp div,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp .stMarkdown {{
    color: {COLOR_NAVY};
}}

/* Square corners on cards, buttons, inputs, code blocks and notices. */
.stButton > button,
.stApp input[type="text"],
.stApp input[type="password"],
.stApp textarea,
.stApp div[data-baseweb="input"],
.stApp div[data-baseweb="textarea"],
.stApp div[data-baseweb="select"] > div,
.demo-card-header,
.embedding-row,
.chunk-text-box,
.prompt-section-bar,
.prompt-section-body,
[class*="st-key-card_step_"] div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stCodeBlock"] pre,
details[data-testid="stExpander"],
details[data-testid="stExpander"] summary,
div[data-testid="stAlertContainer"],
.notice-box,
.retrieval-table {{
    border-radius: 0 !important;
}}

/* Hide Streamlit's toolbar (Deploy, menu) and the empty sidebar gutter. */
#MainMenu, footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ display: none !important; }}
[data-testid="stAppDeployButton"], .stAppDeployButton {{ display: none !important; }}
section[data-testid="stSidebar"] {{ display: none !important; }}
div[data-testid="collapsedControl"] {{ display: none !important; }}
.stApp [data-testid="stAppViewBlockContainer"],
.stApp [data-testid="stMainBlockContainer"] {{
    padding-top: 1.4rem !important;
}}

/* ---------- Inputs ---------- */
.stApp input[type="text"],
.stApp input[type="password"],
.stApp textarea,
.stApp div[data-baseweb="input"] input,
.stApp div[data-baseweb="textarea"] textarea,
.stApp div[data-baseweb="select"] > div {{
    background-color: #FFFFFF !important;
    color: {COLOR_NAVY} !important;
    border: 1px solid {COLOR_BORDER} !important;
}}
.stApp ::placeholder {{
    color: #7A8AA8 !important;
    opacity: 1 !important;
}}
.stApp textarea:disabled,
.stApp textarea[disabled] {{
    color: {COLOR_NAVY} !important;
    -webkit-text-fill-color: {COLOR_NAVY} !important;
    background-color: #F5F8FC !important;
    opacity: 1 !important;
}}
.stApp div[data-testid="stFileUploader"] section {{
    background-color: #FFFFFF !important;
    border: 1px dashed #8FA3C4 !important;
}}

/* ---------- Buttons: cyan, navy on hover. White on the button and every child,
              so Streamlit's inner <p> cannot inherit the navy text colour. ---------- */
.stApp .stButton > button,
.stApp .stButton > button * {{
    color: #FFFFFF !important;
}}
.stApp .stButton > button {{
    background-color: {COLOR_PRIMARY} !important;
    border: 0 !important;
    font-weight: 600 !important;
    padding: 8px 18px !important;
}}
.stApp .stButton > button:hover {{
    background-color: {COLOR_PRIMARY_DARK} !important;
}}
.stApp .stButton > button:disabled,
.stApp .stButton > button:disabled * {{
    background-color: #D0D6E0 !important;
    color: #6B7890 !important;
}}

/* ---------- Radio, checkbox and slider accents (independent of config.toml) ---------- */
input[type="radio"], input[type="checkbox"] {{
    accent-color: {COLOR_PRIMARY} !important;
}}
label[data-baseweb="radio"]:has(input:checked) > div:first-child {{
    background-color: {COLOR_PRIMARY} !important;
    border-color: {COLOR_PRIMARY} !important;
}}
label[data-baseweb="radio"]:has(input:checked) > div:first-child > div {{
    background-color: #FFFFFF !important;
}}
div[role="radiogroup"] > label {{ margin-bottom: 4px; }}
div[data-baseweb="slider"] [role="slider"] {{
    background-color: {COLOR_PRIMARY} !important;
    border-color: {COLOR_PRIMARY} !important;
}}

/* ---------- App header: navy banner, plain text, restart link ---------- */
.stApp .app-header-banner {{
    background: {COLOR_NAVY};
    border-bottom: 4px solid {COLOR_CYAN};
    padding: 18px 24px;
    margin-bottom: 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
}}
.stApp .app-header-banner,
.stApp .app-header-banner * {{
    color: #FFFFFF !important;
}}
.stApp .app-header-banner .header-title {{
    font-size: 1.35rem;
    font-weight: 700;
    line-height: 1.3;
}}
.stApp .app-header-banner .header-subtitle {{
    font-size: 0.95rem;
    opacity: 0.85;
    margin-top: 3px;
    line-height: 1.4;
}}
.stApp .app-header-banner .restart-btn {{
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.55);
    padding: 8px 18px;
    font-weight: 600;
    font-size: 0.95rem;
    text-decoration: none !important;
    white-space: nowrap;
}}
.stApp .app-header-banner .restart-btn:hover {{
    background: rgba(255, 255, 255, 0.10);
}}

/* ---------- Step cards: navy header with a cyan edge ---------- */
.demo-card-header {{
    background: {COLOR_NAVY};
    border-left: 6px solid {COLOR_CYAN};
    padding: 10px 18px;
    font-weight: 600;
    font-size: 1.05rem;
    margin-bottom: -1px;
}}
.demo-card-header, .demo-card-header * {{
    color: #FFFFFF !important;
}}
.stApp [class*="st-key-card_step_"] [data-testid="stVerticalBlockBorderWrapper"],
.stApp [class*="st-key-card_step_"] [data-testid="stVerticalBlockBorderWrapper"] > div,
.stApp [class*="st-key-card_step_"] [data-testid="stVerticalBlock"] {{
    border-radius: 0 !important;
}}
.stApp [class*="st-key-card_step_"] [data-testid="stVerticalBlockBorderWrapper"] {{
    border-color: {COLOR_BORDER} !important;
    background-color: #FFFFFF;
}}
[class*="st-key-card_step_"] {{
    margin-bottom: 26px;
}}

.field-label {{
    font-weight: 700;
    font-size: 1rem;
    margin-top: 12px;
    margin-bottom: 4px;
}}
.field-label.first-label {{ margin-top: 0; }}

.edu-caption {{
    color: #45557A !important;
    font-style: italic;
    font-size: 0.93rem;
    margin: 0 0 16px 0;
    line-height: 1.45;
}}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"],
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] p {{
    color: {COLOR_PRIMARY} !important;
    font-weight: 700;
}}
.stTabs [data-baseweb="tab-highlight"] {{
    background-color: {COLOR_PRIMARY} !important;
}}

/* ---------- Notice boxes ---------- */
.notice-box {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
    margin: 12px 0;
    line-height: 1.5;
    border: 1px solid transparent;
    font-size: 0.95rem;
}}
.notice-box .notice-icon {{
    flex: 0 0 auto;
    font-weight: 700;
    font-size: 1.05rem;
    line-height: 1.4;
}}
.notice-box .notice-text {{ flex: 1 1 auto; }}
.notice-box.notice-success {{ background: #E6F5FB; border-color: #9ED6EE; }}
.notice-box.notice-success .notice-icon {{ color: {COLOR_CYAN} !important; }}
.notice-box.notice-info {{ background: #F3F6FA; border-color: {COLOR_BORDER}; }}
.notice-box.notice-warning {{ background: #FFF6DD; border-color: #F0CB6A; }}
.notice-box.notice-warning .notice-icon {{ color: #A86400 !important; }}
.notice-box.notice-error {{ background: #FBEAEA; border-color: #EFB0AC; }}
.notice-box.notice-error .notice-icon {{ color: #B3261E !important; }}

/* ---------- Code blocks and expanders ---------- */
div[data-testid="stCodeBlock"] pre {{
    background-color: #F5F8FC !important;
    border: 1px solid #E3E9F2 !important;
}}
details[data-testid="stExpander"] summary {{
    background-color: #F5F8FC !important;
}}

/* ---------- Helpers ---------- */
.chunk-text-box {{
    max-height: 260px;
    overflow-y: auto;
    background: #F7F9FC;
    padding: 10px;
    border: 1px solid #E3E9F2;
    white-space: pre-wrap;
    font-family: ui-monospace, Consolas, monospace;
    font-size: 0.82rem;
    line-height: 1.45;
    margin-bottom: 14px;
}}
.embedding-label {{
    font-weight: 700;
    margin-top: 18px;
    margin-bottom: 6px;
}}
.embedding-row {{
    font-family: ui-monospace, Consolas, monospace;
    font-size: 0.85rem;
    background: {COLOR_CYAN_LIGHT};
    border: 1px solid #B3E1F4;
    padding: 8px 12px;
    margin-bottom: 22px;
}}
.summary-line {{
    color: {COLOR_NAVY} !important;
    border-left: 4px solid {COLOR_CYAN};
    padding-left: 10px;
    font-weight: 700;
    font-size: 1.05rem;
    margin: 8px 0 10px 0;
}}
.prompt-section-bar {{
    background: {COLOR_NAVY};
    padding: 5px 12px;
    font-weight: 600;
    font-size: 0.82rem;
    letter-spacing: 0.6px;
}}
.prompt-section-bar, .prompt-section-bar * {{ color: #FFFFFF !important; }}
.prompt-section-body {{
    background: #FFFFFF;
    padding: 12px 14px;
    margin: 0 0 16px 0;
    font-family: ui-monospace, Consolas, monospace;
    font-size: 0.82rem;
    line-height: 1.5;
    max-height: 320px;
    overflow-y: auto;
    white-space: pre-wrap;
    border: 1px solid #E3E9F2;
    border-top: none;
}}
"""
