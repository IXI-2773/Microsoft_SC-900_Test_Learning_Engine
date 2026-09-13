# 05 — Large-bank stress

Measured on the frozen 454-question artifact via `tests/test_sc900_final_bank_runtime.py`.

| Operation | Observation |
| --- | --- |
| Bank JSON parse + `load_bank` | Completes in well under 1s in the unit-test process (class setup; whole module < 50ms including assertions in this environment) |
| Canonical IDs | 454 unique |
| Bank fingerprint | 64 hex, identical on reload |
| Ordered ID list | Stable |
| Random sample shuffle | 40-item subset ok |
| Smart Practice allocation | 25 roles sum to 25 |
| Session signatures | Practice vs Exam differ; 8 soak signatures unique |
| Pathological hang / unbounded memory | Not observed |

No invented performance SLO. No hang, no multi-second parse stall, no fingerprint instability.
