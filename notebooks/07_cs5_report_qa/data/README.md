# Data for Case Study 5

The files the notebook `07_cs5_report_qa.ipynb` reads. On your own machine it reads them from this folder; in Colab it
downloads each one once from this folder on GitHub into `_local/data/`, checks it against the checksum written into the
notebook or into the manifest, and unpacks the bundle into `_local/cs5_bundle/`.

| File | Bytes | sha256 | What it is |
| --- | ---: | --- | --- |
| `cs5_bundle.zip` | 213,660 | `cd45718b332a23deaec2963da481eea013f84fd23562cdd5a238c6f31e36d53d` | the case study's Python modules, documents, charts, label files and legal specification (29 files) |
| `cs5_bundle_manifest.json` | 4,766 | `81c984b60dd48210708c76b6f73d1e5e61702f30fc01b54fbdc913036c038f8d` | every file of the bundle with its checksum and size; the checksums of the bundle and of the recordings |
| `recordings.json` | 1,072,731 | `f26e243654a701f763cbe49bd8cb6eb311c7250066ae25b735be52137df8d37d` | every recorded model run the notebook replays, with its model, settings, tokens, cost and time |

All three files are UTF-8 with LF line endings where they are text. The notebook checks the manifest against the
checksum written into its bundle cell, and every other file against the manifest.

## What is synthetic, and how it was made

**Everything about the insurer is invented.** Brisendale Mutual is a fictitious Irish mutual that sells motor and home
insurance and does business in Lithuania under the freedom to provide services; the documents say it sells home
insurance there. Its supervisor, the home supervisor, is named only by a placeholder ("Home Supervisory Authority"), and
every e-mail address and link ends in `.example`, a domain reserved so that it can reach no real site.

- **`build/facts.json`**: 65 facts for year-end 2026 and 2025 from a seeded generator (`cs5_core.generate_facts`, seed
  20261003, the first draw from base seed 20261002 that met every constraint). Base amounts are drawn and rounded to
  EUR 0.1 million; every total and ratio is derived by code from the rounded amounts. The generator asserts the tier
  limits of Art. 82 of Delegated Regulation (EU) 2015/35, uses the own funds eligible for the MCR (tier 1 plus tier 2 up
  to 20% of the MCR, no tier 3) for the MCR coverage ratio, and makes sure that for every ratio the change in
  percentage points and the relative change differ at the printed precision. Six internal facts (the tiers, the
  diversification, the loss-absorbing capacity of deferred taxes and the basic SCR) never reach the text. The report is
  labelled a dry run of the new format.
- **`build/drivers.md`**: six driver bullets written for the case study; DR5 and DR6 say what is not known.
- **The charts** `chart_scr_modules.png` (the SCR by risk module, before diversification, without value labels),
  `_b.png` (market risk 2026 raised to EUR 250.0 million, +18.3%) and `_c.png` (operational risk 2026 raised to EUR 41.3
  million, +7.6%) were drawn by code from the facts; `work/_chart_rerender_3e9262249866.png` is the reference render
  that the provenance check D-CHART compares every chart with.
- **`build/warmup_excerpt.md`**: an abridged English version of the SFCR excerpt of a 2025 multi-agent report-review
  demonstration, with its figures and its three planted errors (the wrong expense ratio unchanged, the grammar and
  spelling errors re-created in English), and five statements nobody can verify.
- **`build/judge_testset.json`**: 30 sentences about Brisendale Mutual's year, labelled against the bullets (draft
  labels not yet confirmed by an actuary; 12 supported, 12 unsupported, 6 borderline), each with its bullet and a
  rationale, split into 20 sentences for tuning and 10 held out (checksum of the held-out labels in the file). The
  notebook shows the held-out labels only after a participant's own test; the file itself can be read by anyone.

## The three documents

- **Fresh** (`fresh.md`, `fresh_template.md`): the first of three drafts GPT-6 Luna wrote on 23 September 2026 at
  09:50 UTC, placeholders filled by code. No error of fact, number, period or direction was found in it.
