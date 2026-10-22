"""Rebuild every coded deliverable from the frozen data snapshot, end to end.

Run after installing requirements with `python src/run_all.py`. Pass --skip-resources to
skip the optional per-fold runtime/memory benchmark; every data, model, scoring, alert,
report and app input is still rebuilt.
"""

import argparse
import os
import subprocess
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs")
MODELS = [
    ("seasonal", "baseline_scores.csv", "naive_score"),
    ("sarima", "sarima_scores.csv", "score"),
    ("lightgbm", "lightgbm_scores.csv", "score"),
    ("lightgbm_fx", "lightgbm_fx_scores.csv", "score"),
]


def run(path, *args):
    command = [sys.executable, path, *args]
    print("\n$ " + " ".join('"%s"' % part if " " in part else part for part in command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-resources", action="store_true",
                        help="omit the per-model/per-fold timing and memory reruns")
    parser.add_argument("--reuse-model-scores", action="store_true",
                        help="use existing validated model score files instead of refitting")
    args = parser.parse_args()

    run("scripts/check_data.py")
    run("src/panel.py")
    run("src/metrics.py")
    run("src/folds.py")
    run("src/features_fx.py")
    run("src/baseline.py")
    if args.reuse_model_scores:
        for _, filename, _ in MODELS[1:]:
            path = os.path.join(OUT, filename)
            if not os.path.isfile(path):
                raise SystemExit("cannot reuse missing model output: %s" % path)
        print("\nreusing the three existing learned-model score files", flush=True)
    else:
        run("src/sarima.py")
        run("src/lightgbm_pipeline.py")
        run("src/lightgbm_pipeline.py", "--with-fx")

    fold_tables = []
    for model, filename, column in MODELS:
        fold_path = os.path.join(OUT, "fold_table_%s.csv" % model)
        run("src/run_folds.py", "--scores", os.path.join("outputs", filename),
            "--column", column, "--model", model, "--output", fold_path)
        fold_tables.append(pd.read_csv(fold_path))
    combined = pd.concat(fold_tables, ignore_index=True)
    expected = {"seasonal", "sarima", "lightgbm", "lightgbm_fx"}
    if set(combined["model"].astype(str)) != expected or len(combined) != 12:
        raise SystemExit("fold table is incomplete: expected four rules across three folds")
    combined.to_csv(os.path.join(OUT, "fold_table.csv"), index=False)
    print("\ncombined fold table: 4 rules x 3 folds = 12 rows", flush=True)

    run("src/score_alerts.py")
    run("src/report_tables.py")
    if not args.skip_resources:
        run("src/resources.py")
    print("\nEnd-to-end pipeline completed. Streamlit app inputs are in outputs/.", flush=True)


if __name__ == "__main__":
    main()
