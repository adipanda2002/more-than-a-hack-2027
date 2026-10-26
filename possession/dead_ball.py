"""Offline geometry-only alive/dead/unknown evidence; no team ownership or labels."""
from dataclasses import dataclass, fields
from enum import IntEnum, IntFlag
import math

import numpy as np

from possession.features import Features, features_from_inputs


class State(IntEnum):
    UNKNOWN = 0
    ALIVE = 1
    DEAD = 2


class Evidence(IntFlag):
    MOTION = 1
    OUTSIDE_STATIONARY = 2
    RETAINED = 4
    SET_PIECE_CONTEXT = 8
    NOISY_TAG_CONTEXT = 16
    UNGRADED = 32
    STATIONARY_IN_PITCH = 64


@dataclass(frozen=True)
class Config:
    motion_seconds: float = 0.4
    motion_min_mps: float = 0.5
    motion_min_displacement_m: float = 0.2
    motion_coherence: float = 0.6
    max_ball_mps: float = 45.0
    outside_margin_m: float = 0.75
    stationary_seconds: float = 0.6
    stationary_diameter_m: float = 0.6
    retain_seconds: float = 3.0

    def __post_init__(self):
        if any(not math.isfinite(getattr(self, f.name)) or getattr(self, f.name) <= 0
               for f in fields(self)) or self.motion_coherence > 1:
            raise ValueError("invalid dead-ball configuration")
        if self.motion_min_mps > self.max_ball_mps:
            raise ValueError("inconsistent motion configuration")


@dataclass(frozen=True)
class Result:
    state: np.ndarray
    evidence: np.ndarray
    assessed: np.ndarray


def _confirmed_windows(xy, valid, fps, seconds, config, moving):
    """Union of complete confirmed windows; output includes their anchor frame.

    Endpoint displacement/path coherence rejects jitter; speed ceiling rejects jumps.
    Backdating uses observed window anchors, not a tag boundary or a frame constant.
    """
    n = len(xy)
    steps = max(1, math.ceil(seconds * fps))
    out = np.zeros(n, dtype=bool)
    if n <= steps:
        return out
    width = steps + 1
    windows = np.lib.stride_tricks.sliding_window_view
    good = windows(valid, width).all(axis=1)
    points = windows(xy, width, axis=0)
    if moving:
        distances = np.linalg.norm(np.diff(xy, axis=0), axis=1)
        path = windows(distances, steps).sum(axis=1)
        displacement = np.linalg.norm(xy[steps:] - xy[:-steps], axis=1)
        good &= windows(distances, steps).max(axis=1) * fps <= config.max_ball_mps
        good &= displacement >= max(config.motion_min_displacement_m,
                                     config.motion_min_mps * steps / fps)
        good &= displacement >= config.motion_coherence * path
    else:
        # Bounding-box diagonal is a conservative upper bound on point diameter.
        diameter = np.linalg.norm(points.max(axis=2) - points.min(axis=2), axis=1)
        good &= diameter <= config.stationary_diameter_m
    starts = np.flatnonzero(good)
    changes = np.zeros(n + 1, dtype=np.int32)
    np.add.at(changes, starts, 1)
    np.add.at(changes, starts + width, -1)
    return np.cumsum(changes[:-1]) > 0


def infer(features: Features, config=Config()):
    """Infer three-way state, assessed mask and nonprobabilistic evidence bits.

    Uses no team identities, expected states, half kickoff assumption or phase-derived
    labels. Only contiguous graded positive-half blocks share observation memory.
    """
    n, fps = len(features["frame"]), float(features.fps)
    if n == 0:
        raise ValueError("empty feature timeline")
    pitch = np.asarray(features.pitch_m, dtype=float)
    if not math.isfinite(fps) or fps <= 0 or pitch.shape != (2,) or not np.all(
            np.isfinite(pitch) & (pitch > 0)):
        raise ValueError("invalid feature units")
    xy = np.asarray(features["ball_xy_m"])
    seen = np.asarray(features["ball_observed"], dtype=bool) & np.isfinite(xy).all(axis=1)
    half = np.asarray(features["half"])
    assessed = np.asarray(features["graded"], dtype=bool) & (half > 0)
    if xy.shape != (n, 2) or half.shape != (n,) or assessed.shape != (n,):
        raise ValueError("invalid feature shape")
    state = np.full(n, State.UNKNOWN, dtype=np.uint8)
    evidence = np.zeros(n, dtype=np.uint8)
    evidence[~assessed] |= int(Evidence.UNGRADED)
    evidence[features["tag_set_piece"]] |= int(Evidence.SET_PIECE_CONTEXT)
    noisy = features["tag_conflict"] | features["tag_unknown_team"] | features["tag_unknown_code"]
    evidence[noisy] |= int(Evidence.NOISY_TAG_CONTEXT)
    breaks = np.r_[True, (half[1:] != half[:-1]) | (assessed[1:] != assessed[:-1]), True]
    boundaries = np.flatnonzero(breaks)
    for start, stop in zip(boundaries[:-1], boundaries[1:]):
        if not assessed[start]:
            continue
        ball = xy[start:stop]
        observed = seen[start:stop]
        inside = observed & ((ball >= 0) & (ball <= pitch)).all(axis=1)
        outside = observed & ((ball < -config.outside_margin_m) |
                              (ball > pitch + config.outside_margin_m)).any(axis=1)
        live = _confirmed_windows(ball, inside, fps, config.motion_seconds, config, True)
        dead = _confirmed_windows(ball, outside, fps, config.stationary_seconds, config, False)
        stationary = _confirmed_windows(ball, inside, fps, config.stationary_seconds, config, False)
        evidence[start:stop][stationary] |= int(Evidence.STATIONARY_IN_PITCH)
        previous, last = State.UNKNOWN, -1
        for local in range(stop - start):
            index = start + local
            if live[local]:
                previous, last = State.ALIVE, local
                evidence[index] |= int(Evidence.MOTION)
            elif dead[local]:
                previous, last = State.DEAD, local
                evidence[index] |= int(Evidence.OUTSIDE_STATIONARY)
            elif last >= 0 and (local - last) / fps <= config.retain_seconds:
                evidence[index] |= int(Evidence.RETAINED)
            else:
                previous = State.UNKNOWN
            state[index] = previous
    return Result(state, evidence, assessed.copy())


def infer_inputs(inputs, config=Config()):
    """Synthetic adapter: accepts only observations; returns no H/A predictions."""
    return infer(features_from_inputs(inputs), config)
