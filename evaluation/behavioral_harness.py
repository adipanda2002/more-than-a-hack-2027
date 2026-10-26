"""Inject a future predictor into synthetic contracts; never reads match files."""

import argparse
import importlib
import math
from dataclasses import dataclass
from typing import Callable, Iterable, Tuple

from evaluation.behavioral_cases import Case, Inputs, synthetic_cases


LABELS = frozenset(("H", "A", "D", "X"))
Predictor = Callable[[Inputs], Iterable[str]]


def expected_labels(case: Case) -> Tuple[str, ...]:
    """Validate complete, non-overlapping half-open expectations and inputs."""
    observations = case.inputs.observations
    if not observations or not math.isfinite(case.inputs.fps) or case.inputs.fps <= 0:
        raise ValueError("empty observations or invalid fps")
    if any(ob.frame != i for i, ob in enumerate(observations)):
        raise ValueError("synthetic frame indices must be consecutive from zero")
    if any(ob.half not in (1, 2) for ob in observations):
        raise ValueError("unknown half")
    if any(a.half > b.half for a, b in zip(observations, observations[1:])):
        raise ValueError("halves must not run backwards")
    labels = []
    for interval in case.expected:
        if interval.label not in LABELS:
            raise ValueError("unknown expected label")
        if interval.start != len(labels) or interval.stop <= interval.start:
            raise ValueError("expectations must cover inputs without gaps or overlaps")
        labels.extend([interval.label] * (interval.stop - interval.start))
    if len(labels) != len(observations):
        raise ValueError("expectation length differs from input length")
    return tuple(labels)


@dataclass(frozen=True)
class Result:
    case: str
    passed: bool
    mismatches: int


def check_prediction(case: Case, prediction: Iterable[str]) -> Result:
    """Strict states, including X, before the official scorer's abstention fill.

    Exact frame comparisons include both sides of every intended transition.
    Invalid length or label is an interface failure, not a low quality score.
    """
    expected = expected_labels(case)
    actual = tuple(prediction)
    if len(actual) != len(expected):
        raise ValueError("prediction length differs from input length")
    if any(not isinstance(label, str) or label not in LABELS for label in actual):
        raise ValueError("prediction contains unknown labels")
    mismatches = sum(left != right for left, right in zip(expected, actual))
    return Result(case.name, mismatches == 0, mismatches)


def run_cases(predictor: Predictor, cases=None) -> Tuple[Result, ...]:
    """Only Inputs reach predictor; case name and expected states stay outside."""
    cases = synthetic_cases() if cases is None else tuple(cases)
    # Preflight the entire batch before any candidate code is invoked.
    for case in cases:
        expected_labels(case)
    return tuple(check_prediction(case, predictor(case.inputs)) for case in cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-contracts", action="store_true",
                      help="validate fixtures only; does not evaluate a candidate")
    mode.add_argument("--predictor", help="local Python module:function accepting Inputs")
    args = parser.parse_args()
    if args.check_contracts:
        cases = synthetic_cases()
        for case in cases:
            expected_labels(case)
        print("PASS: {} synthetic contracts; no candidate model evaluated".format(len(cases)))
        return 0
    module_name, function_name = args.predictor.split(":", 1)
    predictor = getattr(importlib.import_module(module_name), function_name)
    results = run_cases(predictor)
    for result in results:
        print("{}: {} ({} mismatches)".format(
            "PASS" if result.passed else "FAIL", result.case, result.mismatches))
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
