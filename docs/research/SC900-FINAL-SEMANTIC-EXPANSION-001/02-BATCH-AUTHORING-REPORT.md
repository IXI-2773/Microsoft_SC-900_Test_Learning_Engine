# 02 — Batch authoring report

## Counts

| Metric | Value |
| --- | --- |
| Starting approved | 400 |
| New candidates authored | 115 |
| New approved | 100 |
| New withheld (replaced before compile) | 15 |
| New rejected | 0 |
| Final approved | 500 |
| Generation continued beyond 500 | NO |

Withheld-before-compile reasons: semantic overlap with an existing `tested_decision`, wrong leaf mapping after a stem rewrite, or a multi-select that restated an already tested SIEM/SOAR pair. Those drafts never entered JSONL.

## Batches

| Batch | Serials | Bank numbers | Focus |
| --- | --- | --- | --- |
| 09 | 201–225 | 401–425 | SCI undercoverage + opening Entra distinctions |
| 10 | 226–250 | 426–450 | Entra governance/hybrid/CA + Azure network distinctions |
| 11 | 251–275 | 451–475 | Defender XDR / Sentinel / Defender for Cloud splits |
| 12 | 276–300 | 476–500 | Remaining XDR intel + Purview / privacy / STP |

Batches 13–16 were not pre-authored.

## Authoring rules applied

- Official Microsoft Learn / product documentation only
- No book, dumps, Practice Assessment, or Learn knowledge-check copy
- Conservative 27-family map reused; uniqueness carried by `tested_decision`
- Distractors drawn from neighboring SCI capabilities rather than unrelated DDoS/Bastion/TAP fillers where a better neighbor exists
- Difficulty: all 100 expansion items are intermediate

## Currentness

Study guide skills remain effective 28 July 2026 (58 leaves). Zero Trust overview still publishes verify explicitly, least privilege, and assume breach. Shared-responsibility, Entra hybrid, Sentinel-vs-XDR, and Purview portal claims were checked against the frozen inventory URLs captured 12 September 2026 (same calendar day as this package). No live study-guide change required a taxonomy rewrite.

`CHANGED_SOURCES`: none that alter the 58-leaf map. One mistaken fetch of a non-inventory Zero Trust path 404'd; the inventoried URL `https://learn.microsoft.com/en-us/security/zero-trust/zero-trust-overview` remains current.
