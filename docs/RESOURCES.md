# Model resource measurements

Measurements are from model fitting and scoring rerun separately for each fold. Peak process-tree RSS is sampled every 50 ms; a transient peak between samples can be missed. Machine background load was not controlled, so runtimes are descriptive rather than a hardware-independent guarantee.

## Machine and software

| Item | Value |
|---|---|
| python | 3.11.9 |
| platform | Windows-10-10.0.26300-SP0 |
| processor | Intel64 Family 6 Model 197 Stepping 2, GenuineIntel |
| logical_cpus | 16 |
| pandas | 2.2.3 |
| psutil | 7.2.2 |
| numpy | 2.1.3 |
| scipy | 1.17.1 |
| statsmodels | 0.14.4 |
| lightgbm | 4.7.0 |
| Physical memory (GB) | 31.43 |

## Per-fold full pass

| Model | Fold | Wall seconds | Peak process-tree RSS (MiB) |
|---|---:|---:|---:|
| sarima | 1 | 41.68 | 172.5 |
| sarima | 2 | 54.67 | 170.2 |
| sarima | 3 | 57.78 | 172.8 |
| lightgbm | 1 | 2.77 | 187.9 |
| lightgbm | 2 | 2.76 | 187.6 |
| lightgbm | 3 | 2.77 | 190.5 |
| lightgbm_fx | 1 | 2.77 | 188.8 |
| lightgbm_fx | 2 | 2.83 | 189.6 |
| lightgbm_fx | 3 | 2.88 | 190.4 |

## Fixed fitting settings

SARIMA uses the candidate orders and 12-month seasonal difference in `src/model_config.py`, with a 60-calendar-month rolling fit window and a minimum of 24 observed prices. LightGBM uses the fixed parameters in that file, with one CPU worker for repeatability.

## Reproduce

Run `python src/resources.py` from the repository root after installing `requirements.txt`. The benchmark writes the fold-specific temporary score files under `outputs/_resource_runs/` and keeps the measurements in `outputs/resources.csv`.