- **Gold** (`gold.md`, `gold_template.md`): the fresh draft corrected by the author of the case study, every correction
  logged in `gold_corrections.json`:
  - G1 plain language: explain "qualifying holding";
  - G2 plain language: explain the quota share in everyday words;
  - G3 plain language: explain gross written premiums;
  - G4 plain language: explain net earned premiums and net claims incurred;
  - G5 missing explanation: why claims rose (causes from DR1 and DR4; the effect on net claims incurred is an
    inference, one of the borderline sentences of section 8);
  - G6 plain language: explain the combined ratio and the underwriting result;
  - G7 missing explanation: what changed the SCR, stated as DR2 states it.

  The gold version is the clean control. If its corrections changed, the gold and planted documents would change
  with them, and the recorded runs would have to be made again; a changed label in `error_log.json` is rescored by
  section 7.3 of the notebook from the stored findings, without a paid call.
- **Planted** (`planted.md`, `error_log.json`): the gold version with 16 errors. E01–E10 were planted by the author of
  the case study, who also wrote the checks, before the checks were frozen; H01–H06 were planted after the freeze by
  `gpt-6-sol` (effort low), which saw the rendered gold document, the facts, the bullets and a list of error
  categories written by the author of the checks; its second call also listed the gold text of the sentences already
  used, as off limits. E10 and H06 are targeted by no check, by design. `gold_lt_template.md` is the Lithuanian
  template of the gold version (section 9).

## The legal texts

Quoted from the Official Journal of the European Union as retrieved on 23 September 2026, in English and Lithuanian;
only the Official Journal is authentic. The full verbatim texts the checks use are in `legal/spec.json`.

- Directive (EU) 2025/2 of 27 November 2024 (CELEX 32025L0002), Art. 1 point (25), replacing Art. 51 of Directive
  2009/138/EC: <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32025L0002> and
  <https://eur-lex.europa.eu/legal-content/LT/TXT/HTML/?uri=CELEX:32025L0002>.
- Commission Delegated Regulation (EU) 2026/269 of 29 October 2025 (CELEX 32026R0269; OJ L, 2026/269, 18.2.2026; in
  force 10 March 2026, applying from 30 January 2027), Art. 1 point (86) (new Art. 292) and point (90) (new Art. 298a)
  of Delegated Regulation (EU) 2015/35: <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32026R0269>,
  <https://eur-lex.europa.eu/legal-content/LT/TXT/HTML/?uri=CELEX:32026R0269>, <http://data.europa.eu/eli/reg_del/2026/269/oj>.

Art. 292(1), first sentence:

> The part of the solvency and financial condition report targeted at policy holders and beneficiaries shall start with an indication that policy holders and beneficiaries have the right to request a version of that part in the official language of the Member State where they reside, provided that the insurance or reinsurance undertaking operates in that Member State through the right of establishment or the freedom to provide services.

Art. 292(3), second subparagraph — the prescribed text, which code inserts and never generates. English:

> “Two capital requirements aim at measuring the financial soundness of the undertaking: the Solvency Capital Requirement (SCR) and the Minimum Capital Requirement (MCR). The SCR should deliver a level of capital that enables an undertaking to absorb significant unforeseen losses over a one-year time horizon and should give reasonable assurance to policy holders that payments will be made as they fall due. The MCR is intended to provide a minimum level of security to be held at all times by the undertaking and below which the amount of financial resources (own funds) should not fall.
>
> The capital requirements will need to be covered by capital (own funds) of sufficient quality to ensure that losses can be covered on a going-concern basis as well as in the event of winding-up”.

Lithuanian (official):

> „Siekiant įvertinti įmonės finansinį patikimumą, taikomi du kapitalo reikalavimai: mokumo kapitalo reikalavimas ir minimalaus kapitalo reikalavimas. Mokumo kapitalo reikalavimas turėtų užtikrinti tokį kapitalo lygį, kad įmonė galėtų padengti didelius nenumatytus nuostolius per vienų metų laikotarpį, o draudėjus turėtų pakankamai užtikrinti, kad mokėjimai bus atlikti suėjus jų mokėjimo terminui. Minimalaus kapitalo reikalavimu siekiama užtikrinti minimalų užtikrinimo lygį, kurį įmonė visada turi palaikyti, o įmonės finansinių išteklių (nuosavų lėšų) suma neturėtų būti mažesnė nei šis lygis.
>
> Kapitalo reikalavimus reikės padengti pakankamos kokybės kapitalu (nuosavomis lėšomis), siekiant užtikrinti, kad būtų galima padengti nuostolius tiek veiklos tęstinumo sąlygomis, tiek likvidavimo atveju.“

