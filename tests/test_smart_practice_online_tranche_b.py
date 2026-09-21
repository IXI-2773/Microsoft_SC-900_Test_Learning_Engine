import json
import unittest
from unittest import mock

from app_constants import MODE_SMART_PRACTICE
from builder_identity import builder_context_fingerprint
from smart_practice_online import (
    MAX_REPLACEMENTS_PER_ANSWER,
    MINIMUM_SCORE_DELTA_FOR_REPLACEMENT,
    OnlineQueueProposal,
    build_online_queue_proposal,
    validate_online_replacement_contract,
)
from smart_practice_policy import active_policy, normalize_governance
from tests.test_smart_practice_continuity_spacing_tranche_a import (
    SmartPracticeSpacingAppTests,
    _question,
)


def _q(question_id, utility, role="transfer", **state):
    qnum = sum((index + 1) * ord(char) for index, char in enumerate(question_id)) % 9000 + 1
    question = _question(question_id, qnum, role=role)
    question["smart_utility"] = float(utility)
    question["smart_primary_role"] = role
    question.update(state)
    return question


def _proposal(session, universe, eligible=None, current_index=0):
    return build_online_queue_proposal(
        session,
        universe,
        eligible_challenger_ids=set(eligible or []),
        current_index=current_index,
        policy_id="policy",
        policy_version="v1",
        policy_checksum="checksum",
        learner_revision=("revision", 1),
        builder_context_fingerprint="builder",
        evaluation_time_key="2026-09-21T16:00:00",
    )


