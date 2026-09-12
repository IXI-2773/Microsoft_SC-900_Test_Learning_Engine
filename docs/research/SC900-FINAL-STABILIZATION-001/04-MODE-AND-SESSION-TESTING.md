# 04 — Mode and session testing

| Mode / path | Result |
| --- | --- |
| Practice signature (25) | PASS, distinct from Exam |
| Exam signature (50) | PASS |
| Smart Practice role allocation (25) | PASS, sums to 25 |
| Ordered IDs | PASS, match canonical IDs |
| Randomized shuffle subset (40) | PASS |
| Multi-select count | 5, loaded |
| Resume snapshot current_index=3 | PASS |
| Confidence tag Sure on runtime state | PASS |

GUI mouse/keyboard paths remain covered by existing engine regression tests on the default bank. Those tests were not rewritten to activate the candidate bank.
