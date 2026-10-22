# Model resource measurements

Measurements are from model fitting and scoring rerun separately for each fold. Peak process-tree RSS is sampled every 50 ms; a transient peak between samples can be missed. Machine background load was not controlled, so runtimes are descriptive rather than a hardware-independent guarantee.

## Machine and software

| Item | Value |
|---|---|
| python | 3.12.14 |
| platform | Windows-11-10.0.26300-SP0 |
| processor | Intel64 Family 6 Model 170 Stepping 4, GenuineIntel |
| logical_cpus | 22 |
| pandas | 2.2.3 |
| psutil | 7.2.2 |
| numpy | 2.1.3 |
| scipy | 1.17.1 |
| statsmodels | 0.14.4 |
| lightgbm | 4.7.0 |
| Physical memory (GB) | 31.47 |

## Per-fold full pass

| Model | Fold | Wall seconds | Peak process-tree RSS (MiB) |
|---|---:|---:|---:|
| sarima | 1 | 220.77 | 159.2 |
| sarima | 2 | 302.27 | 157.7 |
| sarima | 3 | 281.33 | 156.6 |
| lightgbm | 1 | 13.22 | 171.2 |
| lightgbm | 2 | 13.67 | 172.2 |
| lightgbm | 3 | 15.33 | 172.2 |
| lightgbm_fx | 1 | 21.34 | 172.2 |
| lightgbm_fx | 2 | 12.94 | 171.8 |
| lightgbm_fx | 3 | 12.91 | 173.1 |

## Fixed fitting settings

SARIMA uses the candidate orders and 12-month seasonal difference in `src/model_config.py`, with a 60-calendar-month rolling fit window and a minimum of 24 observed prices. LightGBM uses the fixed parameters in that file, with one CPU worker for repeatability.

## Reproduce

Run `python src/resources.py` from the repository root after installing `requirements.txt`. The benchmark writes the fold-specific temporary score files under `outputs/_resource_runs/` and keeps the measurements in `outputs/resources.csv`.