class SmartPracticeOnlinePureTests(unittest.TestCase):
    def test_frozen_parameters(self):
        self.assertEqual(5.0, MINIMUM_SCORE_DELTA_FOR_REPLACEMENT)
        self.assertEqual(1, MAX_REPLACEMENTS_PER_ANSWER)

    def test_exact_five_point_delta_replaces(self):
        session = [_q("answered", 1, answered=True), _q("next", 2), _q("victim", 10)]
        challenger = _q("challenger", 15)
        proposal = _proposal(session, session + [challenger], {"challenger"})
        self.assertIsNotNone(proposal.replacement)
        self.assertEqual("victim", proposal.replacement.victim_id)
        self.assertEqual("challenger", proposal.replacement.challenger_id)
        self.assertEqual(5.0, proposal.replacement.score_delta)

    def test_below_five_point_delta_does_not_replace(self):
        session = [_q("answered", 1, answered=True), _q("next", 2), _q("victim", 10)]
        challenger = _q("challenger", 14.999)
        proposal = _proposal(session, session + [challenger], {"challenger"})
        self.assertIsNone(proposal.replacement)
        self.assertEqual(tuple(q["id"] for q in session), proposal.proposed_ids)

    def test_missing_challenger_utility_is_incomparable(self):
        session = [_q("answered", 1, answered=True), _q("next", 2), _q("victim", 10)]
        challenger = _q("challenger", 100)
        challenger.pop("smart_utility")
        proposal = _proposal(session, session + [challenger], {"challenger"})
        self.assertIsNone(proposal.replacement)
        self.assertEqual(tuple(q["id"] for q in session), proposal.proposed_ids)

    def test_nonfinite_utilities_fail_closed(self):
        session = [_q("answered", 1, answered=True), _q("next", 2), _q("victim", float("nan"))]
        challenger = _q("challenger", float("nan"))
        proposal = _proposal(session, session + [challenger], {"challenger"})
        self.assertIsNone(proposal.replacement)
        self.assertEqual(tuple(q["id"] for q in session), proposal.proposed_ids)

    def test_immediate_next_is_immutable(self):
        session = [_q("answered", 1, answered=True), _q("next", 1), _q("victim", 10)]
        challenger = _q("challenger", 50)
        proposal = _proposal(session, session + [challenger], {"challenger"})
        self.assertEqual("next", proposal.proposed_ids[1])

    def test_only_one_outside_replacement_per_answer(self):
        session = [
            _q("answered", 1, answered=True),
            _q("next", 2),
            _q("victim-a", 1),
            _q("victim-b", 2),
        ]
        challengers = [_q("challenger-a", 50), _q("challenger-b", 40)]
        proposal = _proposal(
            session,
            session + challengers,
            {"challenger-a", "challenger-b"},
        )
        outside = set(proposal.proposed_ids) - {q["id"] for q in session}
        self.assertEqual(1, len(outside))
        self.assertEqual("challenger-a", proposal.replacement.challenger_id)

    def test_main_thread_contract_rejects_multiple_outside_replacements(self):
        session = [
            _q("answered", 1, answered=True),
            _q("next", 2),
            _q("victim-a", 1),
            _q("victim-b", 2),
        ]
        challengers = [_q("challenger-a", 50), _q("challenger-b", 40)]
        malformed = OnlineQueueProposal(
            expected_ids=tuple(q["id"] for q in session),
            proposed_ids=("answered", "next", "challenger-a", "challenger-b"),
            replacement=None,
            protected_before={"weak_repair": 0, "due_retention": 0, "blueprint_coverage": 0},
            protected_after={"weak_repair": 0, "due_retention": 0, "blueprint_coverage": 0},
            policy_id="policy",
            policy_version="v1",
            policy_checksum="checksum",
            learner_revision=("revision", 1),
            builder_context_fingerprint="builder",
            evaluation_time_key="2026-09-21T16:00:00",
        )
        self.assertFalse(validate_online_replacement_contract(malformed, session + challengers))

    def test_protected_role_count_cannot_drop(self):
        session = [
            _q("answered", 1, answered=True),
            _q("next", 2),
            _q("protected", 1, role="weak_repair"),
        ]
        challenger = _q("challenger", 50, role="transfer")
        proposal = _proposal(session, session + [challenger], {"challenger"})
        self.assertIsNone(proposal.replacement)
        self.assertEqual(1, proposal.protected_after["weak_repair"])

    def test_same_protected_role_can_replace(self):
        session = [
            _q("answered", 1, answered=True),
            _q("next", 2),
            _q("protected", 1, role="weak_repair"),
        ]
        challenger = _q("challenger", 20, role="weak_repair")
        proposal = _proposal(session, session + [challenger], {"challenger"})
        self.assertEqual("challenger", proposal.proposed_ids[2])

    def test_ineligible_outside_candidate_cannot_replace(self):
        session = [_q("answered", 1, answered=True), _q("next", 2), _q("victim", 1)]
        ineligible = _q("recent", 100)
        eligible = _q("eligible", 5.999)
        proposal = _proposal(
            session,
            session + [ineligible, eligible],
            {"eligible"},
        )
        self.assertIsNone(proposal.replacement)
        self.assertNotIn("recent", proposal.proposed_ids)

    def test_existing_mutable_members_rerank_without_consuming_replacement(self):
        session = [
            _q("answered", 1, answered=True),
            _q("next", 2),
            _q("low", 3),
            _q("high", 30),
        ]
        proposal = _proposal(session, session, set())
        self.assertIsNone(proposal.replacement)
        self.assertEqual(("answered", "next", "high", "low"), proposal.proposed_ids)

    def test_repair_tagged_member_is_locked(self):
        session = [
            _q("answered", 1, answered=True),
            _q("next", 2),
            _q("repair", 1, session_tag="Confusion pair drill"),
            _q("mutable", 2),
        ]
        challenger = _q("challenger", 100)
        proposal = _proposal(session, session + [challenger], {"challenger"})
        self.assertEqual("repair", proposal.proposed_ids[2])

    def test_ties_are_deterministic_by_canonical_id(self):
        session = [
            _q("answered", 1, answered=True),
            _q("next", 2),
            _q("zeta", 10),
            _q("alpha", 10),
        ]
        first = _proposal(session, session, set())
        second = _proposal(session, session, set())
        self.assertEqual(first.proposed_ids, second.proposed_ids)
        self.assertEqual(("answered", "next", "alpha", "zeta"), first.proposed_ids)


