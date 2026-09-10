
            # SC-900 v8 migration regression matrix

            Frozen source: `5c099196525f2df236d4c80069e2b3a00a70bf94`

            The migration executes the five standalone reusable source test modules before changing source code. It then carries the large v8 engine regression suite forward through an AST filter that removes tests coupled to Security+ source banks, screenshot-ingestion tooling, source-specific benchmark fixtures, or the old release packager.

            - Retained v8 engine regression test methods: **422**
            - Removed source-coupled test methods: **22**
            - Replacement SC-900 contract coverage: profile/config isolation, 8-question bank invariants, clean validation, runtime default-bank routing, user-data namespace, release metadata, installation verification, quality tooling, Windows PE build, and launch smoke test.

            ## Removed source-coupled methods

            - `SecurityTestingEngineTests.test_packaged_runtime_auto_migrates_stronger_project_progress`
- `SecurityTestingEngineTests.test_release_packager_outputs_single_exe_folder`
- `SecurityTestingEngineTests.test_chapter_screenshot_filename_parses_source_question_number`
- `SecurityTestingEngineTests.test_chapter_screenshot_metadata_infers_chapter_three_architecture`
- `SecurityTestingEngineTests.test_chapter_screenshot_ocr_parser_prefers_first_explanation_match`
- `SecurityTestingEngineTests.test_chapter_screenshot_manifest_handles_missing_ocr_without_importing`
- `SecurityTestingEngineTests.test_verified_chapter_screenshot_record_maps_to_domain_metadata`
- `SecurityTestingEngineTests.test_chapter_screenshot_review_record_is_quarantined`
- `SecurityTestingEngineTests.test_verified_chapter_screenshot_duplicate_is_skipped`
- `SecurityTestingEngineTests.test_load_bank_has_expected_question_count`
- `SecurityTestingEngineTests.test_merged_bank_includes_imported_study_guide_assessments`
- `SecurityTestingEngineTests.test_merged_bank_validator_has_no_warnings`
- `SecurityTestingEngineTests.test_load_bank_infers_public_source_name_defaults`
- `SecurityTestingEngineTests.test_load_bank_trims_embedded_follow_on_questions_from_explanations`
- `SecurityTestingEngineTests.test_bank_validation_report_has_no_issues`
- `SecurityTestingEngineTests.test_merged_bank_benchmark_stays_within_regression_guardrails`
- `SecurityTestingEngineTests.test_merged_bank_q1105_uses_port_mirroring_answer_key`
- `SecurityTestingEngineTests.test_bank_validation_flags_conflicting_and_repeated_prompts`
- `SecurityTestingEngineTests.test_bank_lint_report_captures_quality_signals`
- `SecurityTestingEngineTests.test_bank_validation_reports_cleanup_artifacts_and_choice_explanation_mismatches`
- `SecurityTestingEngineTests.test_clean_bank_writes_sanitized_output_and_report`
- `SecurityTestingEngineGuiTests.test_clean_bank_default_preserves_runtime_file_stem`
