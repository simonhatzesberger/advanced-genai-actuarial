# Data for Case Study 1

The files the notebook `03_cs1_claims_text_features.ipynb` reads. On your own machine it reads them from this folder;
in Colab it downloads each one once from this folder on GitHub into `_local/data/`.

| File | What it is |
| --- | --- |
| `claims_3000.csv` | the 3,000 workers' compensation claims of the case study |
| `luna_extraction_3000.csv` | the three features GPT-6 Luna extracted from every claim description, used by the models |
| `luna_extraction_3000.json` | how that extraction was made: model, settings, date, tokens, cost, time |
| `luna_nature_of_injury_3000.csv` | the extra-exercise feature `nature_of_injury` for every claim |
| `luna_nature_of_injury_3000.json` | how that extraction was made |

## `claims_3000.csv`

3,000 claims, 18 columns, 474,360 bytes, LF line endings,
sha256 `c875c29d4a659a5222606d600be2b150f0abd9e6dfa56a64fadd3c1ffb4af44d`. The notebook checks this checksum before
it uses the file.

**What it contains.** One row per claim: a claim number, the date and hour of the accident, the report date, the age,
gender, marital status, dependants, weekly wage, part-time or full-time status, hours and days worked per week of the
injured worker, a short free-text claim description, and the ultimate incurred cost of the claim. The file is kept
byte-identical to the published copy and therefore also holds four columns the notebook drops as soon as it reads
the file: the insurer's initial estimate of each claim's cost, and three fields that the article's authors extracted
from the descriptions with `gpt-4o-mini-2024-07-18` (`number_of_body_parts_injured`, `main_body_part_injured`,
`cause_of_injury`). The notebook extracts its own features from the descriptions alone.

**Source.** The data are **synthetic**: they describe no real person and no real claim. They were created by
**Colin Priest** for the Kaggle InClass competition "actuarial-loss-estimation"
(<https://www.kaggle.com/competitions/actuarial-loss-estimation>, 15 December 2020 to 11 April 2021), hosted by
actuarial professional bodies. This copy is byte-identical to the file published in the IAA AI Task Force case-study
repository, <https://github.com/IAA-AITF/Actuarial-AI-Case-Studies>, tag `eaj-v1.0`, folder
`case-studies/2025/claim_cost_prediction_with_LLM-extracted_features/`, which accompanies

> Hatzesberger S, Nonneman I (2026) Advanced applications of generative AI in actuarial science: case studies beyond
> ChatGPT. *European Actuarial Journal* 16(2):481–523. https://doi.org/10.1007/s13385-026-00464-9

**Rights note.** No licence was ever declared for these data. The competition rules contain no licence clause and no
redistribution clause, and Kaggle's general terms of use were not verified. The licences of this repository (MIT for
code, CC BY 4.0 for content) and of the IAA repository do **not** apply to this file. It is redistributed here, with
attribution, for non-commercial teaching, so that the notebook runs without an account or a download from Kaggle.
**If you hold rights in these data and want the file removed, please open an issue: it will be taken out.**

Attribution: synthetic workers' compensation claims created by Colin Priest for the Kaggle InClass competition
"actuarial-loss-estimation"; obtained via the IAA AI Task Force case-study repository (tag `eaj-v1.0`).

## `luna_extraction_3000.csv` and `luna_extraction_3000.json`

The features of the enhanced model: for each of the 3,000 claims, the class of the primary injured body part (one of
8), the class of the cause of the injury (one of 13) and the number of body parts injured, as GPT-6 Luna read them
from the claim description.

Columns: `claim_number`, `body_part_category`, `cause_of_injury_category`, `number_of_body_parts_injured`, `model`,
`effort`, `extraction_date` (UTC).

How it was made: by the notebook itself, section 5, with `RUN_FULL_EXTRACTION = True`.

- Model `gpt-6-luna` (an alias; no dated snapshot exists), reasoning effort `"none"`, `temperature=0`, through
  `client.responses.parse` of the `openai` package, with the Pydantic schema `ClaimFeatures` (two `Literal` fields and a
  non-negative integer) and the instructions printed in section 3 of the notebook.
- One call per distinct description: 2,420 calls for 3,000 claims; each answer was copied to every claim with the
  same description. No call failed, and none needed a retry.
- Recorded on 22 September 2026 (UTC) with 16 requests in parallel, in 196 seconds. Tokens: 3,185,963 input tokens,
  3,141,905 of them billed at the cached price, and 92,860 output tokens.
- Cost at OpenAI's list prices of 22 September 2026 (USD 0.10 / 0.01 / 0.50 per million input / cached input /
  output tokens): **USD 0.0823**, or USD 0.3650 had no input been cached.

The JSON file holds these figures and a fingerprint of the model, its settings, the instructions and the schema; the
notebook compares it with the current instructions and warns if they differ.

## `luna_nature_of_injury_3000.csv` and `luna_nature_of_injury_3000.json`

The worked example of exercise (a): for each of the 3,000 claims, the nature of the primary injury (one of 10 classes,
from `FRACTURE` to `NOT_STATED`), as GPT-6 Luna read it from the claim description.

Columns: `claim_number`, `nature_of_injury`, `model`, `effort`, `extraction_date` (UTC).

How it was made: by the notebook itself, exercise (a), with `RUN_FIELD_EXTRACTION = True`; same model, settings and
procedure as above, with the schema `InjuryNature` and the instructions printed in the notebook. Recorded on 22
September 2026 (UTC): 2,420 calls, one per distinct description, none failed, in 195 seconds with 16 requests in
parallel; 1,346,763 input tokens (the instructions are too short for OpenAI's prompt cache, so none was cached) and
49,437 output tokens; **USD 0.1594** at the same list prices.

## The recorded extractions

Both extractions are output of an OpenAI model, generated under OpenAI's terms of use from the claim descriptions
above, and are published so that the notebook's models run without a key and without re-extracting 3,000 claims.
A new run of the same extraction can give a few different answers: the model is an alias that may change, and its
answers are not fully deterministic even at temperature 0.