Art. 292(5), first subparagraph (the English text lacks the word "report" after "financial condition"):

> 5. The part of the solvency and financial condition targeted at policy holders and beneficiaries shall not exceed five pages.

Art. 298a(1), second sentence:

> Where the translation is generated by a machine translation tool, insurance or reinsurance undertakings shall disclose to that policyholder that that part of the solvency and financial condition report has been machine translated.

> Kai tekstas išverčiamas naudojant mašininio vertimo priemonę, draudimo ar perdraudimo įmonės tam draudėjui atskleidžia, kad ta mokumo ir finansinės padėties ataskaitos dalis buvo išversta mašininiu būdu.

**What rests on less than the text of the acts.** No wording is prescribed for the language notice or for the
machine-translation disclosure: both texts in the documents are the case study's own. That the SFCR for financial year
2027, disclosed in 2028, is the first in the new format is EIOPA's stated view (news item of 30 March 2026 and final
report EIOPA-BoS-26/081, section 1.4), not a provision; the year-end 2026 figures are therefore labelled a dry run.
"The ratio of coverage" in Art. 292(3)(b) is singular; showing the coverage ratios of both the SCR and the MCR is the
case study's reading. Art. 292(3)(c) asks for information only on a non-compliance with the SCR or the MCR, and
Art. 292(2)(d) only where the undertaking belongs to a group: the documents' explicit statements that Brisendale Mutual
met both requirements and belongs to no group are house elements, which `D-SPEC` checks as required (the planted error
E07 removes one). Art. 298a(1), the disclosure included, does not apply where the translation in the requested
language is available online (Art. 298a(2)). The Regulation defines no page format, so every page count before
typesetting is an estimate.
Not checked: the Lithuanian transposition of Directive (EU) 2025/2 and any guidance of the Bank of Lithuania, the new
implementing technical standards on public disclosure, the content of the plans referred to in Art. 19a or 29a of
Directive 2013/34/EU, and national or industry templates. EIOPA's revised guidelines on reporting and disclosure
(EIOPA-BoS-26/280) contain no guideline for the policyholder part.

## The recordings

`recordings.json` holds every model run the notebook replays. All were made on 23 September 2026 (UTC) with the
`openai` package 3.14.0, except the compatibility run (2.29.0). Costs are at OpenAI's list prices for standard
processing retrieved on 22 September 2026, in USD per million tokens — input, cached input, cache write, output:
`gpt-6-luna` 0.10 / 0.01 / 0.125 / 0.50, `gpt-6-sol` 2.00 / 0.20 / 2.50 / 10.00. `gpt-6-luna` ran at reasoning effort
`none` with `temperature=0`, `gpt-6-sol` at effort `low` without a temperature; both are aliases without a dated
snapshot, and every call was made with `store=False` and a strict JSON schema.

| Key | What | Model | Recorded (UTC) | Cost (USD) |
| --- | --- | --- | --- | ---: |
| `drafts` | three drafts from the same request; draft 1 became the fresh document | Luna | 09:50 | 0.0020 |
| `holdout_planter` | the hold-out batch, two calls, 30 seconds after the checks were frozen at 10:09:00 | Sol | 10:09–10:10 | 0.0342 |
| `chart` | calibration of the blind chart read on the gold chart, 5 reads, before the freeze | Luna | 10:08 | 0.0007 |
| `gate.runs` | all checks with the blind chart read: 5 runs each on gold and planted, 1 on fresh | Luna | 10:11–10:17 | 0.0243 |
| `gate.runs` | all checks with the blind chart read, 1 run each on gold and planted | Sol | 10:17–10:19 | 0.1293 |
| `gate.chart_variants` | the two changed charts, 3 blind reads each | Luna | 10:19 | 0.0009 |
| `judge` | the 30 sentences with the gate's judge, 3 runs with Luna and 1 with Sol | Luna, Sol | 10:19–10:21 | 0.0300 |
| `translation` | the Lithuanian translation (16 paragraphs), two fidelity checks, one machine translation of the prescribed text | Luna | 10:21 | 0.0026 |
| `warmup` | the proofreading and the verification check of the warm-up | Luna | 10:21 | 0.0002 |
| `participant` | one run of the live path end to end, in sequence: draft, checks on the draft, gold and planted | Luna | 10:22–10:23 | 0.0078 |
| `compat_openai2` | all checks on gold with `openai` 2.29.0 on Python 3.13.1 | Luna | 10:23–10:24 | 0.0019 |
| `exercise_c_reference` | the reference policy of exercise (c) on the tuning and the held-out sentences | Luna | 10:44 | 0.0012 |
| `earlier_draft` | the live draft of an earlier run of the notebook (drafted 11:09) and all text checks on it | Luna | 11:17 | 0.0018 |

