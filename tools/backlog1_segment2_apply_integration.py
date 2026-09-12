from pathlib import Path


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new, 1)


def replace_all_exact(text: str, old: str, new: str, *, count: int, label: str) -> str:
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(f"{label}: expected {count} occurrences, found {actual}")
    return text.replace(old, new)


def replace_method(text: str, name: str, next_name: str, replacement: str) -> str:
    start = text.index(f"    def {name}(")
    end = text.index(f"\n    def {next_name}(", start)
    return text[:start] + replacement.rstrip() + "\n" + text[end:]


def patch_session_store() -> None:
    path = Path("session_store.py")
    text = path.read_text(encoding="utf-8")
    text = replace_all_exact(
        text,
        '''            "bank_fingerprint",\n            "question_ids",\n            "restore_question_ids",''',
        '''            "bank_fingerprint",\n            "restore_question_ids",''',
        count=2,
        label="canonical snapshot marker compatibility",
    )
    anchor = '''    if len(ids) != len(set(ids)):\n        raise ValueError(f"Duplicate canonical question ID in {field}.")\n    return ids\n\n\ndef migrate_session_snapshot('''
    replacement = '''    if len(ids) != len(set(ids)):\n        raise ValueError(f"Duplicate canonical question ID in {field}.")\n    return ids\n\n\ndef answer_states_by_question_id(answers: list[Mapping[str, Any]]) -> dict[str, SessionAnswerState]:\n    by_id: dict[str, SessionAnswerState] = {}\n    for answer in answers:\n        if not isinstance(answer, Mapping):\n            raise ValueError("Session answer row must be a mapping.")\n        row = cast(SessionAnswerState, dict(answer))\n        question_id = str(row.get("question_id") or "").strip()\n        if not question_id:\n            raise ValueError("Canonical session answer row is missing question_id.")\n        if question_id in by_id:\n            raise ValueError("Duplicate canonical question ID in session answers.")\n        by_id[question_id] = row\n    return by_id\n\n\ndef migrate_session_snapshot('''
    text = replace_once(text, anchor, replacement, label="answer map helper")
    path.write_text(text, encoding="utf-8")


