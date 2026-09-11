# SC900-BANK-PHASE3-001 — Task 7 Allocation and Confound Controls

```text
ALLOCATION_CONFOUND_CONTROLS_FROZEN = YES
ARM_ASSIGNMENT_IMPLEMENTED = NO
TRAIN_PROBE_IS_NOT_ARM_ALLOCATION = YES
```

WORK_BRANCH = `implementation/sc900-reviewed-bank-phase3`
TASK_6_ACCEPTED_HEAD = `f2c9a04d109de1d5d91e3fd32d9e39568f3828c1`
SUPERSEDES_FOR_PHASE3 = measurement/confound sections of `docs/research/SC900-ENGINE-RDAF-CAND01-GATE2-001/09-measurement-and-missingness.md` and the fairness-attack section of `04-rrc1-fairness-and-starvation.md`
DOES_NOT_OVERWRITE = original Gate-2 files

Task 7 freezes requirements for a future champion/challenger comparison. It does **not** implement the experiment, assign arms, or claim causal certainty.

## Motto applied

«Доверяй, но проверяй.» Trust, but verify.

The Task-6 partition was trusted as a measurement holdout, then checked so it would not be misread as Smart Practice vs RRC-1 assignment. A held-out family is not an experimental arm. Bank growth is not empirical validation of either policy.

## Two independent axes

```text
Axis A: TRAIN vs PROBE
        = design-time measurement holdout
        = Task 6
        = 171 TRAIN questions / 20 families
        = 29 PROBE questions / 7 independent families
        = 0 UNASSIGNED

Axis B: Smart Practice vs RRC-1
        = future champion / challenger training policies
        = not assigned in Task 6 or Task 7
        = both policies may consume TRAIN only
        = neither policy may consume PROBE for training
```

Confusing these axes invalidates the comparison. PROBE items are not “the RRC-1 set.” TRAIN items are not “the Smart Practice set.”

## Primary endpoint (unchanged)

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

See `09-TASK7-PRIOR-DECAY-OBLIGATIONS.md` for countable-unit, missingness, and contamination rules.

PROBE capacity for later measurement is 7 independent semantic families, with about four first-attempt items per day across a later 7-day window as the Task-6 justification. That is a design-time sampling plan, not collected outcomes.

## Future arm-comparison reporting contract

If a later authorized package compares Smart Practice (champion) and RRC-1 (challenger), it must measure and report at least the following, by policy, before claiming any policy effect.

| Report | Grain | Purpose |
| --- | --- | --- |
| TRAIN exposure count | item, family, policy | dose |
| Semantic-family exposure | 20 TRAIN families × policy | prevent one arm teaching a family the other never saw |
| Domain exposure | 4 SC-900 domains × policy | blueprint confound |
| Objective exposure | 14 objectives × policy | blueprint confound |
| Difficulty / calibration exposure | policy | difficulty confound |
| Source-family / source-quality exposure | policy | quality confound |
| Calendar time | policy epoch dates | time trend |
| Policy order | which policy was first | order/carryover |
| Session order within policy | session index | fatigue / familiarity |
| Outside-study events | self-report / observable | external learning |
| App-familiarity trend | session index, UI error rates if available | interface learning vs content learning |
| Fatigue / session-length proxies | duration, items/session | effort confound |
| Missing probe observations | UNOBSERVED counts by family/domain | missingness |
| Contaminated probe observations | item and family | contamination |
| Policy exposure dose before each PROBE measurement | per probe item: TRAIN exposures, families taught, calendar days | mediation / dose |

Do not invent causal certainty from these tables. They are the minimum confound ledger.

## Time trend / order effects

The one-learner design remains vulnerable to:

- general learning over calendar time;
- outside Microsoft Learn study;
- other exam-prep activity;
- increasing familiarity with the application;
- question-style familiarity;
- motivation variation;
- fatigue;
- policy order;
- carryover between training periods.

Required controls, not yet implemented:

1. Predeclared analysis windows (policy epochs), frozen before looking at probe outcomes.
2. Paired or stratified objective/family blocks where feasible, so each policy sees comparable TRAIN families rather than disjoint leftovers.
3. Explicit policy-order accounting. If only one order is used, that order is a confound, not a minor footnote.
4. Exposure-dose reporting before each PROBE measurement.
5. Contamination tracking per `09-TASK7-PRIOR-DECAY-OBLIGATIONS.md`.

Session alternation by itself is not sufficient. One policy can teach material that is later measured during another policy’s calendar window. Family-level holdout (Axis A) protects the probe families from training; it does not protect the comparison from time, order, or dose.

## Selection-confound control

A future comparison is invalid if one arm systematically receives, without the imbalance being controlled or explicitly modeled/reported:

- easier questions
- harder questions
- cleaner / higher-source-quality questions
- better-covered objectives
- different semantic-family composition
- different source quality
- different training exposure dose
- different overdue severity
- different domain balance

This is an implementation/research obligation. Task 7 does not implement final arm assignment.

Matched-pool obligation:

- Eligible training universe = Task-6 TRAIN (171 questions / 20 families).
- Smart Practice and RRC-1 draw from that same universe.
- If a session-level matcher cannot be exact, report the realized imbalance using the metrics in `08-TASK7-RRC1-FAIRNESS-STARVATION.md` (`DOMAIN_SERVICE_BALANCE`, `OBJECTIVE_SERVICE_BALANCE`, exposure counts, due-age, repair backlog).

Do not let RRC-1 receive easier or cleaner material than Smart Practice. Do not let Smart Practice receive systematically richer coverage and then attribute the difference solely to scheduling intelligence.

## Task-6 partition consequences that affect allocation

Reported, not manufactured away:

- PROBE holds 7 families and 29 questions.
- TRAIN retains the large families, including Defender XDR (24), Defender for Cloud (16), Purview information protection (16), and Azure NSG/Firewall/WAF/DDoS (15).
- Objectives absent from PROBE: `azure_security_management`, `defender_xdr`, `entra_identity_types_and_function`, `microsoft_sentinel`, `purview_information_protection_lifecycle`, `purview_insider_risk_ediscovery_audit`, `service_trust_privacy`.

Those absences mean the primary endpoint does not measure those objectives directly. A policy that spends most TRAIN dose on Defender XDR can still look strong on Entra/MFA probes for reasons unrelated to Defender scheduling. Exposure-dose and family-exposure reports exist to make that visible.

PROBE domain counts (questions, not independent units): identity 8, Entra 15, security 3, compliance 3. Security and compliance probe capacity is small. Do not treat 3 questions as 3 independent security families; `azure_key_vault` is one family (3 items) and `purview_portal` is one family (3 items).

## Outside-study and missingness

Where observable or self-reported, record Microsoft Learn study, other prep, and interruptions. Missing probe observations stay `UNOBSERVED`. They are not policy failures and not policy successes.

## What Task 7 does not claim

```text
arm allocation complete = NO
champion/challenger executed = NO
policy superiority = NOT CLAIMED
time-trend eliminated = NO
one-learner N-of-1 is decisive = NO
PHASE_3_STRUCTURALLY_ACCEPTED = NO
```
