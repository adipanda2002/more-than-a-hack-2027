"""Frame-aligned tactical features. Values are observations, never possession labels."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

import games

SCHEMA_VERSION = 1
TEAM_UNKNOWN = -1
_OFFENSIVE_CODES = {"players in the box", "ball in final third", "ball in the box",
                    "progression", "attacking transition", "creating chances", "long ball",
                    "build up", "goals"}
_DEFENSIVE_CODES = {"defending in defensive third", "defending in middle third",
                    "defending in attacking third", "defensive transition"}


@dataclass
class Features:
    """Arrays indexed by tactical video frame; distances in metres, speeds in m/s."""
    arrays: dict
    fps: float
    pitch_m: tuple
    team_names: tuple
    schema_version: int = SCHEMA_VERSION

    def __getitem__(self, key):
        return self.arrays[key]


def _team_metadata(meta_path):
    root = ET.parse(meta_path).getroot()
    teams = list(root.iter("Team"))
    if len(teams) != 2:
        raise ValueError("metadata team schema invalid")
    ids = [team.get("id") for team in teams]
    names = tuple((team.findtext("Name") or "").strip() for team in teams)
    if not all(ids) or ids[0] == ids[1]:
        raise ValueError("metadata team IDs invalid")
    slot_team = []
    for player in root.iter("Player"):
        team_id = player.get("teamId")
        slot_team.append(ids.index(team_id) if team_id in ids else TEAM_UNKNOWN)
    if not slot_team:
        raise ValueError("metadata track slots invalid")
    return np.asarray(slot_team, dtype=np.int8), names


def _empty(n, slots, pitch, fps, names):
    length, width = pitch
    nan = lambda shape: np.full(shape, np.nan, dtype=np.float32)
    arrays = {
        "frame": np.arange(n, dtype=np.int32),
        "atd_frame_id": np.arange(1, n + 1, dtype=np.int32),
        "half": np.zeros(n, dtype=np.int8),
        "graded": np.zeros(n, dtype=np.bool_),
        "ball_xy_m": nan((n, 2)), "ball_observed": np.zeros(n, dtype=np.bool_),
        "ball_out_of_pitch": np.zeros(n, dtype=np.bool_), "ball_speed_mps": nan(n),
        "player_xy_m": nan((n, slots, 2)),
        "player_team": np.full((n, slots), TEAM_UNKNOWN, dtype=np.int8),
        "player_observed": np.zeros((n, slots), dtype=np.bool_),
        "player_speed_mps": nan((n, slots)),
        "team_nearest_ball_distance_m": nan((n, 2)),
        "team_observed_count": np.zeros((n, 2), dtype=np.int16),
        "team_nearest_ball_support_count": np.zeros((n, 2), dtype=np.int16),
        "team_mean_speed_mps": nan((n, 2)),
        "team_centroid_separation_m": nan(n),
        "tag_team_offensive": np.zeros((n, 2), dtype=np.bool_),
        "tag_team_defensive": np.zeros((n, 2), dtype=np.bool_),
        "tag_team_defending_opponent_support": np.zeros((n, 2), dtype=np.bool_),
        "tag_team_set_piece": np.zeros((n, 2), dtype=np.bool_),
        "tag_set_piece": np.zeros(n, dtype=np.bool_),
        "tag_unknown_team": np.zeros(n, dtype=np.bool_),
        "tag_unknown_code": np.zeros(n, dtype=np.bool_),
        "tag_conflict": np.zeros(n, dtype=np.bool_),
        "tag_interval_count": np.zeros(n, dtype=np.uint16),
    }
    return arrays


def _normalized_to_pitch_m(x, y, pitch):
    """Convert one normalized ATD point to metres exactly once."""
    length, width = pitch
    return float(x) * length, float(y) * width


def _set_timeline(a, game):
    blocks = games.half_video_blocks(game)
    for half, first, last in blocks:
        a["half"][first:last + 1] = half
    # The published graded windows are the same published video blocks, but the arrays are
    # separate so grade eligibility never acts as an inferred possession/dead-ball state.
    for _, first, last in blocks:
        a["graded"][first:last + 1] = True


def _derive_geometry(a, membership, pitch, fps):
    """Shared production/synthetic geometry; membership is (frame, slot) with -1 unknown."""
    n = len(a["frame"])
    a["player_team"][:] = membership
    p, b = a["player_xy_m"], a["ball_xy_m"]
    observed, ball_seen = a["player_observed"], a["ball_observed"]
    same_half = (a["half"][1:] > 0) & (a["half"][1:] == a["half"][:-1])
    same_team = membership[1:] == membership[:-1]
    for slot_key, speed_key in (("ball_xy_m", "ball_speed_mps"),
                                ("player_xy_m", "player_speed_mps")):
        xy = a[slot_key]
        valid = ball_seen if slot_key == "ball_xy_m" else observed
        pair = valid[1:] & valid[:-1]
        if slot_key == "ball_xy_m":
            good = pair & same_half
            distance = np.linalg.norm(xy[1:] - xy[:-1], axis=1) * fps
            a[speed_key][1:][good] = distance[good]
        else:
            good = pair & same_half[:, None] & same_team & (membership[1:] >= 0)
            distance = np.linalg.norm(xy[1:] - xy[:-1], axis=2) * fps
            a[speed_key][1:][good] = distance[good]
    for team in range(2):
        present = observed & (membership == team)
        counts = present.sum(axis=1)
        a["team_observed_count"][:, team] = counts
        speeds = np.where(present, a["player_speed_mps"], np.nan)
        speed_count = np.isfinite(speeds).sum(axis=1)
        okay = speed_count > 0
        a["team_mean_speed_mps"][okay, team] = np.nansum(speeds[okay], axis=1) / speed_count[okay]
        if ball_seen.any():
            dist = np.linalg.norm(p - b[:, None, :], axis=2)
            dist[~present | ~ball_seen[:, None]] = np.nan
            rows = np.isfinite(dist).any(axis=1)
            nearest = np.full(n, np.nan)
            nearest[rows] = np.nanmin(dist[rows], axis=1)
            a["team_nearest_ball_distance_m"][:, team] = nearest
            a["team_nearest_ball_support_count"][:, team] = (
                np.isfinite(dist) & (dist <= nearest[:, None] + 1e-6)).sum(axis=1)
    centroids = np.full((n, 2, 2), np.nan, dtype=np.float32)
    for team in range(2):
        present = observed & (membership == team)
        count = present.sum(axis=1)
        total = np.where(present[:, :, None], p, 0).sum(axis=1)
        good = count > 0
        centroids[good, team] = total[good] / count[good, None]
    both = np.isfinite(centroids).all(axis=(1, 2))
    a["team_centroid_separation_m"][both] = np.linalg.norm(
        centroids[both, 0] - centroids[both, 1], axis=1)
    length, width = pitch
    a["ball_out_of_pitch"] = ball_seen & ((b[:, 0] < 0) | (b[:, 0] > length) |
                                         (b[:, 1] < 0) | (b[:, 1] > width))


def _team_index(name, names):
    if not name or name.strip().casefold() in {"n/a", "na", "unknown", "none"}:
        return TEAM_UNKNOWN
    def normalize(value):
        words = value.casefold().replace("atletic", "athletic").split()
        return " ".join(word for word in words if word not in {"fc", "club"})
    key = normalize(name)
    for i, candidate in enumerate(names):
        c = normalize(candidate)
        if key == c:
            return i
    return TEAM_UNKNOWN


def _project_tags(path, a, names, fps):
    n = len(a["frame"])
    root = ET.parse(path).getroot()
    for instance in root.iter("instance"):
        try:
            start = int(round(float(instance.findtext("start")) * fps))
            stop = int(round(float(instance.findtext("end")) * fps))
        except (TypeError, ValueError):
            continue
        start, stop = max(0, start), min(n, stop)
        if stop <= start:
            continue
        code = (instance.findtext("code") or "").strip().casefold()
        tags = {label.findtext("group"): label.findtext("text")
                for label in instance.findall("label")}
        team = _team_index(tags.get("Team"), names)
        a["tag_interval_count"][start:stop] += 1
        if team == TEAM_UNKNOWN:
            a["tag_unknown_team"][start:stop] = True
        is_set_piece = code == "set pieces"
        is_defensive = code in _DEFENSIVE_CODES
        if not is_set_piece and not is_defensive and code not in _OFFENSIVE_CODES:
            a["tag_unknown_code"][start:stop] = True
        if is_set_piece:
            a["tag_set_piece"][start:stop] = True
            if team >= 0:
                a["tag_team_set_piece"][start:stop, team] = True
        elif team == TEAM_UNKNOWN:
            continue
        elif is_defensive:
            a["tag_team_defensive"][start:stop, team] = True
            a["tag_team_defending_opponent_support"][start:stop, 1 - team] = True
        elif code in _OFFENSIVE_CODES:
            a["tag_team_offensive"][start:stop, team] = True
    support = a["tag_team_offensive"] | a["tag_team_defending_opponent_support"]
    a["tag_conflict"] = support[:, 0] & support[:, 1]


def features_from_inputs(inputs):
    """Adapt T04 artificial observations into the same geometry feature arrays."""
    obs = inputs.observations
    if not obs:
        raise ValueError("synthetic inputs must contain observations")
    n, pitch, fps = len(obs), tuple(map(float, inputs.pitch_m)), float(inputs.fps)
    names = ("Home", "Away")
    # Synthetic fixture slot membership is provided by each observation's team field.
    max_slots = max((len(row.players) for row in obs), default=0)
    a = _empty(n, max_slots, pitch, fps, names)
    a["half"] = np.asarray([row.half for row in obs], dtype=np.int8)
    a["graded"][:] = True
    slot_teams = np.full((n, max_slots), TEAM_UNKNOWN, dtype=np.int8)
    for i, row in enumerate(obs):
        if row.frame != i:
            raise ValueError("synthetic frames must be contiguous and zero-based")
        if row.ball_xy is not None:
            a["ball_xy_m"][i] = row.ball_xy
            a["ball_observed"][i] = True
        for j, player in enumerate(row.players):
            a["player_xy_m"][i, j] = player.xy
            a["player_observed"][i, j] = True
            slot_teams[i, j] = {"H": 0, "A": 1}.get(player.team, TEAM_UNKNOWN)
        for phase in row.phases:
            idx = {"H": 0, "A": 1}.get(phase.team, TEAM_UNKNOWN)
            code = phase.code.casefold()
            if idx < 0:
                a["tag_unknown_team"][i] = True
            if code not in _OFFENSIVE_CODES | _DEFENSIVE_CODES | {"set pieces"}:
                a["tag_unknown_code"][i] = True
            if code == "set pieces":
                a["tag_set_piece"][i] = True
                if idx >= 0:
                    a["tag_team_set_piece"][i, idx] = True
            elif idx < 0:
                a["tag_unknown_team"][i] = True
            elif code in _DEFENSIVE_CODES:
                a["tag_team_defensive"][i, idx] = True
                a["tag_team_defending_opponent_support"][i, 1 - idx] = True
            elif code in _OFFENSIVE_CODES:
                a["tag_team_offensive"][i, idx] = True
            a["tag_interval_count"][i] += 1
    support = a["tag_team_offensive"] | a["tag_team_defending_opponent_support"]
    a["tag_conflict"] = support[:, 0] & support[:, 1]
    _derive_geometry(a, slot_teams, pitch, fps)
    return Features(a, fps, pitch, names)


def _fingerprint(paths, game, fps, pitch, slot_team):
    digest = hashlib.sha256()
    for path in paths:
        digest.update(Path(path).name.encode())
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    digest.update(Path(__file__).read_bytes())
    config = {"schema": SCHEMA_VERSION, "game": game, "fps": fps, "pitch": pitch,
              "slots": slot_team.tolist(), "python": list(__import__("sys").version_info[:3]),
              "numpy": np.__version__, "half_video_blocks": games.half_video_blocks(game)}
    digest.update(json.dumps(config, sort_keys=True).encode())
    return digest.hexdigest()


def _cache_path(data_dir, game):
    root = Path(__file__).resolve().parents[1]
    path = root / "data" / "cache" / "features" / (game + "-v{}.npz".format(SCHEMA_VERSION))
    rel = path.relative_to(root)
    ignored = subprocess.run(["git", "check-ignore", "--quiet", "--", str(rel)],
                             cwd=root, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL).returncode == 0
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", str(rel)],
                             cwd=root, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL).returncode == 0
    if not ignored or tracked:
        raise ValueError("private cache destination is not safely ignored")
    return path


def _save_cache(path, features, fingerprint):
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = json.dumps({"schema": SCHEMA_VERSION, "fingerprint": fingerprint,
                           "fps": features.fps, "pitch_m": features.pitch_m,
                           "team_names": features.team_names,
                           "python": list(sys.version_info[:3]), "numpy": np.__version__},
                          sort_keys=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".features-", suffix=".npz", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            np.savez_compressed(handle, __metadata__=np.asarray(metadata), **features.arrays)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _load_cache(path, fingerprint, n, slots):
    try:
        with np.load(path, allow_pickle=False) as cache:
            meta = json.loads(str(cache["__metadata__"].item()))
            if meta.get("schema") != SCHEMA_VERSION or meta.get("fingerprint") != fingerprint:
                return None
            if meta.get("python") != list(sys.version_info[:3]) or \
                    meta.get("numpy") != np.__version__:
                return None
            if (not isinstance(meta.get("fps"), (int, float)) or
                    not np.isfinite(meta["fps"]) or meta["fps"] <= 0 or
                    not isinstance(meta.get("pitch_m"), list) or len(meta["pitch_m"]) != 2 or
                    not all(isinstance(v, (int, float)) and np.isfinite(v) and v > 0
                            for v in meta["pitch_m"]) or
                    not isinstance(meta.get("team_names"), list) or len(meta["team_names"]) != 2 or
                    not all(isinstance(v, str) for v in meta["team_names"])):
                return None
            arrays = {key: cache[key] for key in cache.files if key != "__metadata__"}
        expected_shapes = {"frame": (n,), "atd_frame_id": (n,), "half": (n,),
                           "graded": (n,), "ball_xy_m": (n, 2), "ball_observed": (n,),
                           "ball_out_of_pitch": (n,), "ball_speed_mps": (n,),
                           "player_xy_m": (n, slots, 2), "player_observed": (n, slots),
                           "player_team": (n, slots),
                           "player_speed_mps": (n, slots),
                           "team_nearest_ball_distance_m": (n, 2),
                           "team_observed_count": (n, 2),
                           "team_nearest_ball_support_count": (n, 2),
                           "team_mean_speed_mps": (n, 2),
                           "team_centroid_separation_m": (n,),
                           "tag_team_offensive": (n, 2), "tag_team_defensive": (n, 2),
                           "tag_team_defending_opponent_support": (n, 2),
                           "tag_team_set_piece": (n, 2), "tag_set_piece": (n,),
                           "tag_unknown_team": (n,), "tag_unknown_code": (n,),
                           "tag_conflict": (n,), "tag_interval_count": (n,)}
        bool_keys = {"graded", "ball_observed", "ball_out_of_pitch", "player_observed",
                     "tag_team_offensive", "tag_team_defensive",
                     "tag_team_defending_opponent_support", "tag_team_set_piece", "tag_set_piece",
                     "tag_unknown_team", "tag_unknown_code", "tag_conflict"}
        int_keys = {"frame", "atd_frame_id", "half", "team_observed_count",
                    "team_nearest_ball_support_count", "tag_interval_count", "player_team"}
        if set(arrays) != set(expected_shapes) or any(
                arrays[key].shape != shape for key, shape in expected_shapes.items()) or any(
                arrays[key].dtype.kind not in (("b",) if key in bool_keys else
                                               ("i", "u") if key in int_keys else ("f",))
                for key in expected_shapes):
            return None
        if not np.array_equal(arrays["frame"], np.arange(n)) or not np.array_equal(
                arrays["atd_frame_id"], np.arange(1, n + 1)):
            return None
        return Features(arrays, float(meta["fps"]), tuple(meta["pitch_m"]), tuple(meta["team_names"]))
    except Exception:
        return None


def build_features(game=games.GAME, data_dir=None, use_cache=True):
    """Load, align and cache production tactical features. Exceptions are sanitized by CLI."""
    root = data_dir or games.DATA_DIR
    meta_path, raw_path, tags_path = games.require(["atd_meta", "atd_raw", "smart_tagging"],
                                                   game, root)
    slot_team, names = _team_metadata(meta_path)
    n = games.source_frames("tactical", game)
    pitch = tuple(games.GAMES[game]["pitch"])
    fps = float(games.GAMES[game]["fps"])
    fingerprint = _fingerprint((meta_path, raw_path, tags_path), game, fps, pitch, slot_team)
    cache_path = _cache_path(root, game) if use_cache else None
    if cache_path is not None and cache_path.is_file():
        cached = _load_cache(cache_path, fingerprint, n, len(slot_team))
        if cached is not None:
            return cached, True
    a = _empty(n, len(slot_team), pitch, fps, names)
    _set_timeline(a, game)
    with open(raw_path, encoding="utf-8") as handle:
        count = 0
        for expected, line in enumerate(handle, start=1):
            parts = line.rstrip("\n").split(":")
            if len(parts) != 3 or int(parts[0]) != expected or expected > n:
                raise ValueError("ATD alignment schema invalid")
            groups = parts[1].split(";")
            if len(groups) != len(slot_team):
                raise ValueError("ATD slot schema invalid")
            frame = expected - 1
            for slot, group in enumerate(groups):
                if group.startswith("N"):
                    continue
                fields = group.split(",")
                x, y = float(fields[0]), float(fields[1])
                if np.isfinite(x) and np.isfinite(y):
                    a["player_xy_m"][frame, slot] = _normalized_to_pitch_m(x, y, pitch)
                    a["player_observed"][frame, slot] = True
            if not parts[2].startswith("N"):
                fields = parts[2].split(",")
                x, y = float(fields[0]), float(fields[1])
                if np.isfinite(x) and np.isfinite(y):
                    a["ball_xy_m"][frame] = _normalized_to_pitch_m(x, y, pitch)
                    a["ball_observed"][frame] = True
            count += 1
    if count != n:
        raise ValueError("ATD row count invalid")
    membership = np.broadcast_to(slot_team, (n, len(slot_team)))
    _derive_geometry(a, membership, pitch, fps)
    _project_tags(tags_path, a, names, fps)
    features = Features(a, fps, pitch, names)
    if cache_path is not None:
        _save_cache(cache_path, features, fingerprint)
    return features, False
