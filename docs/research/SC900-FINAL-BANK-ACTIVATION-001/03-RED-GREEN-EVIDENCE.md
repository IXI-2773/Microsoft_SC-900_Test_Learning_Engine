# RED / GREEN evidence

## RED command

```
python -m unittest tests.test_sc900_final_bank_activation tests.test_sc900_final_bank_activation_migration -v
```

Run against unmodified `origin/main` plus the new failing activation-contract tests only. Production files were not damaged to manufacture RED.

## RED result

`Ran 18 tests in 0.066s`

`FAILED (failures=13, errors=3)`

Passing characterization tests, proving pre-activation main was still the 8-question state while the frozen 454 bank itself was valid:

- `test_a5_canonical_calibrated_bank_is_runtime_valid` PASS
- `test_historical_baseline_bank_remains_byte_identical` PASS

Genuine RED demonstrating the pre-activation 8-question runtime:

| Test | Failure |
| --- | --- |
| A1 runtime pointer | `sc900_bank_v8_final.json` != `sc900_bank_v8_baseline.json` |
| A2 installation verifier | source still required `instead of 8`; no `RUNTIME_BANK_QUESTION_COUNT` |
| A3 release authority | `EXPECTED_QUESTION_COUNT = 8` |
| A4 active count | active path still the baseline filename |
| A6 Exam pool | `431 != 8` |
| A7 Practice pool | `454 != 8` |
| A8 Smart Practice Stretch | `23 != 0` |
| Active SHA/file | `sc900_bank_v8_final.json` did not exist |
| Packaging | final bank absent from `REQUIRED_RUNTIME_RESOURCES` |
| Count field | `runtime_bank_question_count` missing from profile |

Migration-class RED also failed because the active bank was still the 8-question baseline, so stems/fingerprints/IDs collided with historical baseline identity.

## GREEN command after minimal activation

```
python -m unittest tests.test_sc900_final_bank_activation tests.test_sc900_final_bank_activation_migration tests.test_sc900_contract tests.test_release_workflow tests.test_sc900_exam_tier_runtime tests.test_sc900_final_bank_runtime -v
```

After one bounded contract-test correction (calibrated `domain_code` values are slugs, not `"1"`/`"2"`/`"3"`/`"4"`), those suites passed.

Backlog-2 `test_b2_027` initially failed because it copied `app.DEFAULT_BANK` as a small fixture. After activation that file is the 454-question bank, which changes adaptive choice order. The test fixture was pinned to the historical baseline bank. That is isolation of a confidence-epistemics fixture, not a change to production activation.

## Full suite GREEN

```
python -m unittest discover -s tests -q
```

`Ran 892 tests in 52.053s`

`OK`
