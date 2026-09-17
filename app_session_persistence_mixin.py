import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path

from app_constants import MODE_EXAM, MODE_PRACTICE
from app_info import APP_VERSION
from builder_identity import (
    builder_identities_match,
    builder_ui_state_from_context,
    canonical_builder_identity,
)
from cand01r3_runtime import (
    filter_training_questions,
    is_cand01r3_active,
    persistable_authority_metadata,
    restore_experimental_session,
)
from confidence_epistemics import bind_legacy_answer_event_ids, normalize_confidence
from exam_runtime_eligibility import filter_new_exam_pool
from progress_store import set_progress_flag, set_progress_suspended, update_progress_record
from question_identity import canonical_question_id
from session_identity import bank_content_fingerprint, canonical_session_signature, ordered_question_ids
from session_models import QuestionRuntimeState, apply_answer_state
from session_store import (
    answer_states_by_question_id,
    build_session_snapshot,
    calculate_session_question_limit,
    checkpoint_file_path,
    legacy_progress_file_path,
    legacy_session_file_path,
    migrate_session_snapshot,
    normalize_builder_context,
    progress_file_path,
    runtime_bank_stem,
    saved_session_matches_current,
    serialize_answer_state,
    session_file_path,
    session_signature,
)
from smart_practice_concept_graph import concept_key_for_question as graph_concept_key_for_question


