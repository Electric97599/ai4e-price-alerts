"""Measure each learned model's full calibration/scoring pass for each fold.

Peak resident memory is sampled for the model process and its child processes every 50 ms.
Very brief peaks between samples can be missed; the method and sampling interval are
written in docs/RESOURCES.md.
"""

import csv
import os
import platform
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "resources.csv")
DOC = os.path.join(ROOT, "docs", "RESOURCES.md")
WORK = os.path.join(ROOT, "outputs", "_resource_runs")
MODELS = {
    "sarima": ("src/sarima.py", []),
    "lightgbm": ("src/lightgbm_pipeline.py", []),
    "lightgbm_fx": ("src/lightgbm_pipeline.py", ["--with-fx"]),
}


def process_rss_mb(pid):
    """Return total RSS for the profiled process tree in MiB."""
    import psutil
    try:
        root = psutil.Process(int(pid))
        processes = [root] + root.children(recursive=True)
        total = 0
        for process in processes:
            try:
                total += process.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return total / (1024.0 * 1024.0)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def machine():
    import numpy
    import pandas
    import psutil
    import scipy
    import statsmodels
    import lightgbm

    return {
        "python": sys.version.split()[0], "platform": platform.platform(),
        "processor": platform.processor() or "not reported by OS",
        "logical_cpus": os.cpu_count(), "pandas": pandas.__version__,
        "psutil": psutil.__version__,
        "numpy": numpy.__version__, "scipy": scipy.__version__,
        "statsmodels": statsmodels.__version__,
        "lightgbm": lightgbm.__version__,
    }


def display_command(command):
    """Make a reproducible, repository-relative command string."""
    shown = []
    for index, part in enumerate(command):
        if index == 0 and os.path.normcase(part) == os.path.normcase(sys.executable):
            shown.append("python")
        elif os.path.isabs(part):
            try:
                relative = os.path.relpath(part, ROOT)
                shown.append(relative if relative != os.pardir and not relative.startswith(os.pardir + os.sep)
                             else part)
            except ValueError:
                shown.append(part)
        else:
            shown.append(part)
    return " ".join('"%s"' % part if " " in part else part for part in shown)


def measure(command, log_path):
    """Run direct child process, sample RSS every 50ms, and return wall time and peak RSS."""
    started = time.perf_counter()
    peak_mb = 0.0
    with open(log_path, "w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        while process.poll() is None:
            rss = process_rss_mb(process.pid)
            if rss is not None:
                peak_mb = max(peak_mb, rss)
            time.sleep(0.05)
        # Catch a final sample before the process handle disappears when possible.
        rss = process_rss_mb(process.pid)
        if rss is not None:
            peak_mb = max(peak_mb, rss)
        return_code = process.returncode
    wall = time.perf_counter() - started
    if return_code:
        with open(log_path, encoding="utf-8", errors="replace") as fh:
            tail = "".join(fh.readlines()[-80:])
        raise SystemExit("profile command failed (%d): %s\n%s" %
                         (return_code, " ".join(command), tail))
    if peak_mb <= 0:
        raise SystemExit("could not sample process memory for %s" % " ".join(command))
    return {"wall_seconds": wall, "peak_rss_mb": peak_mb,
            "command": display_command(command)}


def memory_total_gb():
    import psutil
    return round(psutil.virtual_memory().total / (1024.0 ** 3), 2)


def write_report(rows, versions):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["model", "fold", "wall_seconds", "peak_rss_mb", "command"])
        writer.writeheader()
        writer.writerows(rows)
    ram = memory_total_gb()
    doc = ["# Model resource measurements", "",
           "Measurements are from model fitting and scoring rerun separately for each fold. "
           "Peak process-tree RSS is sampled every 50 ms; a transient peak between samples can be missed. "
           "Machine background load was not controlled, so runtimes are descriptive rather than a hardware-independent guarantee.", "",
           "## Machine and software", "",
           "| Item | Value |", "|---|---|"]
    for key, value in versions.items():
        doc.append("| %s | %s |" % (key, value if value is not None else "not reported"))
    doc.append("| Physical memory (GB) | %s |" % (ram if ram is not None else "not reported"))
    doc.extend(["", "## Per-fold full pass", "",
                "| Model | Fold | Wall seconds | Peak process-tree RSS (MiB) |", "|---|---:|---:|---:|"])
    for row in rows:
        doc.append("| %s | %s | %.2f | %.1f |" %
                    (row["model"], row["fold"], row["wall_seconds"], row["peak_rss_mb"]))
    doc.extend(["", "## Fixed fitting settings", "",
                "SARIMA uses the candidate orders and 12-month seasonal difference in `src/model_config.py`, "
                "with a 60-calendar-month rolling fit window and a minimum of 24 observed prices. "
                "LightGBM uses the fixed parameters in that file, with one CPU worker for repeatability.", "",
                "## Reproduce", "",
                "Run `python src/resources.py` from the repository root after installing `requirements.txt`. "
                "The benchmark writes the fold-specific temporary score files under `outputs/_resource_runs/` "
                "and keeps the measurements in `outputs/resources.csv`.", ""])
    with open(DOC, "w", encoding="utf-8") as fh:
        fh.write("\n".join(doc))


def main():
    import folds
    os.makedirs(WORK, exist_ok=True)
    versions = machine()
    print("Machine/software: %s" % versions)
    rows = []
    for model, (script, extra) in MODELS.items():
        for fold in folds.FOLDS:
            label = fold["fold"]
            score_path = os.path.join(WORK, "%s_fold%s.csv" % (model, label))
            log_path = os.path.join(WORK, "%s_fold%s.log" % (model, label))
            command = [sys.executable, script, "--fold", str(label), "--output", score_path, *extra]
            print("\nProfiling %s fold %s" % (model, label), flush=True)
            measure_out = measure(command, log_path)
            row = {"model": model, "fold": str(label), **measure_out}
            rows.append(row)
            print("%s fold %s: %.1f seconds, %.1f MiB peak RSS" %
                  (model, label, row["wall_seconds"], row["peak_rss_mb"]), flush=True)
    write_report(rows, versions)
    print("\nwrote outputs/resources.csv and docs/RESOURCES.md")


if __name__ == "__main__":
    main()