def patch_app_mixin() -> None:
    path = Path("app_session_persistence_mixin.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from progress_store import set_progress_flag, set_progress_suspended, update_progress_record\n",
        "from progress_store import set_progress_flag, set_progress_suspended, update_progress_record\nfrom question_identity import canonical_question_id\nfrom session_identity import bank_content_fingerprint, canonical_session_signature, ordered_question_ids\n",
        label="session identity app imports",
    )
    text = replace_once(
        text,
        "from session_store import (\n    build_session_snapshot,\n",
        "from session_store import (\n    answer_states_by_question_id,\n    build_session_snapshot,\n",
        label="answer map import",
    )

    text = replace_method(
        text,
        "current_session_signature",
        "runtime_bank_stem",
        '''    def _session_bank_questions(self):
        source = list((getattr(self, 'master_questions', None) or self.questions) or [])
        if not source:
            raise ValueError('Session identity requires a loaded question bank.')
        return source

    def current_bank_fingerprint(self):
        return bank_content_fingerprint(self._session_bank_questions())

    def _canonical_ids_for_questions(self, questions):
        return ordered_question_ids(list(questions or []))

    def _questions_for_canonical_ids(self, question_ids):
        source = self._session_bank_questions()
        source_ids = ordered_question_ids(source)
        lookup = dict(zip(source_ids, source))
        resolved = []
        for question_id in question_ids:
            canonical_id = str(question_id or '').strip()
            question = lookup.get(canonical_id)
            if question is None:
                raise ValueError(f'Unknown canonical question reference in session: {canonical_id}')
            resolved.append(question)
        if len(resolved) != len(question_ids):
            raise ValueError('Session canonical question identity could not be resolved exactly.')
        return resolved

    def _questions_for_question_numbers(self, question_numbers):
        source = self._session_bank_questions()
        lookup = {}
        for question in source:
            number = str(question.get('question_number') or '').strip()
            if not number:
                continue
            if number in lookup:
                raise ValueError(f'Ambiguous question number in loaded bank: {number}')
            lookup[number] = question
        resolved = []
        for question_number in question_numbers:
            number = str(question_number or '').strip()
            question = lookup.get(number)
            if question is None:
                raise ValueError(f'Unknown question number in loaded bank: {number}')
            resolved.append(question)
        return resolved

    def current_session_signature(self, mode=None, questions: list[QuestionRuntimeState] | None = None, question_numbers=None):
        mode = str(mode or self.active_session_mode or MODE_PRACTICE)
        if is_cand01r3_active():
            if question_numbers is None:
                questions = questions if questions is not None else self.questions
                question_numbers = [q.get('question_number', '') for q in questions]
            return session_signature(mode, list(question_numbers))
        if questions is None:
            if question_numbers is None:
                questions = self.questions
            else:
                questions = self._questions_for_question_numbers(question_numbers)
        question_ids = self._canonical_ids_for_questions(questions)
        return canonical_session_signature(mode, self.current_bank_fingerprint(), question_ids)
''',
    )

    text = replace_method(
        text,
        "session_file_for_bank",
        "checkpoint_file_for_bank",
        '''    def session_file_for_bank(
        self,
        bank_path,
        mode=None,
        questions: list[QuestionRuntimeState] | None = None,
        question_numbers=None,
        question_ids=None,
    ):
        mode = str(mode or self.active_session_mode or MODE_PRACTICE)
        if is_cand01r3_active():
            if question_numbers is None:
                questions = questions if questions is not None else self.questions
                question_numbers = [q.get('question_number') for q in questions]
            return session_file_path(self.user_data_dir, bank_path, mode, list(question_numbers))
        if question_ids is None:
            if questions is None:
                if question_numbers is None:
                    questions = self.questions
                else:
                    questions = self._questions_for_question_numbers(question_numbers)
            question_ids = self._canonical_ids_for_questions(questions)
        canonical_ids = [str(question_id or '').strip() for question_id in question_ids]
        if not canonical_ids or any(not question_id for question_id in canonical_ids):
            raise ValueError('Session file identity requires canonical question IDs.')
        if question_numbers is None:
            if questions is not None:
                question_numbers = [q.get('question_number') for q in questions]
            else:
                question_numbers = [q.get('question_number') for q in self._questions_for_canonical_ids(canonical_ids)]
        return session_file_path(
            self.user_data_dir,
            bank_path,
            mode,
            list(question_numbers),
            bank_fingerprint=self.current_bank_fingerprint(),
            question_ids=canonical_ids,
        )
''',
    )

    text = replace_method(
        text,
        "_saved_session_matches_current",
        "normalize_builder_context",
        '''    def _saved_session_matches_current(self, saved, questions: list[QuestionRuntimeState] | None = None):
        questions = questions if questions is not None else self.questions
        current_qnums = [q.get('question_number') for q in questions]
        restore_qnums = list(self.session_restore_question_numbers or current_qnums)
        if is_cand01r3_active() or (isinstance(saved, dict) and saved.get('cand01r3')):
            return saved_session_matches_current(
                saved,
                self.active_session_mode,
                current_qnums,
                restore_qnums,
                allow_legacy=True,
            )
        current_ids = self._canonical_ids_for_questions(questions)
        restore_ids = list(getattr(self, 'session_restore_question_ids', None) or current_ids)
        return saved_session_matches_current(
            saved,
            self.active_session_mode,
            current_qnums,
            restore_qnums,
            bank_fingerprint=self.current_bank_fingerprint(),
            current_question_ids=current_ids,
            restore_question_ids=restore_ids,
        )
''',
    )

    text = replace_method(
        text,
        "find_resumable_session_for_builder",
        "clear_resumable_sessions_for_builder",
        '''    def find_resumable_session_for_builder(self, builder_context):
        if not self.bank_path:
            return None
        desired = self.normalize_builder_context(builder_context)
        latest_completed_at = self._latest_completed_session_timestamp(desired)
        candidates = []
        experimental = is_cand01r3_active()
        available_questions = self._session_bank_questions()
        available_qnums = [q.get('question_number') for q in available_questions]
        available_ids = None if experimental else ordered_question_ids(available_questions)
        fingerprint = None if experimental else self.current_bank_fingerprint()
        for path in self.user_data_dir.glob(self._session_builder_glob_pattern(desired.get('mode', self.active_session_mode))):
            if latest_completed_at and path.stat().st_mtime <= latest_completed_at:
                continue
            saved, backup, err = self.persistence.load_json_with_backup(path)
            if err or not saved:
                if err:
                    logging.warning('Skipped resumable session candidate after read failure: %s', path)
                    self._show_bad_json_warning('Session', path, backup, err)
                continue
            candidate_experimental = experimental or bool(isinstance(saved, dict) and saved.get('cand01r3'))
            try:
                if candidate_experimental:
                    migrated = migrate_session_snapshot(
                        saved,
                        desired.get('mode', self.active_session_mode),
                        [],
                        available_question_numbers=available_qnums,
                        allow_legacy=True,
                    )
                else:
                    migrated = migrate_session_snapshot(
                        saved,
                        desired.get('mode', self.active_session_mode),
                        [],
                        bank_fingerprint=fingerprint,
                        available_question_ids=available_ids,
                    )
            except (TypeError, ValueError, KeyError, IndexError) as exc:
                backup = self.persistence.quarantine_invalid_runtime_file(path, label='session')
                self._show_bad_json_warning('Session', path, backup, exc)
                continue
            answers = list(migrated.get('answers', []) or [])
            if answers and all(bool(state.get('answered')) for state in answers):
                continue
            if self._builder_context_matches(migrated.get('builder_context'), desired):
                candidates.append((path.stat().st_mtime, path))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]
''',
    )

    text = replace_method(
        text,
        "clear_resumable_sessions_for_builder",
        "refresh_session_runtime_identity",
        '''    def clear_resumable_sessions_for_builder(self, builder_context):
        if not self.bank_path:
            return 0
        desired = self.normalize_builder_context(builder_context)
        removed = 0
        experimental = is_cand01r3_active()
        available_questions = self._session_bank_questions()
        available_qnums = [q.get('question_number') for q in available_questions]
        available_ids = None if experimental else ordered_question_ids(available_questions)
        fingerprint = None if experimental else self.current_bank_fingerprint()
        for path in self.user_data_dir.glob(self._session_builder_glob_pattern(desired.get('mode', self.active_session_mode))):
            saved, _backup, err = self.persistence.load_json_with_backup(path)
            if err or not saved:
                continue
            candidate_experimental = experimental or bool(isinstance(saved, dict) and saved.get('cand01r3'))
            try:
                if candidate_experimental:
                    migrated = migrate_session_snapshot(
                        saved,
                        desired.get('mode', self.active_session_mode),
                        [],
                        available_question_numbers=available_qnums,
                        allow_legacy=True,
                    )
                else:
                    migrated = migrate_session_snapshot(
                        saved,
                        desired.get('mode', self.active_session_mode),
                        [],
                        bank_fingerprint=fingerprint,
                        available_question_ids=available_ids,
                    )
            except (TypeError, ValueError, KeyError, IndexError):
                self.persistence.quarantine_invalid_runtime_file(path, label='session')
                continue
            if not self._builder_context_matches(migrated.get('builder_context'), desired):
                continue
            try:
                path.unlink()
                removed += 1
            except OSError:
                logging.warning('Could not remove completed resumable session: %s', path)
        return removed
''',
    )

    text = replace_method(
        text,
        "refresh_session_runtime_identity",
        "start_session_from_pool",
        '''    def refresh_session_runtime_identity(self):
        if not self.bank_path:
            return
        identity_qnums = list(self.session_restore_question_numbers or [q.get('question_number') for q in self.questions])
        if is_cand01r3_active():
            self.session_path = self.session_file_for_bank(
                self.bank_path,
                mode=self.active_session_mode,
                question_numbers=identity_qnums,
            )
        else:
            identity_ids = list(getattr(self, 'session_restore_question_ids', None) or self._canonical_ids_for_questions(self.questions))
            self.session_path = self.session_file_for_bank(
                self.bank_path,
                mode=self.active_session_mode,
                question_numbers=identity_qnums,
                question_ids=identity_ids,
            )
        self.last_session_snapshot = None
        if hasattr(self, 'session_label'):
            self.session_label.configure(text=f'Session file: {self.session_path.name}')
''',
    )

    text = replace_once(
        text,
        '''        self.questions = pool\n        self.session_restore_question_numbers = [q.get('question_number') for q in self.questions]\n        self.session_base_question_count = len(self.session_restore_question_numbers)\n''',
        '''        self.questions = pool\n        self.session_restore_question_numbers = [q.get('question_number') for q in self.questions]\n        self.session_restore_question_ids = (\n            [] if is_cand01r3_active() else self._canonical_ids_for_questions(self.questions)\n        )\n        self.session_base_question_count = len(self.session_restore_question_numbers)\n''',
        label="start session restore identity",
    )
    text = replace_once(
        text,
        '''        self.session_path = self.session_file_for_bank(\n            self.bank_path,\n            mode=mode,\n            question_numbers=self.session_restore_question_numbers,\n        )\n''',
        '''        self.session_path = self.session_file_for_bank(\n            self.bank_path,\n            mode=mode,\n            question_numbers=self.session_restore_question_numbers,\n            question_ids=(None if is_cand01r3_active() else self.session_restore_question_ids),\n        )\n''',
        label="start session canonical path",
    )

    text = replace_method(
        text,
        "load_session_if_present",
        "_migrate_legacy_repair_concept_key",
        '''    def load_session_if_present(self, skip_identity_check=False):
        if not self.session_path or not self.session_path.exists():
            if self.bank_path and self.session_path:
                legacy_path = self.legacy_session_file_for_bank(self.bank_path, mode=self.active_session_mode)
                if legacy_path.exists():
                    legacy_saved, backup, err = self.persistence.load_json_with_backup(legacy_path)
                    if err:
                        logging.warning('Legacy session file reset after read failure: %s', legacy_path)
                        self._show_bad_json_warning('Legacy session', legacy_path, backup, err)
                    elif self._saved_session_matches_current(legacy_saved):
                        self.migrate_runtime_file(legacy_path, self.session_path, 'session')
            if not self.session_path or not self.session_path.exists():
                return
        saved, backup, err = self.persistence.load_json_with_backup(self.session_path)
        if err:
            logging.warning('Session file reset after read failure: %s', self.session_path)
            self._show_bad_json_warning('Session', self.session_path, backup, err)
            return
        experimental_session = bool(
            isinstance(saved, dict) and (saved.get('cand01r3') or is_cand01r3_active())
        )
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
                    [q.get('question_number') for q in self.questions],
                    available_question_numbers=[q.get('question_number') for q in available_questions],
                    allow_legacy=True,
                )
            else:
                migrated = migrate_session_snapshot(
                    saved,
                    self.active_session_mode,
                    [q.get('question_number') for q in self.questions],
                    available_question_numbers=[q.get('question_number') for q in available_questions],
                    bank_fingerprint=self.current_bank_fingerprint(),
                    available_question_ids=ordered_question_ids(available_questions),
                )
        except (TypeError, ValueError, KeyError, IndexError) as exc:
            backup = self.persistence.quarantine_invalid_runtime_file(self.session_path, label='session')
            logging.warning('Session file quarantined after validation failure: %s', self.session_path)
            self._show_bad_json_warning('Session', self.session_path, backup, exc)
            return
        saved_answers = list(migrated.get('answers', []) or [])
        if saved_answers and all(bool(state.get('answered')) for state in saved_answers):
            return

        if not experimental_session:
            saved_ids = list(migrated.get('question_ids', []) or [])
            saved_restore_ids = list(migrated.get('restore_question_ids', []) or saved_ids)
            try:
                source_questions = self._questions_for_canonical_ids(saved_ids)
                restore_questions = self._questions_for_canonical_ids(saved_restore_ids)
            except ValueError as exc:
                backup = self.persistence.quarantine_invalid_runtime_file(self.session_path, label='session')
                logging.warning('Session file quarantined after canonical ID resolution failure: %s', self.session_path)
                self._show_bad_json_warning('Session', self.session_path, backup, exc)
                return
            self.questions = self._clone_questions(source_questions)
            self.session_restore_question_ids = saved_restore_ids
            self.session_restore_question_numbers = [q.get('question_number') for q in restore_questions]

        self.index = max(0, min(int(migrated.get('current_index', 0)), len(self.questions) - 1))
        self.elapsed_base = int(migrated.get('elapsed_seconds', 0))
        self.clock_started_at = time.time()
        self.checkpoints_saved = set(migrated.get('checkpoints_saved', []))
        self.exam_reveal = bool(migrated.get('exam_reveal', self.active_session_mode != MODE_EXAM))
        self.active_source_label = str(migrated.get('source_label') or self.active_source_label)
        self.session_rewards = list(migrated.get('session_rewards', []))
        self.unlocked_rewards = set(migrated.get('unlocked_rewards', []))
        self.session_answer_history = [] if is_measurement_answer_mode() else list(migrated.get('session_answer_history', []))
        self.current_quests = list(migrated.get('current_quests', self.current_quests))
        self.quest_completion_keys = set(migrated.get('quest_completion_keys', []))
        self.session_boss_markers = set(migrated.get('session_boss_markers', []))
        self.session_stealth_markers = set(migrated.get('session_stealth_markers', []))
        self.session_xp_gained = int(migrated.get('session_xp_gained', 0))
        self.current_builder_context_data = self.normalize_builder_context(
            migrated.get('builder_context'),
            mode=self.active_session_mode,
            count=migrated.get('session_base_question_count'),
            source_label=migrated.get('source_label'),
        )
        if experimental_session:
            saved_restore_qnums = list(migrated.get('restore_question_numbers', []) or self.session_restore_question_numbers)
            if saved_restore_qnums:
                self.session_restore_question_numbers = saved_restore_qnums
        self.session_base_question_count = int(
            migrated.get('session_base_question_count')
            or len(self.session_restore_question_numbers)
            or len(self.questions)
        )
        self.session_question_limit = int(
            migrated.get('session_question_limit')
            or self.calculate_session_question_limit(self.session_base_question_count)
        )
        if experimental_session:
            saved_qnums = list(migrated.get('question_numbers', []) or [])
            current_qnums = [q.get('question_number') for q in self.questions]
            if saved_qnums and saved_qnums != current_qnums and not is_measurement_answer_mode():
                lookup = {q.get('question_number'): q for q in self.master_questions}
                source_questions = []
                for qnum in saved_qnums:
                    source = lookup.get(qnum)
                    if source is not None:
                        source_questions.append(source)
                if len(source_questions) == len(saved_qnums):
                    self.questions = self._clone_questions(source_questions)
        self.last_session_snapshot = json.dumps(migrated, sort_keys=True, separators=(',', ':'))

        if experimental_session:
            restore_pairs = [
                (question, state)
                for question, state in zip(self.questions, migrated.get('answers', []))
            ]
        else:
            try:
                answer_map = answer_states_by_question_id(list(migrated.get('answers', [])))
                restore_pairs = [
                    (question, answer_map[canonical_question_id(question)])
                    for question in self.questions
                ]
            except (KeyError, ValueError) as exc:
                backup = self.persistence.quarantine_invalid_runtime_file(self.session_path, label='session')
                logging.warning('Session file quarantined after answer identity failure: %s', self.session_path)
                self._show_bad_json_warning('Session', self.session_path, backup, exc)
                return

        progress_changed = False
        for q, state in restore_pairs:
            merged_state = dict(state)
            try:
                self._migrate_legacy_repair_concept_key(q, merged_state)
            except ValueError as exc:
                logging.warning('Session restore skipped after repair concept migration failure: %s', exc)
                self._show_bad_json_warning('Session', self.session_path, None, exc)
                return
            merged_state['flagged'] = bool(state.get('flagged')) or bool(q.get('flagged'))
            merged_state['suspended'] = bool(state.get('suspended')) or bool(q.get('suspended'))
            apply_answer_state(q, merged_state)
            existing = self._progress_record(q, create=False)
            if is_measurement_answer_mode():
                continue
            if q.get('answered') and not int((existing or {}).get('attempts', 0)):
                self._progress_questions()[self._question_key(q)] = update_progress_record(
                    existing,
                    q.get('selected', []),
                    self._question_correct(q),
                    confidence=q.get('last_confidence'),
                    miss_reason=q.get('last_miss_reason'),
                )
                progress_changed = True
            if q.get('flagged'):
                rec = self._progress_record(q, create=True)
                self._progress_questions()[self._question_key(q)] = set_progress_flag(rec, True)
                self.set_flag_by_question_number(q.get('question_number'), True)
                progress_changed = True
            if q.get('suspended'):
                rec = self._progress_record(q, create=True)
                self._progress_questions()[self._question_key(q)] = set_progress_suspended(rec, True)
                self.set_suspended_by_question_number(q.get('question_number'), True)
                progress_changed = True
        if progress_changed:
            self.save_progress()
        self.refresh_session_quests()
        self.refresh_reward_badges()
''',
    )

    old_snapshot_block = '''        snapshot = build_session_snapshot(
            app_version=APP_VERSION,
            bank_file=self.bank_path.name if self.bank_path else '',
            mode=self.active_session_mode,
            builder_context=self.current_builder_context_data,
            source_label=self.active_source_label,
            question_numbers=[q.get('question_number') for q in self.questions],
            restore_question_numbers=list(self.session_restore_question_numbers),
            session_base_question_count=int(self.session_base_question_count or len(self.session_restore_question_numbers) or len(self.questions)),
            session_question_limit=int(self.session_question_limit or self.calculate_session_question_limit(self.session_base_question_count or len(self.questions))),
            current_index=self.index,
            elapsed_seconds=self.current_elapsed_seconds(),
            exam_reveal=self.exam_reveal,
            checkpoints_saved=sorted(list(self.checkpoints_saved), key=lambda x: int(x)),
            session_rewards=list(self.session_rewards),
            unlocked_rewards=sorted(list(self.unlocked_rewards)),
            session_answer_history=([] if is_measurement_answer_mode() else list(self.session_answer_history)),
            current_quests=list(self.current_quests),
            quest_completion_keys=sorted(list(self.quest_completion_keys)),
            session_boss_markers=sorted(list(self.session_boss_markers)),
            session_stealth_markers=sorted(list(self.session_stealth_markers)),
            session_xp_gained=int(self.session_xp_gained),
            answers=[sanitize_measurement_answer_state(q, serialize_answer_state(q)) for q in self.questions],
        )
        payload = dict(snapshot)
'''
    new_snapshot_block = '''        snapshot_kwargs = {
            'app_version': APP_VERSION,
            'bank_file': self.bank_path.name if self.bank_path else '',
            'mode': self.active_session_mode,
            'builder_context': self.current_builder_context_data,
            'source_label': self.active_source_label,
            'question_numbers': [q.get('question_number') for q in self.questions],
            'restore_question_numbers': list(self.session_restore_question_numbers),
            'session_base_question_count': int(self.session_base_question_count or len(self.session_restore_question_numbers) or len(self.questions)),
            'session_question_limit': int(self.session_question_limit or self.calculate_session_question_limit(self.session_base_question_count or len(self.questions))),
            'current_index': self.index,
            'elapsed_seconds': self.current_elapsed_seconds(),
            'exam_reveal': self.exam_reveal,
            'checkpoints_saved': sorted(list(self.checkpoints_saved), key=lambda x: int(x)),
            'session_rewards': list(self.session_rewards),
            'unlocked_rewards': sorted(list(self.unlocked_rewards)),
            'session_answer_history': ([] if is_measurement_answer_mode() else list(self.session_answer_history)),
            'current_quests': list(self.current_quests),
            'quest_completion_keys': sorted(list(self.quest_completion_keys)),
            'session_boss_markers': sorted(list(self.session_boss_markers)),
            'session_stealth_markers': sorted(list(self.session_stealth_markers)),
            'session_xp_gained': int(self.session_xp_gained),
            'answers': [sanitize_measurement_answer_state(q, serialize_answer_state(q)) for q in self.questions],
        }
        if is_cand01r3_active():
            snapshot = build_session_snapshot(**snapshot_kwargs)
        else:
            snapshot = build_session_snapshot(
                **snapshot_kwargs,
                bank_fingerprint=self.current_bank_fingerprint(),
                question_ids=self._canonical_ids_for_questions(self.questions),
                restore_question_ids=list(
                    getattr(self, 'session_restore_question_ids', None)
                    or self._canonical_ids_for_questions(self.questions)
                ),
            )
        payload = dict(snapshot)
'''
    text = replace_once(text, old_snapshot_block, new_snapshot_block, label="canonical session save")
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_session_store()
    patch_app_mixin()
