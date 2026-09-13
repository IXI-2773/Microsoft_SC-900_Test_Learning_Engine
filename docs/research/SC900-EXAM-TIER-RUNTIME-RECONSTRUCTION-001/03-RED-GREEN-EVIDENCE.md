# RED / GREEN evidence

RED_TESTS_RECORDED = YES  
PRODUCTION_RUNTIME_CHANGED = NO at RED checkpoint  
BANK_HASHES_UNCHANGED = YES

## RED command

```text
python -m unittest tests.test_sc900_exam_tier_runtime -v
```

Ran against unpublished tests only. Production runtime files were unmodified. Bank hashes were the frozen values.

## RED result

```text
test_calibrated_and_default_bank_hashes_are_frozen ... ok
test_calibrated_bank_tier_and_exam_eligibility_counts ... ok
test_default_bank_missing_eligibility_field_loads_for_exam ... ok
test_exam_domain_and_topic_filters_compose_without_stretch_backfill ... FAIL
test_exam_history_source_filter_and_count_clamp ... FAIL
test_new_exam_ordered_and_randomized_exclude_stretch ... FAIL
test_r1_new_exam_excludes_explicit_ineligible_question ... FAIL
test_r2_practice_retains_ineligible_question ... ok
test_r3_smart_practice_keeps_ineligible_in_candidate_population ... ok
test_r4_missing_exam_simulation_eligible_remains_exam_usable ... FAIL
test_r5_persisted_exam_with_stretch_restores_saved_identity_order ... ok

Ran 11 tests in 1.359s
FAILED (failures=5)
```

R1 defect proof:

```text
AssertionError: 'stretch-q' unexpectedly found in ['stretch-q']
```

A new ordered Exam with count `1` selected the explicit `exam_simulation_eligible=false` Stretch item.

Preserved current behavior already proven at RED:

- R2 Practice retained the ineligible item.
- R3 Smart Practice candidate population retained the ineligible item.
- R4 missing-field item remained in the Exam session (`legacy-q` was present; the failure was Stretch still included).
- R5 persisted Exam identity/order including Stretch restored.

## GREEN command

```text
python -m unittest tests.test_sc900_exam_tier_runtime -v
```

## GREEN result

```text
Ran 11 tests in 1.030s
OK
```

All five previously failing assertions passed after the bounded Exam construction filter.
