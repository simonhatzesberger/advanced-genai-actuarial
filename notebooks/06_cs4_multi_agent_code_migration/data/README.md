# Data for Case Study 4

The files the notebook `06_cs4_multi_agent_code_migration.ipynb` reads. On your own machine it reads them from this
folder; in Colab it downloads each one once from this folder on GitHub into `_local/data/`. It checks every file's
checksum before it uses it, unpacks the bundle into `_local/cs4_bundle/` and checks every file of the bundle against
the manifest.

| File | Bytes | sha256 | What it is |
| --- | ---: | --- | --- |
| `cs4_bundle_manifest.json` | 12,171 | `7bbc73756e24f52294bce403f4e26dc63c396d1ec66e9e97591a09de326a7602` | the list of every file in the bundle with its checksum, and the checksums of the bundle and the recordings; its own checksum is written into the notebook |
| `cs4_bundle.zip` | 266,992 | `e11a1d20de5e659c5db87b1804b5e18a3637df0286d1f0c8fd068496239e572e` | 77 files: the article's R scripts and data, R's results, the harness, the test suites, the mutants, the exercises, the generators and `cs4lib`, the notebook's plumbing |
| `recordings.json` | 1,864,815 | `8ad8b6e52befde8e417b53aad398dbd8b95c55a610b659af2f4f4d6f334b97d3` | every recorded run the notebook reads: 17 migration runs, 5 Part B runs, and the recorded scores |

All text files, inside the bundle and out, are UTF-8 without a byte-order mark and have LF line endings. Absolute
local paths in the recordings are rewritten (`<workspace>`, `<bundle>`, `<python>`, `<home>`, `<path>`).

## Rights

