# Data for notebook 02

The files the notebook `02_llm_techniques.ipynb` reads. On your own machine it reads them from this folder; in Colab
it downloads each one once from this folder on GitHub into `_local/data/`. It checks every file against the checksum
below before it uses it.

| File | What it is | Used in |
| --- | --- | --- |
| `riscbac_en_first10.jsonl` | ten synthetic car-insurance contracts from the RISCBAC corpus | section 2, structured outputs |
| `mortality_tables.sqlite` | the German private-health mortality tables PKV-Sterbetafel 2022 to 2025, in SQLite | section 3, function calling |
| `recordings_02.json` | the model's replies in the saved run of sections 2 and 3 | both, when no key is visible |

## `riscbac_en_first10.jsonl`

10 lines, 1,630,859 bytes, UTF-8, LF line endings,
sha256 `a2d76ac5884f66bd65740c5c906fff4c5ac82b37bcdfd037b056a20d7c1607a7`.

**What it contains.** One JSON object per line with a single field, `"text"`: the full text of one synthetic
automobile insurance contract, 157,208 to 160,536 characters, with pages separated by `<###NEW_PAGE###>`. Each
contract is issued on the Quebec owner's form (`Q.P.F. B 1 - OWNER'S FORM`) with Quebec endorsements (Q.E.F.): the
declarations — the named insured and address, the contract period, the vehicle, the coverages with their amounts,
deductibles and premiums, the endorsements, the annual premium and tax, the main driver and the discounts — and a
cover page, the general conditions and notices. The notebook sends the model only the declarations pages, 3,925 to
4,963 characters per contract.

**Source.** RISCBAC, a corpus of 10,000 synthetic bilingual (English and French) automobile insurance contracts
generated on the model of Quebec's regulatory standard form, published by David Beauchemin and Richard Khoury:

> Beauchemin D, Khoury R (2023) RISC: Generating Realistic Synthetic Bilingual Insurance Contract. arXiv:2304.04212.
> https://arxiv.org/abs/2304.04212

Dataset: <https://huggingface.co/datasets/davebulaval/RISCBAC>. This file holds the first ten English contracts, as its
name says, unmodified. It was taken from the lecturer's June 2026 seminar repository, which used the same sample; it has
not been compared byte for byte with the copy on Hugging Face.

**Licence.** CC BY 4.0, as declared on the dataset's Hugging Face card. The contracts are synthetic: they describe no
real person, vehicle, insurer or policy. They carry artefacts of the generator, which the notebook points out: every
contract uses the Quebec form while no address is in Quebec, one main driver is 15 years old at inception, some taxes
are printed with floating-point noise (`94.22999999999999$`), and the serial numbers are labelled in French.

Attribution: RISCBAC — synthetic Quebec automobile insurance contracts, D. Beauchemin and R. Khoury (2023),
arXiv:2304.04212, via Hugging Face `davebulaval/RISCBAC`, licensed under CC BY 4.0
(<https://creativecommons.org/licenses/by/4.0/>); first ten English contracts, unmodified.

## `mortality_tables.sqlite`

53,248 bytes, an SQLite 3 database, sha256 `ce714b3cbcbddafa560a74eebbfb3ffc6616e94091e83c0d8d95795b8f0a90bf`.

**What it contains.** One table, `mortality_table`, with the columns `id`, `mortality_table` (the table's name),
`gender` (`MALE` or `FEMALE`), `age` and `probability` (the one-year death probability $q_x$), and SQLite's own
`sqlite_sequence`; no indexes, no views. 824 rows: four tables × two sexes × ages 0 to 102, with no gaps and no
duplicates. The table names are `PKV-Sterbetafel 2022`, `PKV-Sterbetafel 2023`, `PKV-Sterbetafel 2024` and
`PKV-Sterbetafel 2025`. The notebook opens the file read-only, and the connection its tools use may read only the four columns
`mortality_table`, `gender`, `age` and `probability`; the model itself never touches the file.

**Source.** The values are the PKV-Sterbetafeln 2022 to 2025, the mortality tables that the Bundesanstalt für
Finanzdienstleistungsaufsicht (BaFin) publishes each year under § 159 (1) VAG for German private health insurance,
based on the calculations of the Verband der Privaten Krankenversicherung. BaFin's download page for the 2025 table
gives as an example that 288 of one million men aged 30 do not reach age 31 ($q_{30}$ = 0.000288); the database holds
the same value. The file comes from the lecturer's June 2026 seminar repository. It ends at age 102; whether BaFin's
tables continue beyond that age was not checked, and only the value above was compared with BaFin's publication.

These are health-insurance tables. They are used here for look-ups and comparisons, not to price life insurance.

Attribution: PKV-Sterbetafeln 2022, 2023, 2024 and 2025, published by the Bundesanstalt für
Finanzdienstleistungsaufsicht (BaFin), <https://www.bafin.de>.

## `recordings_02.json`

56,960 bytes, UTF-8, LF line endings,
sha256 `c70351c06e860dda96717a0677e30f657d3fc5c22398f24fcd401a6b85d74248`. The notebook's setup cell holds this
checksum.

**What it contains.** A `meta` block — model, date, `openai` package and Python versions, calls, tokens, cost and the
prices used — and `replies`: the 19 replies of the saved run, each under a fingerprint of its request (the sha256 of
the model, the instructions, the input, the tools and the JSON schema), with its text, its output items (function calls
included) and its token counts. Without a key, or when a call fails, the notebook's `respond()` looks the request up
here and replays the reply; a request that differs in any way has no recording.

**How it was made.** By the saved run of the notebook itself, on 23 September 2026 (UTC), with the `openai` package
3.14.0 on Python 3.13.15, model `gpt-5.4-nano-2026-03-17` at its default settings (no reasoning effort,
`temperature` or `top_p` sent) through the Responses API: 1 free-text request and 11 structured-output requests in
section 2, and 7 function-calling requests in section 3. Tokens: 29,720 input tokens, 17,920 of them billed at the
cached price, and 7,076 output tokens. Cost at OpenAI's list prices as of 15 September 2026 (USD 0.20 / 0.02 / 1.25 per
million input / cached input / output tokens): **USD 0.0116**, or USD 0.0148 had no input been cached. Building the
notebook, two trial runs included, cost USD 0.0407 in 58 calls.

The replies are output of an OpenAI model, generated under OpenAI's terms of use from the files above, and are
published so that the notebook can be read and run without a key. A new run can give different answers: the notebook's
commentary describes this recording.
