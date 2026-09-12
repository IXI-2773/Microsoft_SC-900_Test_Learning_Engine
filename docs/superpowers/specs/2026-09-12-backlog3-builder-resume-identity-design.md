# BACKLOG-3 — Session Builder / Resume Identity Integrity

## Scope

Issue #16 implementation from the publication-safe BACKLOG-2 lineage. A resumable session may match a builder request only when both share the same canonical builder identity. Builder identity preserves every material session-construction decision. No user-visible builder intent may be silently discarded before identity comparison.

Do not import PR #13. Do not start Day 1. Do not weaken BACKLOG-1 bank/question identity or BACKLOG-2 confidence integrity. Do not treat mtime as identity.

Starting point: `baf69ecf773cc929d7fb84a00494b434595aa8f3` on `implementation/sc900-backlog2-confidence-epistemics`.

Implementation branch: `implementation/sc900-backlog3-builder-resume-identity`.

## Invariant

```
canonical builder request
  → normalized builder context
  → canonical builder identity / fingerprint
  → session persistence
  → resume discovery
  → cleanup
  → restore validation
  → builder UI restoration
```

The same authority is reused everywhere.

Conceptual identity hierarchy:

```
bank/content identity
  + canonical question identity/order
  + canonical builder identity
  = ordinary resumable-session authority
```

Builder identity complements, and does not replace:

- `bank_fingerprint`
- `question_ids`
- `restore_question_ids`
- `canonical_session_signature`

## Lifecycle

```
builder controls / explicit request
  → normalize_builder_context (keyword-only precedence)
  → builder_context_fingerprint
  → persist builder_context + versioned identity + fingerprint
  → resume/cleanup by exact fingerprint
  → mtime ranks only equivalent fingerprints
  → restore validates stored context against stored fingerprint
  → UI may round-trip canonical context (not identity authority)
```

## Canonical normalizer

One pure function in `builder_identity.py`.

Keyword-only inputs. A raw mapping is optional complementary input, never a silent override of an explicit argument.

Precedence:

1. explicit keyword argument
2. canonical raw field
3. documented legacy / default

`False` is a meaningful boolean. Never use `randomize or existing_value`.

## Identity-bearing fields

| Field | Why material |
| --- | --- |
| `mode` | Practice / Smart Practice / Exam / Weak retest / Due review change construction |
| `count` | Requested size, including distinct `All visible` vs numeric counts |
| `source_label` | Human-facing source badge used by resume history and UI |
| `session_source` | Actual source-pool selector (`All`, `Unseen`, …) |
| `randomize` | Ordered vs randomized construction intent |
| `domain_filter` | Candidate pool |
| `topic_filter` | Candidate pool |
| `status_filter` | Candidate pool |

No immutable source identifier exists beyond normalized `session_source` plus `source_label`. That bounded limitation is accepted; BACKLOG-3 does not invent a source-identity migration.

Non-identity / presentation / runtime-local:

- question numbers (BACKLOG-1 presentation)
- elapsed time, current index, exam reveal, checkpoints
- resulting shuffle order (recorded as canonical question IDs, not as builder intent)
- filesystem mtime / path
- `preserve_if_saved`, `reset_clock`
- visual badges and widget layout

Smart Practice `randomize` is identity-bearing because it changes pool sampling. Session-start still may pass `randomize=False` into `start_session_from_pool` to avoid a second shuffle; that operational flag must not overwrite an already-canonical builder request.

## Fingerprint

- Kind: `canonical_builder_request`
- Version: `1`
- Algorithm: SHA-256 of canonical JSON
- JSON: UTF-8, `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`
- Payload: `{builder_identity, builder_identity_version, builder_context}`
- No mtime, path, timestamps, or process state

## Snapshot schema

Keep `SESSION_SCHEMA_VERSION = 4` as the BACKLOG-1 ordinary envelope.

Builder identity is a complementary versioned authority, not a competing session schema:

- `builder_context`
- `builder_identity`
- `builder_identity_version`
- `builder_context_fingerprint`
- `builder_identity_status` when migration status is not already `canonical`

New ordinary snapshots write all builder identity fields. Schema 4 snapshots that already carry BACKLOG-1 bank/question identity remain valid; missing builder identity is migrated explicitly rather than treated as a wildcard.

## Session file identity

Two materially different builder requests can select the same canonical question IDs in the same order (filter coincidence, or `randomize=True` happening to equal source order).

Decision: builder intent remains a distinct resumable identity. Ordinary session filenames therefore append a short builder fingerprint after the BACKLOG-1 signature:

```
{stem}_{mode}_session_{count}_{session_sig}_{builder_fp12}.json
```

CAND / experimental path keeps question-number file identity unchanged.

Resume discovery continues to glob and validate snapshot identity, so pre-BACKLOG-3 files without the suffix remain discoverable.

## Resume / cleanup

Ordinary candidate is resumable only if:

1. valid session schema
2. valid BACKLOG-1 bank fingerprint
3. valid canonical question/session identity
4. valid canonical builder identity
5. desired fingerprint == saved fingerprint
6. session incomplete and otherwise resumable
7. builder status is not `ambiguous` or `invalid`

mtime may rank only after exact fingerprint equality.

Cleanup uses the same authority. A cleanup for identity X may remove only snapshots with identity X.

## Legacy

| Snapshot | Status | Auto-resume | Unrelated cleanup |
| --- | --- | --- | --- |
| Complete `builder_context` including `randomize` | `migrated` | yes, exact fingerprint | only exact fingerprint |
| `builder_context` present, `randomize` absent | `legacy_defaulted` (`False`) | yes vs ordered/False only | only that fingerprint |
| Missing / unusable `builder_context` | `ambiguous` | no | no |
| Contradictory modern fingerprint | fail closed | no | no (quarantine on restore) |

Historical code used `bool(payload.get("randomize"))`, so absence already meant `False` / ordered. That mapping is documented and deterministic. It is not a wildcard for randomized requests.

Ambiguous snapshots are preserved, not deleted, when automatic identity cannot be proven.

## CAND / PR #13

PR #13 remains absent. Gate-3 CAND deterministic session behavior is unchanged. Experimental restore continues to use its special persistence path. Ordinary randomize identity is not applied to frozen CAND flows.

## Fail closed

- unsupported future builder identity version
- fingerprint mismatch vs stored context
- malformed canonical builder context
- required identity fields absent on a snapshot that already claims builder identity
- invalid types
- unknown identity kind