**The article's files.** The two R scripts and their data (`legacy/chain_ladder/chain_ladder.R`, `triangle.csv`,
`legacy/reserving_glm/reserving_glm.R`, `claims_triangle.csv`, `policies.db`), the article's two test suites and their
expected values (`tests_article/`), and the system prompts the notebook adapts, come from the IAA AI Task Force's
case-study repository, <https://github.com/IAA-AITF/Actuarial-AI-Case-Studies>, tag
[`eaj-v1.0`](https://github.com/IAA-AITF/Actuarial-AI-Case-Studies/tree/eaj-v1.0/case-studies/2026/actuarial_legacy_code_migration_multi-agent_system)
(commit `6cca6fdf`), folder `case-studies/2026/actuarial_legacy_code_migration_multi-agent_system/`, which accompanies

> Hatzesberger S, Nonneman I (2026) Advanced applications of generative AI in actuarial science: case studies beyond
> ChatGPT. *European Actuarial Journal* 16(2):481–523. https://doi.org/10.1007/s13385-026-00464-9

That repository licenses its code under the MIT licence and its text and documents under CC BY 4.0. The notice below
covers the R scripts, their data, the article's tests and the prompts adapted from the article, in this folder, in the
bundle and in the notebook:

```
MIT License

Copyright (c) 2025 International Actuarial Association

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

What was changed: `chain_ladder.R` has CRLF line endings in the article's repository and LF here; the other four files
are byte-identical. The article's test files were changed only in their file paths; `tests_article/CHANGES.md` in the
bundle has the complete diff. The prompts were adapted; section 5.1 of the notebook lists the changes.

**Everything else in the bundle** — the harness, the new test suites, the mutants, the synthetic inputs, R's results,
the exercises, the generators, `cs4lib` and the recordings — was made for this seminar and falls under the
repository's licences (MIT for code, CC BY 4.0 for prose).

**freMTPL2 is not in this folder.** Part B downloads `freMTPL2freq` and `freMTPL2sev` from OpenML (datasets 41214 and
41215) at run time into `_local/fremtpl2/` and checks their sha256 (`aead80a9…` and `c721d570…`). They are downloaded,
not redistributed: OpenML lists them under CC0, while the `CASdatasets` R package they come from is licensed under the
GPL. The VBA exercise's 200 portfolio rows are not freMTPL2 records either (see below).

## `cs4_bundle.zip`

| Folder | What it holds | How it was made |
| --- | --- | --- |
| `legacy/` | the article's two R scripts and their data | copied from the article's repository (see Rights) |
| `inputs/` | the hidden triangles B and the gap triangle: inputs only, no results | `tools/make_inputs.py`, fixed seeds (below) |
| `ground_truth/` | R's results, one JSON per triangle (doubles with 17 significant digits), and R's printed transcripts | R 4.5.2 (DBI 1.2.3, RSQLite 2.4.6, dplyr 1.1.4) running the article's scripts unchanged through `tools/r/` on 23 September 2026; the only edit is `tail_factor <- 1.05` for the tail case |
| `harness/` | the runner, the audit-hook fence, the grader, the tripwire and the two interface texts | written for the seminar |
| `tests/` | the new suites, 16 tests each, and the value-free check helper | written for the seminar |
| `tests_article/` | the article's two suites and their expected values, changed only in their paths | see Rights |
| `mutants/` | the honest references (m0), five deliberately wrong translations (m1 to m5), m2b (the 5-line labels-only stub of section 7.6, written for the article's interface) and the adapter for the article's suites, all written by hand | `tools/make_mutants.py` |
| `exercises/prompt_injection/` | `chain_ladder.R` with a 7-line comment inserted after line 8; R still prints 15,316.33 | written for exercise (a) |
| `exercises/vba/` | the VBA module, its interface, 218 test inputs, the Excel ground truth, 25 tests, the adapter to the fenced harness and a reference solution | below |
| `tools/` | the input and mutant generators and the R harness; run on a copy of the bundle, they reproduce every file byte for byte | written for the seminar |
| `cs4lib/` | the notebook's plumbing: workspace and fenced tools, task messages, report, recordings, drawing, scoring, the VBA exercise, and Part B (data, tools and registry, gate and nodes) | written for the seminar |

**The synthetic triangles.**

- Chain ladder B (`inputs/chain_ladder/triangle_B.csv`, seed 20261002): 10 × 10, origin years 2010–2019, integer
  increments; a volume of 1,700 growing about 6% a year with 3% lognormal noise, a slower payment pattern than A and 4%
  noise per cell. R's total reserve is 32,389.61 (A: 15,316.34), and every origin year from 2011 differs from A's by at
  least 67%.
- The gap triangle (`inputs/chain_ladder/triangle_gap.csv`): A with the cell 2013/dev_3 removed; R stops on it.
- GLM B (`inputs/reserving_glm/claims_triangle_B.csv`, seed 20260925): 15 × 15, origin years 2005–2019, means
  a_i × b_j with gamma noise of variance 10 × mean^1.5, rounded to integers. The seed is the first from 20260923 on that
  gives a dispersion between 150 and 600, a bootstrap coefficient of variation between 0.10 and 0.20 and a material
  process variance. In R: φ = 482.93, total reserve 88,935.03, bootstrap coefficient of variation 0.1154. The noise is
  not exactly over-dispersed Poisson (variance power 1.5 instead of 1): an exactly ODP triangle with this variation put
  zeros into the late cells.

**The VBA exercise.** `legacy/MTPL_Premium.bas` is a small motor tariff function written for the seminar (age, power
and area factors, bonus-malus, a minimum annual premium, `Trim`/`UCase`, `Err.Raise`, Excel's `ROUND`). Its 218 test
inputs (`inputs/vba_cases.json`, seed 20261002) are 200 synthetic portfolio rows — each column drawn on its own from
freMTPL2freq's distribution, so no policy record is copied — and 18 edge cases (an empty age, an age of 29.5, area codes
with spaces or a non-breaking space, bonus-malus levels out of range, premiums that end in a half cent such as 253.125).

**The VBA ground truth is Excel's, not VBA's.** The legacy results in `ground_truth/mtpl_premium_ground_truth.json` were
computed by Excel itself: a worksheet formula written for the seminar, restating `MTPL_Premium` step by step (`LET`,
`IFS`, `UPPER`, `TRIM`, `ROUND`), was evaluated over COM in Excel 16.0 (build 17932, 64-bit) on 23 September 2026, on
all 218 inputs. **The VBA function itself was never executed**: importing the module into a workbook through COM needs
the setting "Trust access to the VBA project object model", which was off and was left off. Three things are therefore
assumptions: that the formula restates the VBA faithfully (how `Select Case` matches, an empty cell comparing as 0,
what `Trim` removes; worksheet `TRIM` also collapses inner runs of spaces, which no test input has); that VBA's Double
arithmetic gives the same double for `annual * Exposure` as the worksheet; and that
`Application.WorksheetFunction.Round` rounds that double as the worksheet `ROUND` does. The worksheet formula and the
Python reference solution agree bit for bit on all 212 premiums and on all 6 error messages, but both were written for
the seminar from the same reading of the VBA.

## `recordings.json`

One JSON file with every recorded run. Nothing in it is needed to run the notebook live; it is what the notebook shows
without a key, and what its tables and commentary quote.

**`part_a`: 17 migration runs.** Recorded on 23 September 2026 between 08:56 and 09:23 UTC with the prompts, tests
and settings of the notebook (each run carries its fingerprint, which section 5.5 of the notebook checks), on Python
3.13.15 with openai 3.14.0 and langgraph 1.2.11, GPT-6 Sol at reasoning effort `low` for the analysis agent and the
translator and GPT-6 Luna at effort `none` (temperature 0) for the compilation agent, the test runner and the report
writer; caps USD 0.40 per run and USD 1.00 per session. Every attempt's code, test results and tripwire report, every
call's tokens (cached tokens and cache writes included) and cost, and the printout are kept.

| Runs | Variant | USD at list prices |
| --- | --- | ---: |
| `rec_cl_01` … `rec_cl_05`, `rec_glm_01` … `rec_glm_05` | the benchmark: 5 chain-ladder and 5 GLM runs | 0.6330 |
| `rec_leak_sol_01`, `rec_leak_luna_01` | the leak demonstration (section 8), with GPT-6 Sol and with GPT-6 Luna as the translator | 0.2275 |
| `rec_injection_01` | exercise (a): the injected R script, at most 2 attempts, no report narrative | 0.0494 |
| `rec_vba_01` | exercise (b): the VBA migration | 0.0280 |
| `rec_approval_01` | exercise (c): the migration with a human approval step (the reviewer's decisions scripted) | 0.0783 |
| `pilot_glm_leak_01`, `pilot_glm_leak_02` | two pilot leak runs with an earlier version of the code and a milder note (`stage: pilot`; only the final code was kept) | 0.4378 |

The 15 final runs cost USD 1.0162 in all.

**`part_b`: 5 Part B runs.** Recorded on 23 September 2026 with the prompts, brief, schemas and settings of the
notebook (fingerprint `0fc594814a55`, checked in section 9.3), GPT-6 Sol at effort `low` for the planner and the fact
checker and GPT-6 Luna at effort `none` for the analyst and the writer, on the same software. They cost USD
0.0462 to 0.0511 each, USD 0.2404 in all. Each run keeps its printout, its final state (plan, decisions,
analysis, drafts, gate results, checker notes, signed report) and its cost by agent; the full results registry, which
the notebook does not need, is left out.

**`mutant_scores`, `vba_scores`, `identical_to_r`.** No model was involved: the scores of the bundle's mutants on the
article's suites and the new suites, and of the VBA reference solution and its mutants, recorded by the harness build
on 23 September 2026; and every final translation of the migration runs re-run through the fenced runner and compared
with R's results, quantity by quantity.
