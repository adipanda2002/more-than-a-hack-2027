"""Transparent offline team-control persistence over shared tactical features."""
from dataclasses import dataclass, fields
import math

import numpy as np

from possession import dead_ball
from possession.features import Features, features_from_inputs


@dataclass(frozen=True)
class Config:
    control_radius_m: float = 2.0
    opponent_margin_m: float = 0.5
    control_seconds: float = 0.4
    max_control_ball_mps: float = 12.0
    retain_seconds: float = 3.0

    def __post_init__(self):
        if any(not math.isfinite(getattr(self, f.name)) or getattr(self, f.name) <= 0
               for f in fields(self)):
            raise ValueError('invalid temporal configuration')


@dataclass(frozen=True)
class Result:
    labels: np.ndarray
    control: np.ndarray  # -1 unknown; 0 home; 1 away; confirmed direct evidence only
    assessed: np.ndarray
    dead_state: np.ndarray


def _confirm_runs(candidate, fps, seconds):
    """Backdate sufficiently long constant-team runs, with no gap filling."""
    confirmed = np.full(len(candidate), -1, dtype=np.int8)
    boundaries = np.flatnonzero(np.r_[True, candidate[1:] != candidate[:-1], True])
    steps = max(1, math.ceil(seconds * fps))
    for start, stop in zip(boundaries[:-1], boundaries[1:]):
        if candidate[start] >= 0 and stop - start >= steps + 1:
            confirmed[start:stop] = candidate[start]
    return confirmed


def infer(features: Features, config=Config(), dead_config=dead_ball.Config()):
    """Return H/A/D/X, preserving team state only within assessed published halves.

    Proximity is a control proxy, not a measured touch or referee decision. No phase
    label, match-specific frame, fixture identity or expected outcome enters decoding.
    T06 UNKNOWN never implies D; ownership can be supported by stationary close control.
    """
    dead = dead_ball.infer(features, dead_config)
    n, fps = len(features['frame']), float(features.fps)
    xy = np.asarray(features['ball_xy_m'])
    pitch = np.asarray(features.pitch_m)
    distances = np.asarray(features['team_nearest_ball_distance_m'])
    counts = np.asarray(features['team_observed_count'])
    speed = np.asarray(features['ball_speed_mps'])
    if distances.shape != (n, 2) or counts.shape != (n, 2) or speed.shape != (n,):
        raise ValueError('invalid control feature shape')
    inside = (features['ball_observed'] & np.isfinite(xy).all(axis=1)
              & ((xy >= 0) & (xy <= pitch)).all(axis=1))
    continuous = np.r_[False, inside[1:] & inside[:-1]
                       & dead.assessed[1:] & dead.assessed[:-1]
                       & (features['half'][1:] == features['half'][:-1])]
    eligible = (inside & dead.assessed & (dead.state != dead_ball.State.DEAD)
                & np.isfinite(distances).all(axis=1) & (distances >= 0).all(axis=1)
                & (counts > 0).all(axis=1)
                & (~continuous | ~np.isfinite(speed) | (speed <= config.max_control_ball_mps)))
    candidate = np.full(n, -1, dtype=np.int8)
    for team in range(2):
        close = ((distances[:, team] <= config.control_radius_m)
                 & (distances[:, 1 - team] - distances[:, team] >= config.opponent_margin_m))
        candidate[eligible & close] = team
    half = features['half']
    boundaries = np.flatnonzero(np.r_[True, (half[1:] != half[:-1]) |
                                     (dead.assessed[1:] != dead.assessed[:-1]), True])
    labels = np.full(n, 'X', dtype='<U1')
    control = np.full(n, -1, dtype=np.int8)
    for start, stop in zip(boundaries[:-1], boundaries[1:]):
        if not dead.assessed[start]:
            continue
        control[start:stop] = _confirm_runs(candidate[start:stop], fps, config.control_seconds)
        owner, last = -1, -1
        for index in range(start, stop):
            if dead.state[index] == dead_ball.State.DEAD:
                labels[index] = 'D'
                owner, last = -1, -1
                continue
            if control[index] >= 0:
                owner, last = int(control[index]), index
            elif last < 0 or (index - last) / fps > config.retain_seconds:
                owner = -1
            if owner >= 0:
                labels[index] = 'HA'[owner]
    return Result(labels, control, dead.assessed.copy(), dead.state.copy())


def predict(inputs, config=Config()):
    """T04 harness adapter; only artificial observations reach the feature builder."""
    return infer(features_from_inputs(inputs), config).labels
