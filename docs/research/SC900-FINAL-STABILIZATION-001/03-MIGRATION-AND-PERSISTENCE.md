# 03 — Migration and persistence

Exercised against the frozen candidate bank through explicit load (not default activation).

| Scenario | Result |
| --- | --- |
| New learner default progress record | PASS |
| Normalize empty/legacy confidence | PASS (BACKLOG-2) |
| Canonical question IDs unique across 454 | PASS |
| Bank fingerprint 64 hex, stable on reload | PASS |
| Session snapshot round-trip with fingerprint + IDs | PASS |
| Builder fingerprint isolation | PASS (BACKLOG-3) |
| Fail-closed canonical snapshot (missing fingerprint/IDs) | existing session_store contract still raises |
| Default bank fingerprint unchanged | PASS |

No progress JSON was rewritten in the operator profile. Tests used isolated snapshots.