class SmartPracticeOnlineAppTests(unittest.TestCase):
    def make_app(self):
        return SmartPracticeSpacingAppTests.make_app(self)

    def install(self, app, questions):
        SmartPracticeSpacingAppTests._install(self, app, questions, [])

    def _start_smart_session(self, app, questions):
        app.start_session_from_pool(
            questions,
            mode=MODE_SMART_PRACTICE,
            count="All visible",
            randomize=False,
            reset_clock=True,
            preserve_if_saved=False,
            builder_context=app.current_builder_context(
                mode=MODE_SMART_PRACTICE,
                count="All visible",
                randomize=False,
            ),
        )

    def _actual_policy_fields(self, app):
        governance = normalize_governance(
            app.progress_data.setdefault("meta", {}).get("smart_practice_policy_governance")
        )
        policy = active_policy(governance)
        return (
            str(policy.get("policy_id") or ""),
            str(policy.get("policy_version") or ""),
            str(policy.get("checksum") or ""),
        )

    def test_committed_smart_practice_answer_triggers_online_rescore(self):
        app = self.make_app()
        questions = [_question("q1", 1), _question("q2", 2), _question("q3", 3)]
        self.install(app, questions)
        app.start_session_from_pool(
            questions,
            mode=MODE_SMART_PRACTICE,
            count="All visible",
            randomize=False,
            reset_clock=True,
            preserve_if_saved=False,
            builder_context=app.current_builder_context(
                mode=MODE_SMART_PRACTICE,
                count="All visible",
                randomize=False,
            ),
        )
        with mock.patch.object(app, "schedule_smart_practice_online_replacement") as schedule:
            app._record_answer(
                app.questions[0],
                ["A"],
                feedback_override={"confidence": "Sure", "miss_reason": ""},
            )
        schedule.assert_called_once_with()

    def test_stale_transaction_token_rejects_without_mutating_queue(self):
        app = self.make_app()
        questions = [_question("q1", 1), _question("q2", 2), _question("q3", 3), _question("q4", 4)]
        self.install(app, questions)
        app.start_session_from_pool(
            questions,
            mode=MODE_SMART_PRACTICE,
            count="All visible",
            randomize=False,
            reset_clock=True,
            preserve_if_saved=False,
            builder_context=app.current_builder_context(
                mode=MODE_SMART_PRACTICE,
                count="All visible",
                randomize=False,
            ),
        )
        before = tuple(question["id"] for question in app.questions)
        app._smart_practice_online_generation = 1
        proposal = OnlineQueueProposal(
            expected_ids=before,
            proposed_ids=(before[0], before[1], before[3], before[2]),
            replacement=None,
            protected_before={"weak_repair": 0, "due_retention": 0, "blueprint_coverage": 0},
            protected_after={"weak_repair": 0, "due_retention": 0, "blueprint_coverage": 0},
            policy_id="unused",
            policy_version="unused",
            policy_checksum="unused",
            learner_revision=("unused",),
            builder_context_fingerprint="unused",
            evaluation_time_key="unused",
        )
        applied = app._apply_smart_practice_online_proposal(
            proposal,
            list(app.questions),
            token=("stale",),
            generation=1,
        )
        self.assertFalse(applied)
        self.assertEqual(before, tuple(question["id"] for question in app.questions))

    def test_mutated_queue_persists_current_membership_and_original_restore_lineage(self):
        app = self.make_app()
        questions = [
            _question("q1", 1),
            _question("q2", 2),
            _question("q3", 3),
            _question("q4", 4),
        ]
        self.install(app, questions)
        app.start_session_from_pool(
            questions[:3],
            mode=MODE_SMART_PRACTICE,
            count="All visible",
            randomize=False,
            reset_clock=True,
            preserve_if_saved=False,
            builder_context=app.current_builder_context(
                mode=MODE_SMART_PRACTICE,
                count="All visible",
                randomize=False,
            ),
        )
        original_restore_ids = tuple(app.session_restore_question_ids)
        replacement = app._clone_questions([questions[3]])[0]
        app._reset_runtime_question_state([replacement])
        app.questions[2] = replacement
        session_path = app.session_path
        app.save_session()
        payload = json.loads(session_path.read_text(encoding="utf-8"))
        self.assertEqual(["q1", "q2", "q4"], payload["question_ids"])
        self.assertEqual(list(original_restore_ids), payload["restore_question_ids"])

    def test_cand01r3_mode_never_starts_online_replacement_worker(self):
        app = self.make_app()
        app.active_session_mode = MODE_SMART_PRACTICE
        app.questions = [_question("q1", 1), _question("q2", 2), _question("q3", 3), _question("q4", 4)]
        with (
            mock.patch("app_session_builder_mixin.is_cand01r3_active", return_value=True),
            mock.patch("app_session_builder_mixin.threading.Thread") as worker_thread,
        ):
            app.schedule_smart_practice_online_replacement()
        worker_thread.assert_not_called()


if __name__ == "__main__":
    unittest.main()
