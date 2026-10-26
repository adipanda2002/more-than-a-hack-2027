# Tactical feature pipeline

`possession.features.build_features()` creates deterministic arrays indexed by tactical video
frame `0..199318`. It verifies every ATD row in order and requires `frame_id == frame + 1`; a
missing, duplicate, or extra row fails the build. Inputs come from `games.asset_paths()` and honor
`MTAH_DATA_DIR`. Run `.venv/bin/python scripts/build_features.py` to build the local cache.
This stage uses tactical tracking XML/TXT and Smart Tagging XML. Video decoding and homography
are not required for these features; no broadcast data or ground-truth labels are used.

The Python API returns `(features, cache_hit)`. Access arrays with `features[key]`; `features.fps`,
`features.pitch_m`, and `features.team_names` carry the coordinate/time context. With N frames and
S track slots, the main array families are:

| Keys | Shape / interpretation |
|---|---|
| `frame`, `atd_frame_id`, `half`, `graded` | `(N,)`; explicit timeline and eligibility, not inferred game state |
| `ball_xy_m`, `ball_observed`, `ball_speed_mps`, `ball_out_of_pitch` | Coordinates `(N,2)`; other fields `(N,)`; gate availability with the observation mask |
| `player_xy_m`, `player_observed`, `player_speed_mps`, `player_team` | Coordinates `(N,S,2)`, other fields `(N,S)`; track slots retain source order; team codes 0 home, 1 away, -1 unknown |
| `team_nearest_ball_distance_m`, `team_observed_count`, `team_nearest_ball_support_count`, `team_mean_speed_mps` | `(N,2)`; team axis 0 is home, 1 is away |
| `team_centroid_separation_m` | `(N,)`; unavailable unless both teams have observed players |
| `tag_team_offensive`, `tag_team_defensive`, `tag_team_defending_opponent_support`, `tag_team_set_piece` | `(N,2)` boolean evidence/context; same home/away team axis |
| `tag_set_piece`, `tag_unknown_team`, `tag_unknown_code`, `tag_conflict`, `tag_interval_count` | `(N,)`; context, missing semantics, overlap conflicts and interval coverage |

Coordinates/distances/speeds are stored as float32 with NaN for unavailable values. Masks are
boolean; indices and counts are integer arrays. The source data directory can be external; cache
output always remains in this checkout's ignored `data/cache/features/` directory.

ATD coordinates are normalized to `[0, 1]` and are converted once to `games.py` pitch metres
(105.3 × 68 m for this match). `fps` is 25. Position arrays use metres; displacement rates use
m/s. `ball_observed` and `player_observed` distinguish missing observations from zero-valued
coordinates. Unavailable distances and speeds remain NaN. Team membership follows the metadata's
home/away ordering; unknown IDs map to no team. Track slots are observations and do not identify
people.

The `half` array uses `games.half_video_blocks()` and is zero elsewhere. The separate `graded`
mask covers frames `11185..90651` and `110808..190197`, inclusive. Thus second-half pre-kickoff
frames are graded while `half` membership describes the published half span; neither field is an
inferred alive/dead state. Motion is calculated from adjacent observed positions only, within the
same published half. Player speed is apparent track-slot displacement, and identity switches can
make it differ from a person's velocity. A missing observation, slot-team change, or half boundary
leaves speed unavailable.

Geometry includes per-team nearest ball distance (m), tied-nearest support count, observed player
count, mean observed displacement speed (m/s), and team-centroid separation (m). No proximity
radius or possession threshold is selected here. `ball_out_of_pitch` is defined only when the ball
is observed. Missingness is available through the observation masks.

Smart Tagging is projected to half-open frame intervals `[round(start_s × fps),
round(end_s × fps))`, clipped to the tactical timeline. The documented offensive and defensive
codes are whitelisted; unrecognized codes and teams retain explicit unknown masks. Club names map through metadata, including
the documented `Atletic Club` spelling; N/A and unrecognized names remain unknown. Offensive tags
support their tagged team, defensive tags support the opponent while preserving the tagged
defending side, and set pieces supply only restart context with a separate optional team context.
Per-team evidence remains boolean, overlaps are retained, and contradictory team-support evidence
sets `tag_conflict`.
These automatic tags are evidence, never labels.

The cache lives under ignored `data/cache/features/`, uses `allow_pickle=False`, atomic replacement,
and fingerprints source asset bytes, schema, feature implementation, game geometry, half blocks,
team mapping, and runtime versions. Stale or malformed caches are rebuilt. The cache metadata contains only the
fingerprint and public schema/configuration fields; all feature arrays remain local and must not be
printed or published. `features_from_inputs()` adapts T04 artificial metre-coordinate fixtures to
the same feature geometry for asset-free tests; it is not a predictor.
