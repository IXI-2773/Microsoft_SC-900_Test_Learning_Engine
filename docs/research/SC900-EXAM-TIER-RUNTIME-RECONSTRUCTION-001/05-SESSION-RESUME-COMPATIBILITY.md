# Session resume compatibility

## Required invariant

NEW ordinary Exam session => current eligibility applies.  
EXISTING persisted Exam session => restore recorded canonical question identities and order.

## New Exam

`start_session_from_pool(..., mode=Exam)` filters with `exam_runtime_eligible` before count sampling. `get_session_builder_pool()` applies the same filter when the UI mode is Exam. Master questions are not mutated and Stretch remains in the loaded bank.

## Historical Exam containing Stretch

RED and GREEN both passed `test_r5_persisted_exam_with_stretch_restores_saved_identity_order`.

A pre-written Exam snapshot containing `[stretch-q, core-q, ineligible-q]` was restored through `start_custom_session` after the eligibility filter existed. Restored identity/order remained `[stretch-q, core-q, ineligible-q]` at saved index `1`.

Resume uses `master_questions` canonical ID lookup, not the newly constructed eligible pool. No retroactive rebuild of historical membership.

## Legacy bank

Default `sc900_bank_v8_baseline.json` still has 8 questions and no `exam_simulation_eligible` field. Missing field => eligible. New Exam of that bank loads all 8 questions.

LEGACY_BANK_COMPATIBILITY = PASS  
LEGACY_SESSION_RESUME = PASS
