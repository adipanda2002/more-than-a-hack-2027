#!/usr/bin/env python3
"""Run the frozen T08 synthetic robustness and engineering gates locally."""

import argparse
import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from evaluation.behavioral_harness import check_prediction, expected_labels
from evaluation.behavioral_cases import Inputs, Observation, Player, synthetic_cases
from evaluation.robustness_cases import limitation_witnesses, robustness_cases
from possession.features import _normalized_to_pitch_m, features_from_inputs
from possession.temporal import Config, infer, predict

CONFIGS = {"C0": Config(), "C1": Config(control_seconds=.01), "C2": Config(retain_seconds=.01)}
ARRAY_FIELDS = ("labels", "control", "assessed", "dead_state")
SYNTH_CACHE = ROOT / "data" / "experiments" / "t08-synthetic.json"
RESOURCE_LIMIT = 1024 ** 3
CACHE_SCHEMA = 3


def source_digest():
    paths = ("possession/temporal.py", "possession/dead_ball.py", "possession/features.py",
             "possession/submission.py", "evaluation/validate_submission.py",
             "evaluation/behavioral_cases.py", "evaluation/behavioral_harness.py",
             "evaluation/robustness_cases.py", "scripts/run_robustness.py",
             "tests/test_robustness.py")
    h = hashlib.sha256()
    for name in sorted(paths):
        h.update(name.encode("utf-8") + b"\0")
        h.update((ROOT / name).read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def _path_is_safe(path):
    """Validate cache location before any read, mkdir, temporary write or replacement."""
    path = Path(path)
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        return False
    if ".." in path.parts or rel != Path("data/experiments/t08-synthetic.json"):
        return False
    if path.exists() and not path.is_file():
        return False
    # lexically inspect every existing component, catching dangling symlinks too.
    current = ROOT
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            return False
    ignored = subprocess.run(["git", "check-ignore", "-q", "--", str(rel)], cwd=ROOT,
                             capture_output=True, check=False)
    tracked = subprocess.run(["git", "ls-files", "--", str(rel)], cwd=ROOT,
                             capture_output=True, check=False)
    return ignored.returncode == 0 and tracked.returncode == 0 and not tracked.stdout


def _swap_inputs(inputs):
    return Inputs(tuple(Observation(o.frame, o.half, o.ball_xy,
                                    tuple(Player({"H": "A", "A": "H"}.get(p.team, p.team), p.xy)
                                          for p in o.players),
                                    tuple(type(ph)(ph.code, {"H": "A", "A": "H"}.get(ph.team, ph.team))
                                          for ph in o.phases)) for o in inputs.observations),
                  inputs.fps, inputs.pitch_m)


def _reverse_slots(inputs):
    return Inputs(tuple(Observation(o.frame, o.half, o.ball_xy, tuple(reversed(o.players)), o.phases)
                        for o in inputs.observations), inputs.fps, inputs.pitch_m)


def _prepend_empty(case):
    fps = case.inputs.fps
    prefix = tuple(Observation(i, 0, None, ()) for i in range(round(2 * fps)))
    shifted = tuple(Observation(o.frame + len(prefix), o.half, o.ball_xy, o.players, o.phases)
                    for o in case.inputs.observations)
    return Inputs(prefix + shifted, fps, case.inputs.pitch_m), len(prefix)


def _converted_features(inputs):
    pitch = inputs.pitch_m
    rows = []
    for o in inputs.observations:
        ball = None if o.ball_xy is None else _normalized_to_pitch_m(
            o.ball_xy[0] / pitch[0], o.ball_xy[1] / pitch[1], pitch)
        players = tuple(Player(p.team, _normalized_to_pitch_m(p.xy[0] / pitch[0],
                                                               p.xy[1] / pitch[1], pitch))
                        for p in o.players)
        rows.append(Observation(o.frame, o.half, ball, players, o.phases))
    return features_from_inputs(Inputs(tuple(rows), inputs.fps, pitch))


def _array_equal(a, b, tolerance=0.0):
    if a.shape != b.shape:
        return False
    if a.dtype.kind in "fc" or b.dtype.kind in "fc":
        return bool(np.allclose(a, b, rtol=0.0, atol=tolerance, equal_nan=True))
    return bool(np.array_equal(a, b))


def _result_equal(a, b):
    return all(_array_equal(getattr(a, name), getattr(b, name)) for name in ARRAY_FIELDS)


def _contract_report(config):
    cases = tuple(synthetic_cases()) + tuple(robustness_cases())
    outcomes = {}
    for case in cases:
        outcomes[case.name] = check_prediction(case, predict(case.inputs, config)).__dict__
    return outcomes, cases


def synthetic_results():
    report = {"schema": CACHE_SCHEMA, "digest": source_digest(),
              "python": platform.python_version(), "numpy": np.__version__,
              "platform": platform.platform(), "config_ids": list(CONFIGS),
              "fixtures": {}, "invariances": {}, "limitations": {}, "resources": {}}
    for config_id, config in CONFIGS.items():
        fixture_rows, cases = _contract_report(config)
        report["fixtures"][config_id] = fixture_rows
        checks = {}
        for case in cases:
            original = infer(features_from_inputs(case.inputs), config)
            swapped = infer(features_from_inputs(_swap_inputs(case.inputs)), config)
            expected_labels_swapped = np.asarray(
                [{"H": "A", "A": "H", "D": "D", "X": "X"}[x] for x in original.labels])
            expected_control_swapped = np.asarray(
                [-1 if int(x) < 0 else 1 - int(x) for x in original.control], dtype=original.control.dtype)
            checks[case.name + ":team_swap"] = bool(
                np.array_equal(swapped.labels, expected_labels_swapped)
                and np.array_equal(swapped.control, expected_control_swapped)
                and np.array_equal(swapped.assessed, original.assessed)
                and np.array_equal(swapped.dead_state, original.dead_state))
            reversed_result = infer(features_from_inputs(_reverse_slots(case.inputs)), config)
            checks[case.name + ":slot_reverse"] = _result_equal(original, reversed_result)
            repeated = infer(features_from_inputs(case.inputs), config)
            checks[case.name + ":repeat_all_arrays"] = _result_equal(original, repeated)
            if case.name.startswith(("R01_", "R03_", "R05_", "R06_")) and case.inputs.fps == 10:
                prepended, offset = _prepend_empty(case)
                shifted = infer(features_from_inputs(prepended), config)
                checks[case.name + ":time_translation"] = bool(
                    np.all(shifted.labels[:offset] == "X") and all(
                        _array_equal(getattr(shifted, field)[offset:], getattr(original, field))
                        for field in ARRAY_FIELDS))
            if case.name.startswith(("R01_", "R05_")):
                base_features = features_from_inputs(case.inputs)
                converted = _converted_features(case.inputs)
                for key in ("team_nearest_ball_distance_m", "ball_speed_mps", "player_speed_mps"):
                    checks[case.name + ":metric:" + key] = _array_equal(
                        base_features[key], converted[key], 1e-12)
                checks[case.name + ":metric:labels"] = bool(np.array_equal(
                    original.labels, infer(converted, config).labels))
        report["invariances"][config_id] = checks
        report["limitations"][config_id] = _limit_report(config)
    return report


def _limit_report(config):
    rows = {}
    for witness_id, case in limitation_witnesses():
        actual = predict(case.inputs, config)
        expected = expected_labels(case)
        mismatch = sum(a != b for a, b in zip(actual, expected))
        row = {"passed": mismatch == 0, "mismatches": mismatch}
        if witness_id == "L02_missing_stoppage":
            result = infer(features_from_inputs(case.inputs), config)
            intended = [v == "D" for v in expected]
            row["x_expiry_present"] = any(intended[i] and result.labels[i] == "X"
                                          for i in range(len(expected)))
            row["dead_established"] = any(intended[i] and int(result.dead_state[i]) == 2
                                          for i in range(len(expected)))
        rows[witness_id] = row
    return rows


def _resource_child(config_id):
    n, fps = 199319, 25
    observations = []
    for i in range(n):
        t = i / fps
        x = 20.0 + 5.0 * math.sin(t / 10.0)
        observations.append(Observation(i, 1, (x + .3, 25.0),
                                        (Player("H", (x, 25.0)), Player("A", (x, 45.0)))))
    inputs = Inputs(tuple(observations), fps=fps)
    start = time.perf_counter()
    features = features_from_inputs(inputs)
    feature_seconds = time.perf_counter() - start
    del observations, inputs
    start = time.perf_counter()
    result = infer(features, CONFIGS[config_id])
    decode_seconds = time.perf_counter() - start
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != "darwin":
        rss *= 1024
    print(json.dumps({"feature_seconds": feature_seconds, "decode_seconds": decode_seconds,
                      "peak_rss_bytes": int(rss), "labels_valid": bool(np.isin(
                          result.labels, ["H", "A", "D", "X"]).all())}, sort_keys=True))


def resource_check(config_id):
    try:
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                               "--resource-child", config_id], cwd=ROOT, capture_output=True,
                              text=True, timeout=120, check=False)
        if proc.returncode != 0 or not proc.stdout.strip():
            return {"passed": False, "reason": "child_failure"}
        row = json.loads(proc.stdout.strip().splitlines()[-1])
        if not all(k in row for k in ("feature_seconds", "decode_seconds", "peak_rss_bytes", "labels_valid")):
            return {"passed": False, "reason": "incomplete_result"}
        row["passed"] = bool(row["labels_valid"]
                             and 0 <= row["peak_rss_bytes"] < RESOURCE_LIMIT
                             and 0 <= row["feature_seconds"] < 120
                             and 0 <= row["decode_seconds"] < 120
                             and row["feature_seconds"] + row["decode_seconds"] < 120)
        if not row["passed"]:
            row["reason"] = "limit"
        return row
    except subprocess.TimeoutExpired:
        return {"passed": False, "reason": "timeout"}
    except Exception:
        return {"passed": False, "reason": "child_failure"}


