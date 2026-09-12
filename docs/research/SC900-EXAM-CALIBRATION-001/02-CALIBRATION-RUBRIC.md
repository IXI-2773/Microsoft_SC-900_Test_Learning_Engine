# Calibration rubric

Version: `sc900-exam-calibration-2026-09-12-v1`

## Tiers

### FUNDAMENTALS_CORE

One principal concept and one principal decision. Direct definition, capability recognition, simple service selection, or a short one-step scenario. A learner who knows the SC-900 fact should answer without a hidden inference chain.

Typical `reasoning_steps`: 0 or 1. `exam_simulation_eligible`: true.

### FUNDAMENTALS_APPLIED

A short realistic scenario, a neighboring-service comparison, or a simple requirement-to-capability map. Still Fundamentals depth.

Typical `reasoning_steps`: 1. `exam_simulation_eligible`: true.

### STRETCH

Two or more reasoning steps, stacked clues, or a fine-grained service boundary that is educationally useful but harder than normal exam simulation.

Typical `reasoning_steps`: 2+. `exam_simulation_eligible`: false for ordinary Exam mode. Remain available for Smart Practice, hard review, and mastery.

## Rewrite rule

Simplify reasoning, not knowledge. Preserve `tested_decision`, semantic family, leaf, correct Microsoft fact, current terminology, explanation, and canonical ID when the proposition is unchanged.

Do not dumb down distractors into unrelated-product jokes. Prefer conceptual neighborhoods:

- authentication / authorization / federation / Conditional Access
- PIM / access reviews / entitlement management / Identity Protection
- NSG / Azure Firewall / WAF / DDoS Protection
- Sentinel / Defender XDR / Defender for Cloud
- sensitivity labels / DLP / retention / records management
- Service Trust Portal / Compliance Manager / compliance score

## Distractor classes

`PLAUSIBLE_NEIGHBOR`, `COMMON_MISCONCEPTION`, `TECHNICALLY_RELATED_BUT_WRONG`, `CROSS_PRODUCT_GIVEAWAY`, `ABSURD`, `AMBIGUOUS`.

Targets: `AMBIGUOUS = 0`. `ABSURD` rare. Cross-product giveaways materially reduced. One weaker option is allowed.

## Negative, binary, and multi-select

Negative wording is allowed in moderation. No new true/false engine type. Do not force additional multi-select volume; the bank still has 5 multi-select items.

## Metadata

Durable fields added without replacing `beginner` / `intermediate`:

- `exam_calibration_tier`
- `reasoning_steps`
- `exam_simulation_eligible`
- `calibration_version`
