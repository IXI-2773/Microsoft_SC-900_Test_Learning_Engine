# Evidence Matrix

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-003`

## Internal Evidence

| Source | Claim supported | Limitation | Changes candidate? |
| --- | --- | --- | --- |
| `docs/research/SC900-ENGINE-RDAF-SUCCESSOR-002/README.md` | Current authority is CAND-01R2 with Smart Practice champion, RRC-1 challenger, TRAIN / PROBE isolation, and decaying prior. | Documentation authority only. | No, reconstructs authority. |
| `docs/research/SC900-ENGINE-RDAF-SUCCESSOR-002/04-profile-informed-cand01r2-revision.md` | RRC-1 supersedes DWC-1 and assigns REPAIR before REVIEW before COVERAGE. | No implementation proof. | No, confirms comparator. |
| `progress_store.py` | Existing due and active-weak predicates are available and separable. | RRC-1 precedence is not implemented. | No. |
| `app_session_builder_mixin.py` | Current builders and Smart Practice pools lack partition guards. | Current runtime was not expected to have them. | Yes, requires future shared exclusion boundary. |
| `app_question_flow_mixin.py` | Follow-up, twin, memory, confusion, and repair paths can inject bank questions. | No PROBE concept exists yet. | Yes, expands leakage guard scope. |
| `app_game_mixin.py` | Boss and stealth checkpoint paths can inject questions. | Optional gamification, but still a valid exposure path. | Yes, guard must include gamification. |
| `app_question_render_mixin.py` and `app.py` | Answer/explanation rendering and history can reveal correct letters/texts. | Normal behavior outside probe study. | Yes, probe custody must cover reveal/export. |
| `sc900_bank_v8_baseline.json` and `tests/test_sc900_contract.py` | Current bank has 8 placeholder questions. | Not an empirical CAND-01R2 bank. | Yes, blocks positive Gate 2. |

## External Evidence

| Source | Claim supported | Limitation | Direct or analogical | Candidate effect |
| --- | --- | --- | --- | --- |
| Microsoft Learn, "Study guide for Exam SC-900" (`https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-900`) | SC-900 blueprint weights and exam scope. | Blueprint is not a question-bank design. | Direct for SC-900 structure. | Requires blueprint-balanced bank/partition. |
| Roediger and Karpicke, "Test-Enhanced Learning: Taking Memory Tests Improves Long-Term Retention" (`https://doi.org/10.1111/j.1467-9280.2006.01693.x`) | Retrieval practice can improve delayed retention versus restudy. | Passage-learning task; not SC-900 policy comparison. | Analogical. | Supports delayed retrieval endpoint, not Smart Practice superiority. |
| Karpicke and Roediger, "Repeated Retrieval During Learning Is the Key to Long-Term Retention" (`https://doi.org/10.1037/0278-7393.33.4.704`) | Repeated retrieval can improve long-term retention. | General memory study, not Microsoft certification. | Analogical. | Supports due/review service as plausible. |
| Butler, "Repeated testing produces superior transfer of learning relative to repeated studying" (`https://doi.org/10.1037/a0019902`) | Retrieval practice may support transfer better than restudy. | Transfer depends on task and cue structure. | Analogical. | Supports measuring transfer but not assuming it. |
| Latimier, Peyre, and Ramus, spacing retrieval-practice meta-analysis (`https://doi.org/10.1007/s10648-020-09572-8`) | Spacing retrieval episodes benefits retention. | Heterogeneous domains; schedule details vary. | Analogical. | Supports spacing as plausible but not personally calibrated. |
| AERA, APA, NCME, Standards for Educational and Psychological Testing (`https://www.testingstandards.net/open-access-files.html`) | Validity, fairness, reliability, and test-use arguments matter for assessment claims. | General standards, not app-specific. | Analogical/standards. | Blocks "tests pass, therefore scientifically valid." |
| Liao et al., N-of-1 carryover modeling (`https://arxiv.org/abs/2112.13991`) | N-of-1 trials require attention to carryover and temporal correlation. | Clinical-method paper, not education-specific. | Analogical. | Supports time-trend/carryover caution. |

## Evidence Summary

External evidence supports the plausibility of retrieval, spacing, delayed assessment, and validity/fairness controls. It does not prove Smart Practice superiority, RRC-1 equivalence, cross-exam prior portability, or meaningful held-out transfer for SC-900.