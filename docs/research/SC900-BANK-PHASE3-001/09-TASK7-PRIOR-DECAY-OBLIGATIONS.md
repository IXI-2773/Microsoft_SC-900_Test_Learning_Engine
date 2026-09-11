# SC900-BANK-PHASE3-001 — Task 7 Prior-Decay, Missingness, and Contamination Obligations

```text
PRIOR_DECAY_OBLIGATIONS_FROZEN = YES
MISSINGNESS_RULE_FROZEN = YES
CONTAMINATION_RULE_FROZEN = YES
PRIOR_DECAY_TEST_OBLIGATIONS = FROZEN
RUNTIME_PRIOR_AUTHORITY_IMPLEMENTED = NO
```

WORK_BRANCH = `implementation/sc900-reviewed-bank-phase3`
TASK_6_ACCEPTED_HEAD = `f2c9a04d109de1d5d91e3fd32d9e39568f3828c1`
SUPERSEDES_FOR_PHASE3 = `docs/research/SC900-ENGINE-RDAF-CAND01-GATE2-001/08-decay-rule-adversarial-review.md` and the counting/missingness sections of `09-measurement-and-missingness.md`
DOES_NOT_OVERWRITE = original Gate-2 files `07`, `08`, and `09`

Task 7 freezes the countable observation, missingness, contamination, and SEED/ADVISORY/RETIRED test obligations against the real Phase-3 partition. It does **not** implement prior-authority runtime logic.

## Motto applied

«Доверяй, но проверяй.» Trust, but verify.

The frozen stage rule was trusted as already-stated design. Counting semantics were not trusted until the exact unit, identity, and exclusion rules were written against Task-6 PROBE membership. Bank construction does not produce prior-decay observations. Seven PROBE families create future measurement capacity; they are not 29 independent outcomes already in hand.

## Frozen stage rule

Historical prior authority remains:

| Stage | Condition |
| --- | --- |
| `SEED` | fewer than 10 clean SC-900 held-out probe outcomes |
| `ADVISORY` | 10 through 29 clean SC-900 held-out probe outcomes |
| `RETIRED` | at least 30 clean 7-day probe outcomes AND all four domains represented AND at least 4 observations per domain |

After `RETIRED`, the historical prior loses decision authority permanently.

It must never regain authority because of:

- restore
- device change
- bank change
- missing later observations
- import
- backup
- retry
- redo
- data pruning

Monotonicity:

```text
SEED -> ADVISORY -> RETIRED
```

Stage may stay. Stage may advance. Stage may not regress. Confidence labels and response time must not alter stage.

During `ADVISORY`, direct SC-900 evidence outranks the historical prior when they conflict. Direct evidence does not rewind the stage.

## Countable observation

The exact future countable unit for stage progression and for the primary endpoint is all of the following:

```text
exam                = SC-900, not SY0-701 or any other exam
item membership     = designated held-out PROBE in the frozen Task-6 manifest
                      before the training epoch that precedes measurement
family membership   = one of the 7 PROBE families
cleanliness         = uncontaminated (see below)
attempt             = first scored attempt on that exact canonical item
timing              = valid 7-day measurement window where the RETIRED
                      rule or the primary endpoint requires it
domain metadata     = valid SC-900 domain from the reviewed store
identity            = stable evaluation identity (learner + exam +
                      partition epoch + canonical item id)
not duplicated by   = retry, restore, backup, redo, export/import,
                      replayed history, duplicate persistence
```

Effective independent measurement units remain **7 families**, not 29 questions. Question-level outcomes may still be counted toward the numeric 10/29/30 stage thresholds when each outcome satisfies the countable-unit rule. Family clustering must be reported with those counts so that 30 question-level outcomes in 2 families are not mistaken for 30 independent semantic measurements.

Wrong-exam outcomes are not countable.

Invalid or missing domain metadata: the observation is not countable toward RETIRED’s all-domain / per-domain clauses. It is also not countable toward the primary endpoint until domain metadata is valid. Do not impute a domain.

## Stable evaluation identity

A countable observation is keyed by:

```text
evaluation_id = (learner_id, exam=SC-900, partition_epoch, canonical_question_id)
```

`partition_epoch` is the Task-6 epoch frozen in the manifest (`phase3-task6-train-probe-partition` at Task-6 acceptance).

Device, path, backup filename, and session filename are not identity. Two persisted rows with the same `evaluation_id` are one observation. The earliest clean first scored attempt wins. Later rows are duplicates.

If learner identity is not yet implemented, the local single-learner device remains one implicit learner. Restore onto a second device must carry the same evaluation identity rather than minting a new SEED counter.

## Missingness

A missed delayed probe is:

```text
UNOBSERVED
```

It is not `WRONG` and not `CORRECT`.

Do not impute primary-endpoint success or failure from absence.

Rationale, carried forward from Gate 2: treating missed probes as wrong punishes absence; treating them as correct rewards absence. Both distort a one-learner delayed endpoint.

UNOBSERVED outcomes:

- do not increment clean outcome totals;
- do not increment SEED/ADVISORY/RETIRED counters;
- do not enter the primary endpoint numerator or denominator;
- must be reported separately as missingness.

