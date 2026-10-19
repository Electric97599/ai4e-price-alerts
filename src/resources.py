"""Starter for issue #9: measured wall clock and memory for a full scoring pass.

Owner: Dufitumukiz. Sheet: docs/on-ramp/dufitumukiz.md. Rules: AGENTS.md.

Output: docs/RESOURCES.md, plus outputs/resources.csv with one row per model and fold.

The report needs numbers, not adjectives: how long a full pass takes, how much memory it
peaks at, and on what machine with which library versions. Run it on the laptop the group
actually uses, and write the machine state down beside the numbers, including whether
anything else was running.

Run:  python src/resources.py --command "python src/baseline.py"
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "outputs", "resources.csv")
DOC = os.path.join(ROOT, "docs", "RESOURCES.md")


def machine():
    """What a reader needs to reproduce the timing."""
    import numpy
    import pandas
    versions = {"python": sys.version.split()[0], "pandas": pandas.__version__,
                "numpy": numpy.__version__, "machine": platform.platform()}
    try:
        import lightgbm
        versions["lightgbm"] = lightgbm.__version__
    except ImportError:
        versions["lightgbm"] = "not installed"
    try:
        import statsmodels
        versions["statsmodels"] = statsmodels.__version__
    except ImportError:
        versions["statsmodels"] = "not installed"
    return versions


def measure(command):
    """Run a command and return wall clock seconds and peak memory of the child.

    TODO(#9): implement the peak memory half. On Windows the portable route is
    psutil.Process(...).memory_info().rss sampled while the child runs, or
    resource.getrusage(RUSAGE_CHILDREN).ru_maxrss where it exists. Return a dict with
    wall_seconds and peak_mb, and say in the docstring which method you used, because
    peak RSS measured by sampling understates a short spike.
    """
    started = time.perf_counter()
    completed = subprocess.run(command, shell=True, cwd=ROOT, capture_output=True, text=True)
    wall = time.perf_counter() - started
    if completed.returncode != 0:
        raise SystemExit("command failed:\n%s" % completed.stderr[-800:])
    raise NotImplementedError("issue #9: add peak memory to this measurement, wall clock "
                              "alone was %.1f s" % wall)


def write_report(rows):
    """TODO(#9): write docs/RESOURCES.md from the rows and machine()."""
    raise NotImplementedError("issue #9: write docs/RESOURCES.md")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", action="append",
                        help="a command whose full pass should be timed; repeatable")
    args = parser.parse_args()
    # Default to this interpreter, so the timing is not distorted by a different python on
    # PATH that may not even have pandas installed.
    commands = args.command or ['"%s" src/baseline.py' % sys.executable]
    print(json.dumps(machine(), indent=1))
    rows = [measure(command) for command in commands]
    write_report(rows)


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as todo:
        print("Not built yet:", todo)
        print("See the docstring at the top of this file, and your sheet in docs/on-ramp/.")
        raise SystemExit(2)