class SessionPersistenceMixin:
    def current_elapsed_seconds(self):
        return int(self.elapsed_base + (time.time() - self.clock_started_at))

    def calculate_session_question_limit(self, base_count):
        return calculate_session_question_limit(base_count)

    def _session_bank_questions(self):
        source = list((getattr(self, "master_questions", None) or self.questions) or [])
        if not source:
            raise ValueError("Session identity requires a loaded question bank.")
        return source

    def current_bank_fingerprint(self):
        return bank_content_fingerprint(self._session_bank_questions())

    def _canonical_ids_for_questions(self, questions):
        return ordered_question_ids(list(questions or []))

    def _questions_for_canonical_ids(self, question_ids):
        source = self._session_bank_questions()
        source_ids = ordered_question_ids(source)
        lookup = dict(zip(source_ids, source, strict=True))
        resolved = []
        for question_id in question_ids:
            canonical_id = str(question_id or "").strip()
            question = lookup.get(canonical_id)
            if question is None:
                raise ValueError(f"Unknown canonical question reference in session: {canonical_id}")
            resolved.append(question)
        if len(resolved) != len(question_ids):
            raise ValueError("Session canonical question identity could not be resolved exactly.")
        return resolved

    def _questions_for_question_numbers(self, question_numbers):
        source = self._session_bank_questions()
        lookup = {}
        for question in source:
            number = str(question.get("question_number") or "").strip()
            if not number:
                continue
            if number in lookup:
                raise ValueError(f"Ambiguous question number in loaded bank: {number}")
            lookup[number] = question
        resolved = []
        for question_number in question_numbers:
            number = str(question_number or "").strip()
            question = lookup.get(number)
            if question is None:
                raise ValueError(f"Unknown question number in loaded bank: {number}")
            resolved.append(question)
        return resolved

    def current_session_signature(
        self, mode=None, questions: list[QuestionRuntimeState] | None = None, question_numbers=None
    ):
        mode = str(mode or self.active_session_mode or MODE_PRACTICE)
        if is_cand01r3_active():
            if question_numbers is None:
                questions = questions if questions is not None else self.questions
                question_numbers = [q.get("question_number", "") for q in questions]
            return session_signature(mode, list(question_numbers))
        if questions is None:
            if question_numbers is None:
                questions = self.questions
            else:
                questions = self._questions_for_question_numbers(question_numbers)
        question_ids = self._canonical_ids_for_questions(questions)
        return canonical_session_signature(mode, self.current_bank_fingerprint(), question_ids)

    def runtime_bank_stem(self, bank_path):
        return runtime_bank_stem(bank_path)

    def session_file_for_bank(
        self,
        bank_path,
        mode=None,
        questions: list[QuestionRuntimeState] | None = None,
        question_numbers=None,
        question_ids=None,
        builder_context=None,
        builder_context_fingerprint=None,
    ):
        mode = str(mode or self.active_session_mode or MODE_PRACTICE)
        if is_cand01r3_active():
            if question_numbers is None:
                questions = questions if questions is not None else self.questions
                question_numbers = [q.get("question_number") for q in questions]
            return session_file_path(self.user_data_dir, bank_path, mode, list(question_numbers))
        if question_ids is None:
            if questions is None:
                if question_numbers is None:
                    questions = self.questions
                else:
                    questions = self._questions_for_question_numbers(question_numbers)
            question_ids = self._canonical_ids_for_questions(questions)
        canonical_ids = [str(question_id or "").strip() for question_id in question_ids]
        if not canonical_ids or any(not question_id for question_id in canonical_ids):
            raise ValueError("Session file identity requires canonical question IDs.")
        if question_numbers is None:
            if questions is not None:
                question_numbers = [q.get("question_number") for q in questions]
            else:
                question_numbers = [q.get("question_number") for q in self._questions_for_canonical_ids(canonical_ids)]
        fingerprint = self._builder_fingerprint_for_path(builder_context, builder_context_fingerprint)
        return session_file_path(
            self.user_data_dir,
            bank_path,
            mode,
            list(question_numbers),
            bank_fingerprint=self.current_bank_fingerprint(),
            question_ids=canonical_ids,
            builder_context_fingerprint=fingerprint,
        )

    def _builder_fingerprint_for_path(self, builder_context=None, builder_context_fingerprint=None):
        if builder_context_fingerprint:
            return str(builder_context_fingerprint).strip()
        source = builder_context
        if source is None:
            source = getattr(self, "current_builder_context_data", None)
        if not isinstance(source, dict) or not source:
            return None
        identity = canonical_builder_identity(source)
        return identity["builder_context_fingerprint"]

    def checkpoint_file_for_bank(self, bank_path, answered_count: int):
        return checkpoint_file_path(self.checkpoint_dir, bank_path, self.active_session_mode, answered_count)

    def progress_file_for_bank(self, bank_path):
        return progress_file_path(self.user_data_dir, bank_path)

    def legacy_session_file_for_bank(self, bank_path, mode=None):
        return legacy_session_file_path(bank_path, str(mode or self.active_session_mode or MODE_PRACTICE))

    def legacy_progress_file_for_bank(self, bank_path):
        return legacy_progress_file_path(bank_path)

    def migrate_runtime_file(self, legacy_path, new_path, label: str):
        self.persistence.migrate_runtime_file(legacy_path, new_path, label=label)

    def _saved_session_matches_current(self, saved, questions: list[QuestionRuntimeState] | None = None):
        questions = questions if questions is not None else self.questions
        current_qnums = [q.get("question_number") for q in questions]
        restore_qnums = list(self.session_restore_question_numbers or current_qnums)
        if is_cand01r3_active() or (isinstance(saved, dict) and saved.get("cand01r3")):
            return saved_session_matches_current(
                saved,
                self.active_session_mode,
                current_qnums,
                restore_qnums,
                allow_legacy=True,
            )
        current_ids = self._canonical_ids_for_questions(questions)
        restore_ids = list(getattr(self, "session_restore_question_ids", None) or current_ids)
        return saved_session_matches_current(
            saved,
            self.active_session_mode,
            current_qnums,
            restore_qnums,
            bank_fingerprint=self.current_bank_fingerprint(),
            current_question_ids=current_ids,
            restore_question_ids=restore_ids,
        )

    def normalize_builder_context(
        self,
        raw=None,
        *,
        mode=None,
        count=None,
        randomize=None,
        source_label=None,
        session_source=None,
        domain_filter=None,
        topic_filter=None,
        status_filter=None,
    ):
        return normalize_builder_context(
            raw,
            mode=mode,
            count=count,
            randomize=randomize,
            source_label=source_label,
            session_source=session_source,
            domain_filter=domain_filter,
            topic_filter=topic_filter,
            status_filter=status_filter,
        )

    def restore_builder_ui_from_context(self, builder_context):
        state = builder_ui_state_from_context(builder_context)
        if hasattr(self, "session_mode_var"):
            self.session_mode_var.set(state["mode"])
        if hasattr(self, "session_count_var") and state["count"]:
            self.session_count_var.set(state["count"])
        if hasattr(self, "session_source_var"):
            self.session_source_var.set(state["session_source"])
        if hasattr(self, "session_random_var"):
            self.session_random_var.set(bool(state["randomize"]))
        if hasattr(self, "domain_filter_var"):
            self.domain_filter_var.set(state["domain_filter"])
        if hasattr(self, "topic_filter_var"):
            self.topic_filter_var.set(state["topic_filter"])
        if hasattr(self, "status_filter_var"):
            self.status_filter_var.set(state["status_filter"])
        if state["source_label"]:
            self.active_source_label = state["source_label"]

    def _canonical_builder_identity(self, builder_context=None, **kwargs):
        return canonical_builder_identity(builder_context, **kwargs)

    def _builder_context_matches(self, saved_context, current_context):
        saved = saved_context
        if not isinstance(saved, dict) or "builder_context_fingerprint" not in (saved or {}):
            saved = canonical_builder_identity(saved_context)
        current = current_context
        if not isinstance(current, dict) or "builder_context_fingerprint" not in (current or {}):
            current = canonical_builder_identity(current_context)
        return builder_identities_match(saved, current)

    def _session_builder_glob_pattern(self, mode):
        safe_mode = str(mode or "").lower().replace(" ", "_").replace("/", "_")
        return f"{self.runtime_bank_stem(self.bank_path)}_{safe_mode}_session_*.json"

    def _session_discovery_glob_patterns(self, mode):
        patterns = [self._session_builder_glob_pattern(mode)]
        authority = getattr(self, "content_revision_authority", None)
        if authority is None or not self.bank_path:
            return patterns
        safe_mode = str(mode or "").lower().replace(" ", "_").replace("/", "_")
        source_stem = runtime_bank_stem(Path(self.bank_path).with_name(authority.source_bank_filename))
        source_pattern = f"{source_stem}_{safe_mode}_session_*.json"
        if source_pattern not in patterns:
            patterns.append(source_pattern)
        return patterns

    def _session_discovery_paths(self, mode):
        seen: set[Path] = set()
        paths: list[Path] = []
        for pattern in self._session_discovery_glob_patterns(mode):
            for path in self.user_data_dir.glob(pattern):
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                paths.append(path)
        return paths

    def _maybe_migrate_authorized_session(self, path: Path, saved):
        authority = getattr(self, "content_revision_authority", None)
        if authority is None or not isinstance(saved, dict) or not self.bank_path:
            return saved, Path(path), None
        saved_fp = str(saved.get("bank_fingerprint") or "").strip()
        try:
            current_fp = self.current_bank_fingerprint()
        except ValueError:
            return saved, Path(path), None
        if saved_fp != authority.source_bank_content_fingerprint or current_fp != authority.target_bank_content_fingerprint:
            return saved, Path(path), None
        target_path = self.session_file_for_bank(
            self.bank_path,
            mode=saved.get("mode"),
            question_ids=list(saved.get("question_ids") or []),
            question_numbers=list(saved.get("question_numbers") or []),
            builder_context=saved.get("builder_context"),
            builder_context_fingerprint=saved.get("builder_context_fingerprint"),
        )
        source_questions = None
        source_bank_path = Path(self.bank_path).parent / authority.source_bank_filename
        if source_bank_path.exists():
            try:
                source_payload = json.loads(source_bank_path.read_text(encoding="utf-8"))
                if isinstance(source_payload, dict) and isinstance(source_payload.get("questions"), list):
                    source_questions = source_payload["questions"]
            except (OSError, UnicodeError, json.JSONDecodeError):
                source_questions = None
        payload, _archive, error = self.persistence.migrate_session_file_across_approved_revision(
            Path(path),
            Path(target_path),
            list((getattr(self, "data", None) or {}).get("questions") or self._session_bank_questions()),
            authority,
            Path(self.bank_path).name,
            source_questions=source_questions,
        )
        if error is not None or payload is None:
            logging.warning("Approved content revision session migration skipped without quarantine: %s (%s)", path, error)
            return None, Path(path), error
        return payload, Path(target_path), None

    def _latest_completed_session_timestamp(self, builder_context):
        desired = canonical_builder_identity(builder_context)
        desired_fp = desired["builder_context_fingerprint"]
        latest = 0.0
        for entry in self._progress_meta().get("session_history", []):
            entry_fp = str(entry.get("builder_context_fingerprint") or "").strip()
            if not entry_fp or entry_fp != desired_fp:
                continue
            try:
                latest = max(latest, datetime.fromisoformat(str(entry.get("at") or "")).timestamp())
            except ValueError:
                continue
        return latest

    def find_resumable_session_for_builder(self, builder_context):
        if not self.bank_path:
            return None
        desired = canonical_builder_identity(builder_context)
        latest_completed_at = self._latest_completed_session_timestamp(desired["builder_context"])
        candidates = []
        experimental = is_cand01r3_active()
        available_questions = self._session_bank_questions()
        available_qnums = [q.get("question_number") for q in available_questions]
        available_ids = None if experimental else ordered_question_ids(available_questions)
        fingerprint = None if experimental else self.current_bank_fingerprint()
        for path in self._session_discovery_paths(desired["builder_context"].get("mode", self.active_session_mode)):
            if latest_completed_at and path.stat().st_mtime <= latest_completed_at:
                continue
            saved, backup, err = self.persistence.load_json_with_backup(path)
            if err or not saved:
                if err:
                    logging.warning("Skipped resumable session candidate after read failure: %s", path)
                    self._show_bad_json_warning("Session", path, backup, err)
                continue
            saved, path, migrate_error = self._maybe_migrate_authorized_session(path, saved)
            if migrate_error or not saved:
                continue
            candidate_experimental = experimental or bool(isinstance(saved, dict) and saved.get("cand01r3"))
            try:
                if candidate_experimental:
                    migrated = migrate_session_snapshot(
                        saved,
                        desired["builder_context"].get("mode", self.active_session_mode),
                        [],
                        available_question_numbers=available_qnums,
                        allow_legacy=True,
                    )
                else:
                    migrated = migrate_session_snapshot(
                        saved,
                        desired["builder_context"].get("mode", self.active_session_mode),
                        [],
                        bank_fingerprint=fingerprint,
                        available_question_ids=available_ids,
                    )
            except (TypeError, ValueError, KeyError, IndexError) as exc:
                backup = self.persistence.quarantine_invalid_runtime_file(path, label="session")
                self._show_bad_json_warning("Session", path, backup, exc)
                continue
            answers = list(migrated.get("answers", []) or [])
            if answers and all(bool(state.get("answered")) for state in answers):
                continue
            if builder_identities_match(migrated, desired):
                candidates.append((path.stat().st_mtime, path))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]

    def clear_resumable_sessions_for_builder(self, builder_context):
        if not self.bank_path:
            return 0
        desired = canonical_builder_identity(builder_context)
        removed = 0
        experimental = is_cand01r3_active()
        available_questions = self._session_bank_questions()
        available_qnums = [q.get("question_number") for q in available_questions]
        available_ids = None if experimental else ordered_question_ids(available_questions)
        fingerprint = None if experimental else self.current_bank_fingerprint()
        for path in self._session_discovery_paths(desired["builder_context"].get("mode", self.active_session_mode)):
            saved, _backup, err = self.persistence.load_json_with_backup(path)
            if err or not saved:
                continue
            saved, path, migrate_error = self._maybe_migrate_authorized_session(path, saved)
            if migrate_error or not saved:
                continue
            candidate_experimental = experimental or bool(isinstance(saved, dict) and saved.get("cand01r3"))
            try:
                if candidate_experimental:
                    migrated = migrate_session_snapshot(
                        saved,
                        desired["builder_context"].get("mode", self.active_session_mode),
                        [],
                        available_question_numbers=available_qnums,
                        allow_legacy=True,
                    )
                else:
                    migrated = migrate_session_snapshot(
                        saved,
                        desired["builder_context"].get("mode", self.active_session_mode),
                        [],
                        bank_fingerprint=fingerprint,
                        available_question_ids=available_ids,
                    )
            except (TypeError, ValueError, KeyError, IndexError):
                self.persistence.quarantine_invalid_runtime_file(path, label="session")
                continue
            if not builder_identities_match(migrated, desired):
                continue
            try:
                path.unlink()
                removed += 1
            except OSError:
                logging.warning("Could not remove completed resumable session: %s", path)
        return removed

    def refresh_session_runtime_identity(self):
        if not self.bank_path:
            return
        identity_qnums = list(
            self.session_restore_question_numbers or [q.get("question_number") for q in self.questions]
        )
        if is_cand01r3_active():
            self.session_path = self.session_file_for_bank(
                self.bank_path,
                mode=self.active_session_mode,
                question_numbers=identity_qnums,
            )
        else:
            identity_ids = list(
                getattr(self, "session_restore_question_ids", None) or self._canonical_ids_for_questions(self.questions)
            )
            self.session_path = self.session_file_for_bank(
                self.bank_path,
                mode=self.active_session_mode,
                question_numbers=identity_qnums,
                question_ids=identity_ids,
            )
        self.last_session_snapshot = None
        if hasattr(self, "session_label"):
            self.session_label.configure(text=f"Session file: {self.session_path.name}")

    def start_session_from_pool(
        self,
        pool: list[QuestionRuntimeState],
        mode=MODE_PRACTICE,
        count="All visible",
        randomize=True,
        reset_clock=True,
        preserve_if_saved=False,
        source_label=None,
        builder_context=None,
    ):
        if getattr(self, "smart_practice_prewarm", None) is not None:
            self.smart_practice_prewarm.invalidate()
        self.flush_scheduled_session_save()
        self.flush_scheduled_progress_save()
        pool = list(pool)
        if is_cand01r3_active():
            pool = filter_training_questions(pool)
            if not pool:
                return
        if mode == MODE_EXAM:
            pool = filter_new_exam_pool(pool)
        if count != "All visible":
            try:
                limit = max(0, int(count))
                if limit and len(pool) > limit:
                    pool = random.sample(pool, limit) if randomize else pool[:limit]
            except (TypeError, ValueError):
                pass
        pool = self._clone_questions(pool)
        self.answer_order_epoch += 1
        pool = self._apply_adaptive_answer_order(pool)
        if randomize:
            random.shuffle(pool)
        if not pool:
            return
        self.questions = pool
        self.session_restore_question_numbers = [q.get("question_number") for q in self.questions]
        self.session_restore_question_ids = (
            [] if is_cand01r3_active() else self._canonical_ids_for_questions(self.questions)
        )
        self.session_base_question_count = len(self.session_restore_question_numbers)
        self.active_session_mode = mode
        self.active_source_label = str(source_label or self.active_source_label or "Full bank")
        if builder_context is not None:
            identity = canonical_builder_identity(builder_context)
        else:
            identity = canonical_builder_identity(
                None,
                mode=mode,
                count=count,
                randomize=randomize,
                source_label=self.active_source_label,
                session_source=(
                    self.normalize_session_source(self.session_source_var.get())
                    if hasattr(self, "session_source_var") and hasattr(self, "normalize_session_source")
                    else None
                ),
                domain_filter=self.domain_filter_var.get() if hasattr(self, "domain_filter_var") else None,
                topic_filter=self.topic_filter_var.get() if hasattr(self, "topic_filter_var") else None,
                status_filter=(
                    self.normalize_status_filter(self.status_filter_var.get())
                    if hasattr(self, "status_filter_var") and hasattr(self, "normalize_status_filter")
                    else None
                ),
            )
        self.current_builder_context_data = identity["builder_context"]
        self.exam_reveal = mode != MODE_EXAM
        self.index = 0
        if reset_clock:
            self.elapsed_base = 0
            self.clock_started_at = time.time()
            self.checkpoints_saved = set()
        self.unlocked_rewards = set()
        self.session_rewards = []
        self.current_quests = []
        self.quest_completion_keys = set()
        self.session_boss_markers = set()
        self.session_stealth_markers = set()
        self.session_xp_gained = 0
        self.session_completion_signature = None
        self.last_session_summary = None
        self.session_answer_history = []
        self.rescue_domains_triggered = set()
        self.session_question_limit = self.calculate_session_question_limit(self.session_base_question_count)
        self.last_checkpoint_notice = ""
        self.checkpoint_label.configure(text="")
        self.clear_reward_banner()
        self.refresh_reward_badges()
        self.last_question_list_signature = None
        self.last_session_snapshot = None
        self.session_path = self.session_file_for_bank(
            self.bank_path,
            mode=mode,
            question_numbers=self.session_restore_question_numbers,
            question_ids=(None if is_cand01r3_active() else self.session_restore_question_ids),
        )
        if hasattr(self, "session_label"):
            self.session_label.configure(text=f"Session file: {self.session_path.name}")
        self.choose_session_quests()
        self.scroll_to_top_on_render = True
        if preserve_if_saved:
            resume_path = self.find_resumable_session_for_builder(self.current_builder_context_data)
            if resume_path is not None:
                self.session_path = resume_path
                if hasattr(self, "session_label"):
                    self.session_label.configure(text=f"Session file: {self.session_path.name}")
                self.load_session_if_present(skip_identity_check=True)
            else:
                self.load_session_if_present()
        self.set_sidebar_visible(False)
        self.render_question()

    def load_session_if_present(self, skip_identity_check=False):
        if not self.session_path or not self.session_path.exists():
            if self.bank_path and self.session_path:
                legacy_path = self.legacy_session_file_for_bank(self.bank_path, mode=self.active_session_mode)
                if legacy_path.exists():
                    legacy_saved, backup, err = self.persistence.load_json_with_backup(legacy_path)
                    if err:
                        logging.warning("Legacy session file reset after read failure: %s", legacy_path)
                        self._show_bad_json_warning("Legacy session", legacy_path, backup, err)
                    elif self._saved_session_matches_current(legacy_saved):
                        self.migrate_runtime_file(legacy_path, self.session_path, "session")
            if not self.session_path or not self.session_path.exists():
                return
        saved, backup, err = self.persistence.load_json_with_backup(self.session_path)
        if err:
            logging.warning("Session file reset after read failure: %s", self.session_path)
            self._show_bad_json_warning("Session", self.session_path, backup, err)
            return
        experimental_session = bool(isinstance(saved, dict) and (saved.get("cand01r3") or is_cand01r3_active()))
        if experimental_session:
            restored = restore_experimental_session(self.questions, saved)
            if not restored.accepted:
                return
            if restored.questions:
                self.questions = restored.questions
        if not skip_identity_check and not self._saved_session_matches_current(saved):
            return
        available_questions = list(self.master_questions or self.questions)
        try:
            if experimental_session:
                migrated = migrate_session_snapshot(
                    saved,
                    self.active_session_mode,
                    [q.get("question_number") for q in self.questions],
                    available_question_numbers=[q.get("question_number") for q in available_questions],
                    allow_legacy=True,
                )
            else:
                migrated = migrate_session_snapshot(
                    saved,
                    self.active_session_mode,
                    [q.get("question_number") for q in self.questions],
                    available_question_numbers=[q.get("question_number") for q in available_questions],
                    bank_fingerprint=self.current_bank_fingerprint(),
                    available_question_ids=ordered_question_ids(available_questions),
                )
        except (TypeError, ValueError, KeyError, IndexError) as exc:
            backup = self.persistence.quarantine_invalid_runtime_file(self.session_path, label="session")
            logging.warning("Session file quarantined after validation failure: %s", self.session_path)
            self._show_bad_json_warning("Session", self.session_path, backup, exc)
            return
        if not experimental_session and not skip_identity_check:
            current = getattr(self, "current_builder_context_data", None)
            if isinstance(current, dict) and current:
                current_identity = canonical_builder_identity(current)
                if current_identity.get("builder_context_fingerprint") and not builder_identities_match(
                    migrated, current_identity
                ):
                    return
        saved_answers = list(migrated.get("answers", []) or [])
        if saved_answers and all(bool(state.get("answered")) for state in saved_answers):
            return

        if not experimental_session:
            saved_ids = list(migrated.get("question_ids", []) or [])
            saved_restore_ids = list(migrated.get("restore_question_ids", []) or saved_ids)
            try:
                source_questions = self._questions_for_canonical_ids(saved_ids)
                restore_questions = self._questions_for_canonical_ids(saved_restore_ids)
            except ValueError as exc:
                backup = self.persistence.quarantine_invalid_runtime_file(self.session_path, label="session")
                logging.warning("Session file quarantined after canonical ID resolution failure: %s", self.session_path)
                self._show_bad_json_warning("Session", self.session_path, backup, exc)
                return
            self.questions = self._clone_questions(source_questions)
            self.session_restore_question_ids = saved_restore_ids
            self.session_restore_question_numbers = [q.get("question_number") for q in restore_questions]

        self.index = max(0, min(int(migrated.get("current_index", 0)), len(self.questions) - 1))
        self.elapsed_base = int(migrated.get("elapsed_seconds", 0))
        self.clock_started_at = time.time()
        self.checkpoints_saved = set(migrated.get("checkpoints_saved", []))
        self.exam_reveal = bool(migrated.get("exam_reveal", self.active_session_mode != MODE_EXAM))
        self.active_source_label = str(migrated.get("source_label") or self.active_source_label)
        self.session_rewards = list(migrated.get("session_rewards", []))
        self.unlocked_rewards = set(migrated.get("unlocked_rewards", []))
        self.session_answer_history = list(migrated.get("session_answer_history", []))
        self.current_quests = list(migrated.get("current_quests", self.current_quests))
        self.quest_completion_keys = set(migrated.get("quest_completion_keys", []))
        self.session_boss_markers = set(migrated.get("session_boss_markers", []))
        self.session_stealth_markers = set(migrated.get("session_stealth_markers", []))
        self.session_xp_gained = int(migrated.get("session_xp_gained", 0))
        self.current_builder_context_data = dict(migrated.get("builder_context") or {})
        if not experimental_session:
            self.restore_builder_ui_from_context(self.current_builder_context_data)
        if experimental_session:
            saved_restore_qnums = list(
                migrated.get("restore_question_numbers", []) or self.session_restore_question_numbers
            )
            if saved_restore_qnums:
                self.session_restore_question_numbers = saved_restore_qnums
        self.session_base_question_count = int(
            migrated.get("session_base_question_count")
            or len(self.session_restore_question_numbers)
            or len(self.questions)
        )
        self.session_question_limit = int(
            migrated.get("session_question_limit")
            or self.calculate_session_question_limit(self.session_base_question_count)
        )
        if experimental_session:
            saved_qnums = list(migrated.get("question_numbers", []) or [])
            current_qnums = [q.get("question_number") for q in self.questions]
            if saved_qnums and saved_qnums != current_qnums:
                lookup = {q.get("question_number"): q for q in self.master_questions}
                source_questions = []
                for qnum in saved_qnums:
                    source = lookup.get(qnum)
                    if source is not None:
                        source_questions.append(source)
                if len(source_questions) == len(saved_qnums):
                    self.questions = self._clone_questions(source_questions)
        self.last_session_snapshot = json.dumps(migrated, sort_keys=True, separators=(",", ":"))

        if experimental_session:
            restore_pairs = [
                (question, state) for question, state in zip(self.questions, migrated.get("answers", []), strict=False)
            ]
        else:
            try:
                answer_map = answer_states_by_question_id(list(migrated.get("answers", [])))
                restore_pairs = [(question, answer_map[canonical_question_id(question)]) for question in self.questions]
            except (KeyError, ValueError) as exc:
                backup = self.persistence.quarantine_invalid_runtime_file(self.session_path, label="session")
                logging.warning("Session file quarantined after answer identity failure: %s", self.session_path)
                self._show_bad_json_warning("Session", self.session_path, backup, exc)
                return

        progress_changed = False
        for q, state in restore_pairs:
            merged_state = dict(state)
            try:
                self._migrate_legacy_repair_concept_key(q, merged_state)
            except ValueError as exc:
                logging.warning("Session restore skipped after repair concept migration failure: %s", exc)
                self._show_bad_json_warning("Session", self.session_path, None, exc)
                return
            merged_state["flagged"] = bool(state.get("flagged")) or bool(q.get("flagged"))
            merged_state["suspended"] = bool(state.get("suspended")) or bool(q.get("suspended"))
            apply_answer_state(q, merged_state)
            if q.get("answered") and not str(q.get("last_confidence") or "").strip():
                q["last_confidence"] = normalize_confidence(q.get("last_confidence"))
            existing = self._progress_record(q, create=False)
            if q.get("answered") and not int((existing or {}).get("attempts", 0)):
                self._progress_questions()[self._question_key(q)] = update_progress_record(
                    existing,
                    q.get("selected", []),
                    self._question_correct(q),
                    confidence=q.get("last_confidence"),
                    miss_reason=q.get("last_miss_reason"),
                )
                progress_changed = True
            if q.get("flagged"):
                rec = self._progress_record(q, create=True)
                self._progress_questions()[self._question_key(q)] = set_progress_flag(rec, True)
                self.set_flag_by_question_number(q.get("question_number"), True)
                progress_changed = True
            if q.get("suspended"):
                rec = self._progress_record(q, create=True)
                self._progress_questions()[self._question_key(q)] = set_progress_suspended(rec, True)
                self.set_suspended_by_question_number(q.get("question_number"), True)
                progress_changed = True
        progress_history = list(self._progress_history()) if hasattr(self, "_progress_history") else []
        bind_legacy_answer_event_ids(
            runtime_questions=self.questions,
            session_history=self.session_answer_history,
            progress_history=progress_history,
        )
        if progress_changed:
            self.save_progress()
        self.refresh_session_quests()
        self.refresh_reward_badges()

    def _migrate_legacy_repair_concept_key(self, question, answer_state):
        legacy_key = answer_state.get("repair_concept_key")
        if not legacy_key:
            return
        if not isinstance(legacy_key, str):
            raise ValueError("repair_concept_key must be a string")
        if any(marker in legacy_key for marker in ("(", ")", "[", "]", "{", "}", "<", ">", ",")):
            raise ValueError(f"Malformed repair_concept_key: {legacy_key}")
        canonical_key = graph_concept_key_for_question(question)[0]
        if legacy_key == canonical_key:
            return
        known_canonical_prefixes = (
            "coverage::",
            "objective_topic::",
            "repair::",
            "group::",
            "domain_topic::",
            "question::",
        )
        lowered = legacy_key.casefold()
        if lowered.startswith(known_canonical_prefixes):
            if lowered != canonical_key.casefold():
                raise ValueError(f"Unknown legacy repair_concept_key for restored question: {legacy_key}")
            if legacy_key != canonical_key:
                answer_state["repair_concept_key"] = canonical_key
            return
        if "::" not in legacy_key:
            raise ValueError(f"Unknown repair_concept_key format: {legacy_key}")
        legacy_kind, legacy_value = legacy_key.split("::", 1)
        legacy_kind = legacy_kind.strip().casefold()
        legacy_value = legacy_value.strip().casefold()
        if legacy_kind == "topic":
            expected_values = [
                str(topic).strip().casefold() for topic in question.get("topics", []) if str(topic).strip()
            ]
        elif legacy_kind == "objective":
            expected_values = [str(question.get("objective_code") or "").strip().casefold()]
        elif legacy_kind == "domain":
            expected_values = [str(question.get("domain") or "").strip().casefold()]
        else:
            raise ValueError(f"Unknown repair_concept_key format: {legacy_key}")
        if legacy_value not in [value for value in expected_values if value]:
            raise ValueError(f"Unknown legacy repair_concept_key for restored question: {legacy_key}")
        answer_state["legacy_repair_concept_key"] = legacy_key
        answer_state["repair_concept_key"] = canonical_key
        snapshot = answer_state.get("prediction_snapshot")
        if isinstance(snapshot, dict) and snapshot.get("concept_key") == legacy_key:
            snapshot["concept_key"] = answer_state["repair_concept_key"]

    def save_session(self, show_notice=False, *, force_complete=False):
        if not self.questions or not self.session_path:
            return
        self.save_queue.cancel("session")
        is_complete = self._all_session_questions_resolved_for_finish() or bool(
            force_complete and self.active_session_mode == MODE_EXAM
        )
        if is_complete:
            self.clear_resumable_sessions_for_builder(self.current_builder_context_data)
            if self.session_path.exists():
                self.session_path.unlink()
            self.last_session_snapshot = None
            self.session_path = None
            self.session_label.configure(text="Session complete: progress saved")
            return
        snapshot_kwargs = {
            "app_version": APP_VERSION,
            "bank_file": self.bank_path.name if self.bank_path else "",
            "mode": self.active_session_mode,
            "builder_context": self.current_builder_context_data,
            "source_label": self.active_source_label,
            "question_numbers": [q.get("question_number") for q in self.questions],
            "restore_question_numbers": list(self.session_restore_question_numbers),
            "session_base_question_count": int(
                self.session_base_question_count or len(self.session_restore_question_numbers) or len(self.questions)
            ),
            "session_question_limit": int(
                self.session_question_limit
                or self.calculate_session_question_limit(self.session_base_question_count or len(self.questions))
            ),
            "current_index": self.index,
            "elapsed_seconds": self.current_elapsed_seconds(),
            "exam_reveal": self.exam_reveal,
            "checkpoints_saved": sorted(list(self.checkpoints_saved), key=lambda x: int(x)),
            "session_rewards": list(self.session_rewards),
            "unlocked_rewards": sorted(list(self.unlocked_rewards)),
            "session_answer_history": list(self.session_answer_history),
            "current_quests": list(self.current_quests),
            "quest_completion_keys": sorted(list(self.quest_completion_keys)),
            "session_boss_markers": sorted(list(self.session_boss_markers)),
            "session_stealth_markers": sorted(list(self.session_stealth_markers)),
            "session_xp_gained": int(self.session_xp_gained),
            "answers": [serialize_answer_state(q) for q in self.questions],
        }
        if is_cand01r3_active():
            snapshot = build_session_snapshot(**snapshot_kwargs)
        else:
            snapshot = build_session_snapshot(
                **snapshot_kwargs,
                bank_fingerprint=self.current_bank_fingerprint(),
                question_ids=self._canonical_ids_for_questions(self.questions),
                restore_question_ids=list(
                    getattr(self, "session_restore_question_ids", None)
                    or self._canonical_ids_for_questions(self.questions)
                ),
            )
        payload = dict(snapshot)
        if is_cand01r3_active():
            payload["cand01r3"] = persistable_authority_metadata()
            payload["question_ids"] = [
                str(question.get("id") or question.get("question_id") or "")
                for question in self.questions
                if str(question.get("id") or question.get("question_id") or "")
            ]
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        if serialized != self.last_session_snapshot:
            self.persistence.write_json(self.session_path, payload)
            self.last_session_snapshot = serialized
        self.session_label.configure(text=f"Session file: {self.session_path.name}")
        if show_notice:
            self.checkpoint_label.configure(text="Session saved.")
            self.root.after(2500, self._clear_checkpoint_notice)

    def schedule_session_save(self, delay_ms=250):
        if not self.questions or not self.session_path:
            return
        self.save_queue.schedule("session", lambda: self.save_session(show_notice=False), delay_ms=delay_ms)

    def flush_scheduled_session_save(self):
        self.save_queue.flush("session")

    def _clear_checkpoint_notice(self):
        if self.checkpoint_label.cget("text") == "Session saved.":
            self.checkpoint_label.configure(text=self.last_checkpoint_notice)

    def maybe_save_checkpoint(self):
        answered_count = sum(1 for q in self.questions if q.get("answered"))
        if answered_count and answered_count % 22 == 0 and self.bank_path:
            marker = str(answered_count)
            if marker not in self.checkpoints_saved:
                p = self.checkpoint_file_for_bank(self.bank_path, answered_count)
                payload = {
                    "app_version": APP_VERSION,
                    "bank_file": self.bank_path.name,
                    "mode": self.active_session_mode,
                    "answered_count": answered_count,
                    "current_index": self.index,
                    "elapsed_seconds": self.current_elapsed_seconds(),
                    "question_numbers": [q.get("question_number") for q in self.questions],
                    "answers": [serialize_answer_state(q) for q in self.questions],
                }
                self.persistence.write_checkpoint(p, payload)
                self.checkpoints_saved.add(marker)
                self.last_checkpoint_notice = f"Checkpoint saved at {answered_count} answered."
                self.checkpoint_label.configure(text=self.last_checkpoint_notice)
