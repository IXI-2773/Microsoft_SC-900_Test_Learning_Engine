# Future TRAIN/PROBE Leakage Verification Matrix

WORK_ID = `SC900-BANK-PHASE2-001`
STATUS = `FUTURE_IMPLEMENTATION_CONTRACT`

This matrix converts the Gate-2 leakage inventory into explicit later implementation/test obligations. Phase 2 does **not** implement these guards.

## Shared future eligibility rule

Later runtime implementation must provide one fail-closed eligibility boundary used by every path capable of selecting, inserting, restoring, caching, rendering, recording, analyzing, or exporting question material.

For a normal training context:

```text
eligible = approved AND role == TRAIN AND family_state == resolved
```

For a defined measurement event:

```text
eligible = approved AND role == PROBE AND family_state == resolved
           AND event_authority_allows_probe_exposure
```

Missing manifest membership, unknown/disputed family state, malformed partition metadata, or role ambiguity must deny exposure rather than silently default to TRAIN.

## Matrix

| Path | TRAIN permitted? | PROBE permitted? | Probe metadata permitted? | Future guard location | Fail-closed behavior | Future verification obligation |
| --- | --- | --- | --- | --- | --- | --- |
| Smart Practice initial selection | Yes | No | No | shared candidate eligibility before scoring | exclude unknown/non-TRAIN | prove every scored candidate is TRAIN-eligible |
| Smart Practice prewarm/cache | Yes | No | No | before payload/pool creation and cache write | omit non-TRAIN and invalidate ambiguous cache | seed cache with PROBE/unknown and prove absence |
| Normal practice builder | Yes | No | No | shared pool builder | exclude non-TRAIN | full builder-path test |
| Full-bank practice/restore | Yes | No | No | restore normalization + builder boundary | restored role/family mismatch blocks item/session as specified | restore fixture containing PROBE and malformed metadata |
| Due review | Yes | No | No | before due predicate/service ordering | non-TRAIN cannot become due candidate | due PROBE fixture remains unavailable |
| Weak retest | Yes | No | No | before weak predicate/service ordering | non-TRAIN cannot become weak candidate | weak PROBE fixture remains unavailable |
| Twins/related-item injection | Yes | No | No | related-candidate source pool | filter entire family/role before similarity logic | force nearest twin to be PROBE; prove not injected |
| Delayed-recall training follow-up | Yes | No | No | follow-up candidate pool | deny non-TRAIN despite legacy “probe” naming | prove label does not bypass manifest |
| Memory ramp | Yes | No | No | related same-unit/topic/objective pool | exclude non-TRAIN first | only TRAIN siblings eligible |
| Wrong-answer memory | Yes | No | No | answer-label related-candidate pool | exclude non-TRAIN before label matching | PROBE answer labels never select PROBE item |
| Confusion-pair drill | Yes | No | No | confusion candidate pool | exclude non-TRAIN before pair construction | PROBE candidate cannot enter pair |
| Streak rescue | Yes | No | No | rescue candidate pool | exclude non-TRAIN before domain selection | same-domain PROBE cannot be injected |
| Misconception repair | Yes | No | No | prerequisite/transfer/twin/answer/confusion candidate boundary | all child injections inherit shared eligibility | one test per repair subtype plus aggregate path |
| Boss round | Yes | No | No | game candidate pool | exclude non-TRAIN before due/weak/domain ranking | PROBE never enters boss injection |
| Stealth checkpoint | Yes | No | No | checkpoint candidate pool | exclude non-TRAIN before topic/unit analytics selection | PROBE never enters checkpoint |
| Explicit measurement/probe runner | No except control mechanics | Yes | Minimal event metadata only | dedicated event authority + manifest boundary | deny if event epoch/role/family invalid | prove only authorized PROBE role exposed and once-per-protocol semantics as specified |
| Answer rendering | Yes for answered TRAIN | Only during authorized measurement flow | No cross-arm reveal | render context must carry authorized role/event | suppress answer/explanation if context invalid | direct render tests for TRAIN, authorized PROBE, unauthorized PROBE |
| Explanation rendering | Yes for answered TRAIN | Only as protocol permits after measurement capture | No | same as answer render | suppress on invalid custody | prove primary response captured before any reveal |
| Progress/history write | Yes | Measurement records only under protocol | No answer text outside approved custody | history serialization boundary | reject/redact forbidden stem/answer fields | history fixtures show no cross-arm answer leakage |
| Analytics dashboard | Aggregate TRAIN; measurement aggregates as approved | Raw PROBE content no | No revealing IDs/stems/answers/families | analytics projection/redaction boundary | redact/deny fields without authority | snapshot tests for redacted PROBE content |
| Analytics export | Aggregate allowed by protocol | Raw PROBE content no | No | export schema/projection boundary | export fails or redacts on forbidden fields | export golden-file tests |
| Import | Structural ingestion only | Structural ingestion only | Role assignment not inferred | import validation + manifest reconciliation | imported item remains UNASSIGNED until reviewed/partitioned | import missing family/role cannot become exposed |
| Compiler/candidate-bank build | Approved content may be compiled as candidate data | Approved PROBE may exist in candidate data but not training runtime exposure | Manifest metadata preserved separately/as designed | compile/reconciliation step | missing/mismatched identity fails build/partition validation | deterministic compile + manifest join test |
| Candidate-bank rebuild | Same as compiler | Same as compiler | No silent loss | deterministic rebuild/reconciliation | role/family loss fails | rebuild hash/metadata test |
| Progress restore/import | TRAIN records may restore | PROBE measurement records only under protocol | No role downgrades | restore schema migration/reconciliation | mismatch denies exposure and surfaces error | legacy + malformed restore fixtures |
| Developer/debug helpers | TRAIN only by default | Only explicit isolated test authority | No | helper API boundary | safe default excludes PROBE | debug helper tests prove default-safe behavior |
| Test fixtures | Synthetic roles allowed | Synthetic roles allowed | Synthetic only | test-data namespace | production manifest cannot be implicitly reused | test fixture separation check |

## Required cross-cutting tests

Later Gate-3 verification must include:

1. **Negative-path injection:** every selector/injector is given a high-priority PROBE item and must still refuse it outside an authorized measurement event.
2. **Unknown-state fail closure:** missing item, missing family, disputed family, malformed role, stale partition epoch, and manifest mismatch all deny normal exposure.
3. **Semantic-family isolation:** a TRAIN item and PROBE sibling cannot coexist in one family/epoch; manifest validation fails before runtime.
4. **Restore/rebuild persistence:** role and family identity survive serialization/rebuild or the operation fails visibly.
5. **Cache invalidation:** no stale pre-partition cache can expose material after a manifest/epoch change.
6. **Answer custody:** unauthorized histories, dashboards, logs, exports, and render paths contain no PROBE answer/explanation material.
7. **Primary-endpoint ordering:** first-attempt probe correctness is recorded before any explanation/correct-answer reveal.
8. **All-path inventory reconciliation:** Gate-3 implementation review must map every row above to concrete code location(s) and executable tests; an unmapped path blocks proof.

## Gate boundary

This matrix addresses the Gate-2 requirement to specify future guard semantics and a verification matrix. It does not claim those guards exist. Actual runtime enforcement remains a Gate-3-or-later requirement.
