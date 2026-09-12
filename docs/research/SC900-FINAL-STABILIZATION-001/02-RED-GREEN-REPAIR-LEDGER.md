# 02 — RED-GREEN repair ledger

No reproducible engine defect required a production code change.

| ID | Class | Symptom | RED | Fix | GREEN |
| --- | --- | --- | --- | --- | --- |
| — | — | None found against the frozen bank | n/a | n/a | n/a |

Content repairs that preceded freeze (not engine defects):

| ID | Class | Symptom | Repair |
| --- | --- | --- | --- |
| TD-EMPTY | content | 200 predecessors lacked `tested_decision` | Overlay in `tools/sc900_final_predecessor_overlay.py` |
| SEM-DUP | content | 46 predecessor paraphrases | Withheld |
| POS-LEAK | content | MLC answer position `(serial-1)%4` | Hash-based `redistribute_single_select` |

`FINAL_P0_DEFECTS = 0`  
`FINAL_P1_DEFECTS = 0`  
`FINAL_P2_DEFECTS = 0` found that met the repair bar  
`FINAL_P3_DEFECTS`: residual cross-product distractors on some predecessor identification items (documented, not rewritten)