A later completed attempt on the same item after the valid window is not a substitute primary observation unless a later research protocol explicitly defines a secondary timing window. Task 7 does not define that substitute.

## Contamination

A contaminated PROBE result:

- does not count toward clean outcome totals;
- does not count toward the RETIRED threshold;
- does not enter the primary endpoint;
- must be reported separately.

Contamination-relevant exposure includes, where materially revealing:

- exact stem shown outside a clean measurement protocol;
- correct answer reveal;
- explanation / rationale reveal;
- same-item practice, due/weak/coverage/follow-up/boss/stealth/session restore;
- semantic-family-equivalent training item (whole-family partition already forbids TRAIN/PROBE splits; a runtime leak would still contaminate);
- transfer-edge-connected content;
- analytics/export/history that reveals the answer or proposition;
- screenshot/issue review of the item during the learner study epoch.

Contamination is monotonic for the affected observation. Once contaminated, the observation stays contaminated unless a later research protocol explicitly defines a stronger provenance correction. Task 7 defines no such correction.

Do not “clean” an exposed item merely because the user forgot it.

Family-level consequence: contamination of one PROBE item does not automatically contaminate other items in the same family, but it does reduce the independent-family measurement capacity if the family’s remaining items are also compromised. Report both item-level and family-level contamination.

## Primary endpoint alignment

Primary endpoint remains:

```text
7-day first-attempt correctness on CLEAN HELD-OUT SC-900 probe items
```

A primary observation requires:

- PROBE membership frozen before training;
- no contaminating exposure;
- first scored attempt;
- valid timing;
- valid SC-900 metadata;
- valid persistence identity.

This is the same unit used for RETIRED counting when the 7-day window is required. SEED/ADVISORY numeric counts may include clean first-attempt SC-900 PROBE outcomes that satisfy cleanliness and identity even if a particular protocol stage uses a shorter diagnostic window, but RETIRED additionally requires the 7-day window plus domain coverage. Do not mix those clauses.

## Historical prior portability (unchanged prohibition)

Carried forward from Gate-2 `07-historical-prior-portability.md`:

The SY0-701 prior may transfer only exam-independent strategy tendencies. It must not transfer Security+ domain mastery, question difficulty, concept-graph edges, or readiness estimates into SC-900 decisions.

Phase 3 did not produce direct SC-900 outcome evidence. Portability remains `PLAUSIBLE_BUT_UNPROVEN`. See `11-TASK7-NOETIC-REASSESSMENT.md` (N02).

## Prior-decay future test matrix

Do not implement prior-authority runtime logic in Task 7. The following tests are implementation-ready obligations.

| Test ID | Scenario | Required result |
| --- | --- | --- |
| PD01 | Clean countable outcomes = 0..9 | stage = `SEED` |
| PD02 | Transition at 10 clean countable outcomes | stage becomes `ADVISORY`; does not skip to `RETIRED` |
| PD03 | Clean countable outcomes = 29, domain coverage incomplete or complete | stage remains `ADVISORY` |
| PD04 | 30 clean 7-day outcomes but one domain has fewer than 4 | stage remains `ADVISORY`; does not reset to `SEED` |
| PD05 | 30 clean 7-day outcomes, all four domains, >=4 per domain | stage becomes `RETIRED` |
| PD06 | After RETIRED, restore old progress with <10 outcomes | stage remains `RETIRED` |
| PD07 | After RETIRED, device change / new path / bank filename change | stage remains `RETIRED` |
| PD08 | After RETIRED, later observations go missing / pruned / backup-only | stage remains `RETIRED` |
| PD09 | Contaminated correct PROBE | excluded from clean count and primary endpoint; reported separately; cannot push SEED→ADVISORY or ADVISORY→RETIRED |
| PD10 | UNOBSERVED delayed probe | excluded from clean count; not scored wrong or correct |
| PD11 | Duplicate restored / imported / replayed observation | one countable row; extras excluded |
| PD12 | Redo / retry of the same PROBE item | not a first attempt; excluded from primary |
| PD13 | SY0-701 or other non-SC-900 outcome | excluded |
| PD14 | Invalid or missing domain on an otherwise clean row | excluded from RETIRED domain clauses and from primary until valid |
| PD15 | During ADVISORY, direct SC-900 evidence contradicts prior | direct evidence wins; stage does not rewind |
| PD16 | High confidence aligned with prior during SEED/ADVISORY | confidence does not alter stage |
| PD17 | Fast or slow response time aligned with prior | response time does not alter stage |
| PD18 | Manifest hash mismatch or missing role on a supposed PROBE item | NOT ELIGIBLE; not countable |
| PD19 | Training exposure to a co-family TRAIN item cannot occur under the frozen partition; if a runtime leak later shows a co-family item | contaminate the affected PROBE observation(s) per the contamination rule |
| PD20 | Measurement path used a TRAIN item | not a PROBE observation |

## What Task 7 does not claim

```text
historical prior empirically portable = NOT CLAIMED
clean SC-900 probe outcomes currently collected = 0
SEED/ADVISORY/RETIRED runtime engine = NOT IMPLEMENTED
N02 resolved by bank growth = NO
```
