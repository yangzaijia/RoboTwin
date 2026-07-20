# Project-level TODO

## Deferred: IK-feasible candidate filtering on the correct physical Piper axes

- Status: deferred and outside the current candidate-strategy video comparison.
- Current policy: execute the raw Orientation, Fused, and Top-score selections unchanged. Do not replace, rerank, or automatically fall back. Preserve IK/execution failures in `plan_summary.json`, individual videos, and the composed video for manual review.
- Future goal: after the correct `robot_replay -> anygrasp_raw/Piper +X` basis conversion, test candidates within each strategy for IK, joint limits, camera direction, and continuity, then choose the first feasible item in that strategy's own ranking.
- Future constraints: never substitute across strategies; never relax reach/rotation tolerances to manufacture success; report raw rank, replacement rank, failure reason, and final candidate ID.
- Acceptance: raw-top and feasible-top runs are reproducible side by side on a fixed episode, failures distinguish IK miss, joint limit, execution non-convergence, and collision, and historical raw-strategy outputs remain untouched.
