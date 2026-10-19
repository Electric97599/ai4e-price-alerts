# On ramp: Jean Chrisostome Dufitumukiz (jeanchrd)

## Your two tasks

- **#8 Penalty sensitivity and subgroup tables**, week 13.
- **#9 Timing and memory of a full scoring pass**, week 13.

Both run on the results the modelling tasks produce, so start by building the code against
the reference output in `outputs/baseline_scores.csv`. When the real model score files
appear, the same scripts run unchanged.

Both starters exist and run: `src/report_tables.py` reads the fold table and stops at
`penalty_table`, and `src/resources.py` prints the machine and library versions and stops at
the peak memory measurement. Run them first to see exactly what is missing.

## Read in this order

1. `AGENTS.md`: the rules and the numbers that must not drift.
2. `docs/CONTEXT.md`, section "The measures": what the penalty is and what it is not.
3. `src/metrics.py`: `weighted_penalty` and `mean_absolute_error` already exist. Use them.
4. `outputs/baseline_scores.csv`: the shape you will be reading.

## Task #8, what to build

`src/report_tables.py`:

- The weighted penalty at k = 1, 3 and 5, so the ranking is shown to survive or fail rather
  than resting on one assumed weight. The weights are assumptions, not measured costs, and
  every table says so in its caption.
- Subgroup tables: by state inside each window, and state and commodity pooled across the
  three windows. Check the group sizes before choosing a pooling threshold: about 472 cells
  over 44 series is roughly eleven each, so a rule of "pool groups under 30 cells" would
  collapse the whole table inside one window. Report the sizes that actually exist.
- Write markdown for the report plus a CSV, and state the cell count on every table.

## Task #9, what to build

`src/resources.py`:

- Wall clock and peak memory for a full pass of each model across the three folds, on the
  machine the group actually uses, not a cloud instance nobody will reproduce.
- Write `docs/RESOURCES.md`: the numbers, the interpreter and library versions, the machine
  specification, and the command that reproduces it.

Done when rerunning the script gives the same picture.

## Watch for

- A penalty table computed on different cell sets across models is a false comparison.
  State coverage beside every column, or restrict to common cells.
- Fold 1 calibrates on 260 cells, not 472. A per fold table that hides that invites the
  question.
- Timing numbers taken while another job is running on the same laptop are still fine, as
  long as the machine state is written down beside them.

## Paste this into your AI assistant

> Read AGENTS.md, docs/CONTEXT.md and docs/on-ramp/dufitumukiz.md before touching anything.
> My tasks are issues #8 and #9. Build against outputs/baseline_scores.csv first. Every
> table must state its cell count, and the penalty weights must be described as assumptions.
> Show me the command output behind every number.