def _expected_invariance_names(cases):
    names = set()
    for case in cases:
        names.update(case.name + ":" + suffix for suffix in
                     ("team_swap", "slot_reverse", "repeat_all_arrays"))
        if case.name.startswith(("R01_", "R03_", "R05_", "R06_")) and case.inputs.fps == 10:
            names.add(case.name + ":time_translation")
        if case.name.startswith(("R01_", "R05_")):
            names.update(case.name + ":metric:" + key for key in
                         ("team_nearest_ball_distance_m", "ball_speed_mps",
                          "player_speed_mps", "labels"))
    return names


def _outcome_valid(row, length):
    count = row.get("mismatches")
    return (type(row.get("passed")) is bool and type(count) is int
            and 0 <= count <= length and row["passed"] == (count == 0))


def _report_valid(report, digest=None):
    digest = source_digest() if digest is None else digest
    try:
        if (report.get("schema") != CACHE_SCHEMA or report.get("digest") != digest
                or report.get("python") != platform.python_version()
                or report.get("numpy") != np.__version__
                or report.get("platform") != platform.platform()
                or report.get("config_ids") != list(CONFIGS)):
            return False
        fixtures = report["fixtures"]
        invariances = report["invariances"]
        limitations = report["limitations"]
        resources = report["resources"]
        if any(set(m) != set(CONFIGS) for m in (fixtures, invariances, limitations, resources)):
            return False
        cases = tuple(synthetic_cases()) + tuple(robustness_cases())
        lengths = {c.name: len(c.inputs.observations) for c in cases}
        invariant_names = _expected_invariance_names(cases)
        witnesses = dict(limitation_witnesses())
        for cid in CONFIGS:
            if set(fixtures[cid]) != set(lengths) or set(invariances[cid]) != invariant_names:
                return False
            for name, result in fixtures[cid].items():
                if not _outcome_valid(result, lengths[name]):
                    return False
            if any(type(v) is not bool for v in invariances[cid].values()):
                return False
            if set(limitations[cid]) != set(witnesses):
                return False
            for name, witness in limitations[cid].items():
                if not _outcome_valid(witness, len(witnesses[name].inputs.observations)):
                    return False
            if any(type(limitations[cid]["L02_missing_stoppage"].get(key)) is not bool
                   for key in ("x_expiry_present", "dead_established")):
                return False
        for row in resources.values():
            if not isinstance(row, dict) or not isinstance(row.get("passed"), bool):
                return False
            if row["passed"] is False:
                if row.get("reason") not in {"timeout", "child_failure", "incomplete_result",
                                               "limit", "not_run_after_failure"}:
                    return False
                continue
            if (not isinstance(row.get("peak_rss_bytes"), int)
                    or not isinstance(row.get("feature_seconds"), (int, float))
                    or not isinstance(row.get("decode_seconds"), (int, float))
                    or not math.isfinite(row["feature_seconds"])
                    or not math.isfinite(row["decode_seconds"])
                    or row["peak_rss_bytes"] < 0 or row["peak_rss_bytes"] >= RESOURCE_LIMIT
                    or row["feature_seconds"] < 0 or row["decode_seconds"] < 0
                    or row["feature_seconds"] + row["decode_seconds"] >= 120
                    or row.get("labels_valid") is not True):
                return False
        return True
    except (KeyError, TypeError, AttributeError):
        return False


