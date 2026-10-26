"""Artificial geometry and separate behavioral expectations; no competition data.

This is a test adapter contract, not a production feature schema or a predictor.
Fixtures are intentionally small and idealized. See EVALUATION_PROTOCOL.md.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


Point = Tuple[float, float]


@dataclass(frozen=True)
class Player:
    team: Optional[str]
    xy: Point


@dataclass(frozen=True)
class Phase:
    code: str
    team: Optional[str] = None


@dataclass(frozen=True)
class Observation:
    frame: int
    half: int
    ball_xy: Optional[Point]
    players: Tuple[Player, ...]
    phases: Tuple[Phase, ...] = ()


@dataclass(frozen=True)
class Inputs:
    observations: Tuple[Observation, ...]
    fps: float = 10.0
    pitch_m: Point = (100.0, 60.0)


@dataclass(frozen=True)
class Interval:
    start: int
    stop: int
    label: str


@dataclass(frozen=True)
class Case:
    name: str
    inputs: Inputs
    expected: Tuple[Interval, ...]


def _moving(frame, team="H", half=1, missing=False, phases=()):
    """Co-moving player and ball; opponent is well separated. Metres, seconds."""
    x = 20.0 + frame / 10.0
    home_y, away_y = (25.0, 45.0) if team == "H" else (45.0, 25.0)
    return Observation(
        frame, half, None if missing else (x + 0.3, 25.0),
        (Player("H", (x, home_y)), Player("A", (x, away_y))), phases,
    )


def synthetic_cases():
    """Fresh immutable cases. Intent lives in Case.expected, never in Inputs.

    Exact boundaries are engineering contracts for these invented situations,
    not claims that tracking uniquely identifies control/referee decisions.
    """
    sustained = tuple(_moving(i) for i in range(80))

    deflection = list(sustained)
    # A single opponent proximity/contact event, then an immediate return to H.
    contact = deflection[35]
    deflection[35] = Observation(
        35, 1, contact.ball_xy,
        (contact.players[0], Player("A", (23.8, 25.0))),
    )

    missing = tuple(_moving(i, missing=30 <= i < 50) for i in range(80))
    turnover = tuple(
        _moving(i, team="H" if i < 50 else "A", missing=30 <= i < 50)
        for i in range(100)
    )
    loose = list(sustained)
    for i in range(30, 45):
        # Both players far from a moving loose ball, then H resumes control.
        loose[i] = Observation(i, 1, (23.0 + (i - 30) * 0.05, 33.0),
                               _moving(i).players)

    restart = []
    for i in range(100):
        if i < 30:
            restart.append(_moving(i))
        elif i < 60:
            # Outside touchline, stationary; a noisy set-piece phase is not
            # itself an exact start/end label. The ball is visible throughout.
            phases = (Phase("SET PIECES", "A"),) if 45 <= i < 70 else ()
            restart.append(Observation(i, 1, (23.0, -2.0),
                                       _moving(30).players, phases))
        else:
            phases = (Phase("SET PIECES", "A"),) if i < 70 else ()
            restart.append(_moving(i, team="A", phases=phases))

    halves = tuple(
        _moving(i) if i < 40 else
        _moving(i, team="A", half=2)
        for i in range(90)
    )
    # A defending-team phase must not be copied as the possession team.
    noisy_tags = tuple(_moving(i, phases=(Phase("DEFENDING", "A"),
                                         Phase("UNRECOGNIZED", None)))
                       for i in range(80))
    return (
        Case("sustained_control", Inputs(sustained), (Interval(0, 80, "H"),)),
        Case("transient_opponent_deflection", Inputs(tuple(deflection)),
             (Interval(0, 80, "H"),)),
        Case("missing_ball_inside_possession", Inputs(missing),
             (Interval(0, 80, "H"),)),
        Case("loose_ball_retains_control", Inputs(tuple(loose)),
             (Interval(0, 80, "H"),)),
        Case("controlled_turnover_after_gap", Inputs(turnover),
             (Interval(0, 50, "H"), Interval(50, 100, "A"))),
        Case("visible_dead_ball_then_restart", Inputs(tuple(restart)),
             (Interval(0, 30, "H"), Interval(30, 60, "D"),
              Interval(60, 100, "A"))),
        Case("half_boundary_resets_state", Inputs(halves),
             (Interval(0, 40, "H"), Interval(40, 90, "A"))),
        Case("noisy_phase_is_not_possession", Inputs(noisy_tags),
             (Interval(0, 80, "H"),)),
    )
