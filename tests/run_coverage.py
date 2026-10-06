#!/usr/bin/env python3
"""Run unit/integration tests and enforce 80% line coverage without dependencies."""
from pathlib import Path
import tempfile
import trace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def run_tests():
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    return unittest.TextTestRunner(verbosity=2).run(suite)


def main():
    tracer = trace.Trace(count=True, trace=False)
    outcome = tracer.runfunc(run_tests)
    counts = {key: count for key, count in tracer.results().counts.items()
              if Path(key[0]).parent == ROOT / "scripts"}
    passed = outcome.wasSuccessful()
    with tempfile.TemporaryDirectory(prefix="chargepath-coverage-") as directory:
        trace.CoverageResults(counts=counts).write_results(show_missing=True, coverdir=directory)
        for name in ("build_updates", "sync_app_store", "build_share_cards"):
            lines = (Path(directory) / f"{name}.cover").read_text(encoding="utf-8").splitlines()
            covered = sum(line[:7].strip().rstrip(":").isdigit() for line in lines)
            missed = sum(line.startswith(">>>>>>") for line in lines)
            percent = covered / (covered + missed) * 100 if covered + missed else 0
            print(f"{name}: {percent:.1f}% line coverage ({covered}/{covered + missed})")
            passed = passed and percent >= 80
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