def _load_cache():
    if not _path_is_safe(SYNTH_CACHE) or not SYNTH_CACHE.is_file():
        return None
    try:
        report = json.loads(SYNTH_CACHE.read_text(encoding="utf-8"))
        return report if _report_valid(report) else None
    except Exception:
        return None


def _save_cache(report):
    if not _path_is_safe(SYNTH_CACHE):
        raise ValueError("unsafe T08 cache path")
    SYNTH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    # Recheck after mkdir, then use a unique same-directory temporary for atomic replace.
    if not _path_is_safe(SYNTH_CACHE):
        raise ValueError("unsafe T08 cache path")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=SYNTH_CACHE.parent,
                                         prefix=".t08-", suffix=".tmp", delete=False) as stream:
            temp_path = Path(stream.name)
            json.dump(report, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        if not _path_is_safe(SYNTH_CACHE):
            raise ValueError("unsafe T08 cache path")
        os.replace(temp_path, SYNTH_CACHE)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _eligible(report):
    """Return per-config gates and whether C0 may enter full-match validation."""
    if not _report_valid(report):
        return None
    gates = {}
    for cid in CONFIGS:
        semantic = all(row["passed"] for row in report["fixtures"][cid].values())
        invariance = all(report["invariances"][cid].values())
        resource_ok = report["resources"][cid].get("passed") is True
        gates[cid] = {"semantic": semantic, "invariance": invariance,
                      "resource": resource_ok, "eligible": semantic and invariance and resource_ok}
    return gates


def _run_full_match():
    from possession.features import build_features
    from possession.submission import checked_output, write_csv, OUTPUT_ROOT
    paths = (OUTPUT_ROOT / "t08" / "c0-first.csv", OUTPUT_ROOT / "t08" / "c0-second.csv")
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            first_path, second_path = map(checked_output, paths)
            features, _ = build_features()
            if not np.array_equal(features["frame"], np.arange(199319)):
                raise ValueError("timeline")
            first = infer(features, CONFIGS["C0"])
            second = infer(features, CONFIGS["C0"])
            if not _result_equal(first, second):
                raise ValueError("nondeterminism")
            assessed = features["graded"] & (features["half"] > 0)
            from possession.dead_ball import State
            if (not np.isin(first.labels, ["H", "A", "D", "X"]).all()
                    or not np.array_equal(first.assessed, assessed)
                    or np.any(first.labels[~assessed] != "X")
                    or not np.array_equal(first.labels == "D", first.dead_state == State.DEAD)):
                raise ValueError("invariant")
            write_csv(first_path, features["frame"], first.labels)
            write_csv(second_path, features["frame"], second.labels)
            if first_path.read_bytes() != second_path.read_bytes():
                raise ValueError("bytes")
            validator = [sys.executable, str(ROOT / "evaluation/validate_submission.py")]
            validations = [subprocess.run(validator + [str(p)], cwd=ROOT, capture_output=True,
                                          check=False) for p in paths]
            if any(p.returncode != 0 for p in validations):
                raise ValueError("validator")
        return True
    except Exception:
        return False


def _execute(full_match=False):
    report = _load_cache()
    if report is None:
        report = synthetic_results()
        for cid in CONFIGS:
            report["resources"][cid] = resource_check(cid)
            if not report["resources"][cid].get("passed"):
                # Complete accounting records explicit missing candidates as failures.
                for remaining in list(CONFIGS)[list(CONFIGS).index(cid) + 1:]:
                    report["resources"][remaining] = {"passed": False, "reason": "not_run_after_failure"}
                break
        _save_cache(report)
    gates = _eligible(report)
    if gates is None:
        return report, None, "invalid_cache"
    if any(not gate["invariance"] for gate in gates.values()):
        return report, gates, "invariance_failure"
    if any(not gate["resource"] for gate in gates.values()):
        return report, gates, "resource_failure"
    if not gates["C0"]["semantic"]:
        return report, gates, "c0_gate_failure"
    production = "NOT_REQUESTED"
    if full_match:
        production = "PASS" if _run_full_match() else "FAIL"
        report["production_c0"] = production
        # Production result is safe fixed status; persist it with the same atomic cache path.
        _save_cache(report)
    return report, gates, ("production_failure" if production == "FAIL" else "ok")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-match", action="store_true")
    parser.add_argument("--resource-child", choices=tuple(CONFIGS), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.resource_child:
        _resource_child(args.resource_child)
        return 0
    report, gates, status = _execute(full_match=args.full_match)
    if report:
        print("T08 source digest: {}".format(report.get("digest", "invalid")))
        print("Python {} / NumPy {} / {}".format(report.get("python", "unknown"),
              report.get("numpy", "unknown"), report.get("platform", "unknown")))
        for cid in CONFIGS:
            fixtures = report.get("fixtures", {}).get(cid, {})
            inv = report.get("invariances", {}).get(cid, {})
            passed = sum(v.get("passed") is True for v in fixtures.values())
            mismatches = sum(v.get("mismatches", 0) for v in fixtures.values())
            print("{} semantic: {}/{} pass, {} mismatches; invariance failures: {}".format(
                cid, passed, len(fixtures), mismatches, sum(v is not True for v in inv.values())))
            row = report.get("resources", {}).get(cid, {})
            if row.get("passed") is True:
                print("{} resource: PASS feature {:.3f}s, decode {:.3f}s, peak {} bytes".format(
                    cid, row["feature_seconds"], row["decode_seconds"], row["peak_rss_bytes"]))
            else:
                print("{} resource: FAIL ({})".format(cid, row.get("reason", "incomplete")))
            for name, witness in report.get("limitations", {}).get(cid, {}).items():
                print("{} {}: {} ({} mismatches)".format(cid, name,
                    "PASS" if witness.get("passed") else "EXPECTED LIMITATION",
                    witness.get("mismatches", "unknown")))
        if args.full_match:
            print("C0 full-match fixed checks: {}".format(report.get("production_c0", "FAIL")))
    if status != "ok":
        print("T08 gate: FAIL ({})".format(status.split(":")[0]))
        return 1
    if gates is None or any(not gate["invariance"] for gate in gates.values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
