# 01 — Debug inventory

Primary stress artifact: frozen 454-question candidate bank, loaded only through explicit test/runtime configuration.

## Matrix coverage

| Area | Method | Result |
| --- | --- | --- |
| Installation / startup | `tests/test_application_bootstrap.py`, `tools/verify_installation.py` | PASS |
| Fresh / missing user-state | existing engine regression + verify_installation | PASS |
| Candidate-bank explicit load | `tests/test_sc900_final_bank_runtime.py` | PASS |
| Learner progress / BACKLOG-1 | `tests/test_backlog1_*.py` | PASS |
| Confidence / BACKLOG-2 | `tests/test_backlog2_confidence_epistemics.py` | PASS |
| Builder/resume / BACKLOG-3 | `tests/test_backlog3_builder_resume_identity.py` | PASS |
| Practice / Exam signatures | final-bank runtime test | PASS |
| Smart Practice allocation | final-bank runtime test | PASS |
| Multi-select presence | 5 items loaded and typed `multi` | PASS |
| Large-bank parse/fingerprint | final-bank runtime test | PASS |
| Soak signatures | 8 distinct practice/exam signatures for 10/25/50/100 | PASS |
| Gate-3 CAND | `tests/test_cand01r3_*.py` | PASS |
| Phase-3 | `tests/test_sc900_phase3*.py` | PASS |
| PR #13 isolation | corpus + engine contracts | PASS (`PR13_IMPORTED = NO`) |

No new features were added. Engine code was not changed except test/harness coverage of the frozen bank.
