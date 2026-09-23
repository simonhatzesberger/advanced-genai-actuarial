# Data files for Case Study 3

No photo file from the vehicle-damage data set is stored in this repository: the notebook fetches the photos it
needs from Kaggle when it runs, into `_local/`. Its saved outputs do show the twelve photos listed in
`gallery.csv`, as thumbnails of at most 256 pixels on the long side: in the gallery of section 2.3 and in the
twelve-photo comparison of section 5. No other photo of the data set appears in the notebook.

**Data set.** The Analytics Vidhya × Ripik.AI HackFest data set (1–3 December 2023), published on Kaggle by the
user imnandini as `imnandini/analytics-vidya-ripik-ai-hackfest`. The uploader declares an Apache 2.0 licence.

| File | What it holds |
|---|---|
| `predictions_test300.csv` | The 300 test photos (file name and label) with every model's prediction. The three 2025 columns are the saved predictions of March 2025 from the research notebook behind Hatzesberger & Nonneman (2026). The 2026 columns were recorded on 22 September 2026 with the models named in the notebook. |
| `recording_2026.json` | Tokens, cost and latency of the 2026 recording, with the package versions used. |
| `test300_near_copies.csv` | For each test photo, its highest correlation and smallest hash distance to any training or validation photo, and whether it counts as a near-copy (notebook section 6.9). |
| `gallery.csv` | The 12 gallery photos the notebook shows (file names only), with the screen that keeps them apart from every photo the fine-tuned model was trained, validated or tested on, and a screening note. |
| `gallery_predictions_2026.csv`, `synthetic_predictions_2026.csv` | The recorded answers of the saved run. The notebook falls back on them when a model is not available to the reader's key. |
| `synthetic_base_car.png`, `synthetic_dent.png` | Images generated with `gpt-image-2.5-sunburst` for the fraud-awareness exercise: an undamaged car that does not exist, and the same car with a dent added. A visible SYNTHETIC band was added after generation, so their C2PA signatures no longer validate. |

Article: Hatzesberger S, Nonneman I (2026) Advanced applications of generative AI in actuarial science: case studies
beyond ChatGPT. European Actuarial Journal 16(2):481–523. https://doi.org/10.1007/s13385-026-00464-9