The case study's build spent USD 0.2519 in 167 paid calls, pilots, three drafts discarded for a gate bug and the
compatibility run included; the last two rows were added while the notebook was built. The deterministic results in the
file (`gate.deterministic_only`, `gate.with_dpp`, `gate.mutants`, `gate.overflow`, the page counts) cost nothing; the
typeset page counts come from printing the HTML renders to A4 PDF with a headless browser, which the notebook does not
repeat. The model outputs were generated under OpenAI's terms of use from the synthetic inputs above. A rerun can give
different answers: the models are aliases that may change, and their answers are not fully deterministic even at
temperature 0.

Internal labels of the build were replaced before publication — the planter and corrector of the development batch
and the gold corrections are named "the author of the case study", and the judge labels are marked as drafts not yet
confirmed by an actuary — and the build's own sign-off log was left out: the notebook writes a fresh one into
`_local/`, and signs nothing unless a reviewer's decisions, or the notebook's examples on request, are given.

## Lithuanian

The Lithuanian texts have been **checked by machine only**: GPT-6 Luna's translation, and the case study's own
Lithuanian house texts in `cs5_core.house_texts` — the title, the machine-translation disclosure, the table labels, the
captions, the plans statement and the invariant abbreviations after numbers ("mln. EUR", "proc.", and "proc. punkt."
for percentage points, whose usage is not confirmed). Nobody who built the case study reads Lithuanian; the checks test
numbers, placeholders, the official wording and the disclosure, not fluency. The prescribed text and the section
headings are the official Lithuanian ones. In the seminar, a Lithuanian participant is asked to read a paragraph.

## The frozen checks and the three post-hoc changes

`build/cs5_checks.py` (sha256 `96c9ecb36a10…`) and `build/cs5_llm_checks.py` (`d3b1cca97c14…`) are byte-identical to the
versions frozen at 2026-09-23T10:09:00Z, before the hold-out errors were planted; the prompts, schemas and settings of
the LLM checks have the frozen fingerprints (`recordings.json`, `meta.freeze`). Three changes were adopted after the
freeze and are applied by the notebook at run time, switchable with `USE_POST_HOC`:

1. the Lithuanian language-notice rule of `D-NOTICE` allows up to eight words between "oficialiąja" and "kalba";
2. the renderer lets a Lithuanian value ending in a full stop ("proc.") absorb the sentence's full stop, so that no
   sentence ends in "..";
3. the page estimate uses 53 lines per page instead of 50.

None of them changes a finding on the English gold or planted documents, so the recall figures are those of the frozen
checks. Three modules differ from the build versions: `cs5_llm.py` (the notebook's client, ledger and session cap, the
calls under way counted against the cap, and nothing more sent after three failed requests in a row; same interface and
fingerprint function), and `cs5_warmup.py` and `cs5_translate.py` (docstrings and one label only).

## A working-group prototype

The design shares two ideas with a working-group prototype for validating a technical actuarial document: the LLM
extracts and Python decides, and a checker is measured on planted errors and a clean control. The prototype is referred
to, not reproduced: none of its code, text or data is in this folder.

## Rights note

The synthetic facts, bullets, documents, charts, labels and the code in the bundle were written for this case study
(the warm-up excerpt is an abridged English version of the excerpt of a 2025 demonstration, see above) and fall under
the repository's licences (MIT for code, CC BY 4.0 for content). The quotations from the Official Journal
are EU legal texts, reproduced from EUR-Lex with their source; © European Union. The recorded model outputs are
published under OpenAI's terms of use so that the notebook runs without a key.
