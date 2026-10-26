"""Frozen T08 artificial robustness fixtures and independent expectations."""

from dataclasses import replace

from evaluation.behavioral_cases import Case, Inputs, Interval, Observation, Player


def _rows(seconds, fps=10, team_fn=None, missing=(), dead=(), half_fn=None, noise=False):
    n = round(seconds * fps)
    out = []
    for i in range(n):
        t = i / fps
        team = team_fn(i, t) if team_fn else "H"
        hx, ax = (19.7 + t, 20.0 + t)
        hy, ay = 25.0, 45.0
        if team == "A":
            hx, ax, hy, ay = 20.0 + t, 19.7 + t, 45.0, 25.0
        ball = (20.0 + t, 25.0)
        if noise:
            ball = (ball[0] + .04 * (-1) ** i, ball[1] + .03 * (-1) ** (i // 2))
        if i in dead:
            ball = (23.0, -2.0)
        if i in missing:
            ball = None
        half = half_fn(i, t) if half_fn else 1
        out.append(Observation(i, half, ball,
                               (Player("H", (hx, hy)), Player("A", (ax, ay)))))
    return tuple(out)


def _case(name, rows, fps, boundaries):
    return Case(name, Inputs(rows, fps=fps), tuple(
        Interval(round(a * fps), round(b * fps), label) for a, b, label in boundaries))


def robustness_cases():
    cases = []
    for fps in (10, 5, 25):
        cases.append(_case("R01_turnover_{}fps".format(fps),
                           _rows(10, fps, lambda i, t: "H" if t < 5 else "A"), fps,
                           ((0, 5, "H"), (5, 10, "A"))))
    # One two-frame A contact against otherwise stable H control.
    rows = list(_rows(8))
    for i in (30, 31):
        o = rows[i]
        t = i / 10
        rows[i] = replace(o, players=(Player("H", (40, 25)), Player("A", (19.7 + t, 25))))
    cases.append(_case("R02_deflection", tuple(rows), 10, ((0, 8, "H"),)))
    for fps in (10, 5, 25):
        cases.append(_case("R03_occlusion_{}fps".format(fps),
                           _rows(10, fps, lambda i, t: "H" if t < 5 else "A",
                                 missing=range(round(3*fps), round(4*fps))), fps,
                           ((0, 5, "H"), (5, 10, "A"))))
    cases.append(_case("R04_long_gap", _rows(10, missing=range(20, 80)), 10,
                       ((0, 5, "H"), (5, 8, "X"), (8, 10, "H"))))
    for fps in (5, 10, 25):
        cases.append(_case("R05_restart_{}fps".format(fps), _rows(10, fps,
                           lambda i, t: "H" if t < 3 else ("A" if t >= 6 else "H"),
                           dead=range(round(3*fps), round(6*fps))), fps,
                       ((0, 3, "H"), (3, 6, "D"), (6, 10, "A"))))
        cases.append(_case("R06_half_reset_{}fps".format(fps), _rows(10, fps,
                           lambda i, t: "H" if t < 4 else ("A" if t >= 6 else "H"),
                           missing=range(round(4*fps), round(6*fps)),
                           half_fn=lambda i, t: 1 if t < 4 else 2), fps,
                       ((0, 4, "H"), (4, 6, "X"), (6, 10, "A"))))
    cases.append(_case("R07_noise", _rows(10, 10,
                           lambda i, t: "H" if t < 5 else "A", noise=True), 10,
                       ((0, 5, "H"), (5, 10, "A"))))
    return tuple(cases)


def limitation_witnesses():
    # Static ball and players: share exactly the same observation inputs between intents.
    base = tuple(Observation(i, 1, (20, 25), (Player("H", (19.7, 25)),
                                              Player("A", (20, 45)))) for i in range(80))
    return (("L01_live_H", Case("L01_live_H", Inputs(base), (Interval(0, 80, "H"),))),
            ("L01_stoppage_D", Case("L01_stoppage_D", Inputs(base), (Interval(0, 80, "D"),))),
            ("L02_missing_stoppage", _case("L02_missing_stoppage",
                 _rows(8, missing=range(20, 80)), 10,
                 ((0, 2, "H"), (2, 8, "D")))))
