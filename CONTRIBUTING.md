# Working together on this repository

Four people edit this repo, so the rules are simple and mechanical. Nothing here needs
git knowledge beyond the five commands in step 2.

## 1. One time setup

```
git clone https://github.com/Electric97599/ai4e-price-alerts.git
cd ai4e-price-alerts
pip install -r requirements.txt
python src/panel.py
python src/baseline.py
streamlit run app.py
```

If `streamlit run app.py` opens a browser tab with the price history, the setup worked.
Ask for access before cloning if the clone asks for a password: the owner adds you as a
collaborator by email or by GitHub username.

## 2. The loop for every task

```
git switch main
git pull
git switch -c task/<issue-number>-short-name
# edit files
git add -A
git commit -m "Closes #<issue-number>: what changed"
git push -u origin task/<issue-number>-short-name
```

Then open a pull request on GitHub. One reviewer approves, the reviewer merges. Never
push straight to `main`, because a broken `main` breaks the demo app for everyone.

## 3. What each file owns

| File | Owner | What it does |
|---|---|---|
| `src/panel.py` | Ogunkoya | Builds the evaluation panel and prints the counts in Table 1 of the proposal |
| `src/baseline.py` | Ogunkoya | Seasonal naive and persistence reference rules, with coverage and the balanced market check |
| `src/sarima.py` | Abodunrin | One SARIMA per series, refitted at every monthly origin |
| `src/lightgbm_model.py` | Abodunrin | Pooled LightGBM, with and without the exchange rate |
| `src/score_latest.py` | Abodunrin | Scores the newest month for every series into `outputs/alerts.csv` |
| `src/run_folds.py` | Bizima | Runs any scorer through all three folds and writes the fold table |
| `src/features_fx.py` | Bizima | Turns the frozen CBN rate series into a model ready monthly feature |
| `src/report_tables.py` | Dufitumukiz | Penalty sensitivity at k = 1, 3, 5 and the subgroup tables |
| `src/resources.py` | Dufitumukiz | Timing and memory of a full scoring pass |
| `app.py` | Abodunrin | The Streamlit demo, three screens |

Two files are shared and nobody edits them alone, because every model depends on them:

- `src/folds.py` holds the three fold windows and the cell convention (a scored cell is
  indexed by the month whose outcome it records).
- `src/metrics.py` holds every measure in the proposal. Run `python src/metrics.py`; if
  the self tests fail, stop and say so, because the comparison is not trustworthy.

## 4. The rules the whole group follows

- Every model writes a CSV of scores with the columns `series, mi, score`, where `mi` is
  the outcome month as `year * 12 + month`. `src/run_folds.py` reads that shape, so the
  comparison costs nobody any glue code.
- Thresholds are chosen inside each fold on calibration cells only, through
  `metrics.choose_threshold`. Never pass a scored month to it, and never tune a
  threshold by looking at scored results.
- Report the realized false alarm rate next to the 10 percent target, including when it
  is higher than the target. That is a finding, not a failure to hide.
- Never commit a number into a document that the script does not print.
- Keep the frozen data untouched. If a download is refreshed, say so in the pull request
  and regenerate `data/nigeria/SHA256SUMS` from inside that folder.

## 5. Before opening a pull request

```
python src/metrics.py      # self tests
python src/folds.py        # 1,452 cells and 355 rises
python src/baseline.py     # the reference numbers
```

CI runs the same three commands on every push, so a red check means one of them broke.
