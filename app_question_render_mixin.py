import time
import tkinter as tk

from app_constants import MODE_EXAM
from cand01r3_runtime import get_context, is_cand01r3_active, revalidate_training_question
from progress_store import is_super_confident_active, recovery_ladder_stage, study_status_name
from render_cache import ChoiceRenderSnapshot, QuestionRenderSnapshot
from source_trust import derive_source_trust_warning
from ui_theme import BLUE, DARK, RED


class QuestionRenderMixin:
    def _question_topics_text(self, q):
        topics = ", ".join(str(t).strip() for t in q.get("topics", []) if str(t).strip())
        return f"   Topic: {topics}" if topics else ""

    def _question_header_text(self, q):
        return f"Q{q.get('question_number')}   Page {q.get('source_page','')}   Domain: {q.get('domain','')}{self._question_topics_text(q)}"

    def _question_meta_text(self, q, trust_warning=None):
        study_status = study_status_name(self._progress_record(q, create=False))
        question_type_text = "Multi-select" if q.get("question_type") == "multi" else "Single answer"
        meta_text = f"Status: {study_status}   |   {self.current_source_badge_text()}   |   {question_type_text}"
        if trust_warning:
            meta_text += f"   |   {trust_warning['text']}"
        return meta_text

    def _render_empty_question_state(self):
        self.topbar_title.configure(text="Microsoft SC-900 Test Learning Engine")
        self.question_meta_label.configure(text="Ready to start a set")
        self.meta_strip_label.configure(text="")
        self.issue_label.pack_forget()
        self.clear_answer_toast()
        self.review_panel.pack_forget()
        self.status_label.pack_forget()
        self.confidence_wrap.pack_forget()
        self.answer_meta_label.pack_forget()
        self.question_label.configure(
            text="Choose your session options on the left, then click START SET or FULL BANK to begin."
        )
        for row in self.choice_rows.values():
            row.pack_forget()
        self.flag_btn.configure(text="FLAG")
        self.suspend_btn.configure(text="SUSPEND")
        self.report_issue_btn.configure(text="REPORT ISSUE", state="disabled")
        self.redo_btn.configure(state="disabled")
        self.submit_btn_visible = False
        self.action_hint.configure(text="No active set yet.")
        self.action_hint.pack(fill="x", pady=(4, 0))
        self.explanation_wrap.pack_forget()
        self._update_progress()
        self._layout_action_buttons()
        self.prev_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")
        self.finish_btn.configure(state="disabled")
        self.question_count.configure(text="QUESTION 0 of 0   |   No active set. Build a session to begin.")
        self.score_label.configure(text="")
        self.session_label.configure(text="Session file: not started")
        self.set_sidebar_visible(True)
        self._apply_compact_review_visibility()

    def _source_trust_warning_for_question(self, q):
        payload = getattr(self, "smart_practice_signal_cache_payload", None) or {}
        if not payload:
            return None
        return derive_source_trust_warning(
            q,
            payload.get("source_map") or {},
            payload.get("source_trust_map") or {},
        )

    def _render_question_header(self, q, trust_warning=None):
        self.topbar_title.configure(text=f"Microsoft SC-900 Test Learning Engine - {self.active_session_mode}")
        self.question_meta_label.configure(text=self._question_header_text(q))
        meta_text = self._question_meta_text(q, trust_warning)
        if trust_warning:
            self.meta_strip_label.configure(
                text=meta_text,
                bg=trust_warning["background"],
                fg=trust_warning["foreground"],
            )
        else:
            self.meta_strip_label.configure(text=meta_text, bg="#f7f9fc", fg=DARK)
        self.question_label.configure(text=q.get("prompt", ""))
        issues = self.question_issue_notes(q)
        if issues:
            self.issue_label.configure(text="Issue notes:\n- " + "\n- ".join(issues))
            self.issue_label.pack(fill="x", pady=(8, 10))
        else:
            self.issue_label.pack_forget()
        self._render_answer_toast()
        return self._progress_record(q, create=False)

    def _general_explanation_for_question(self, q, show_exam_feedback):
        if not q.get("answered") or not show_exam_feedback:
            return ""
        return str(q.get("general_explanation", "")).strip() or "No explanation is available for this question yet."

    def _choice_feedback_is_legacy_blanket_duplicate(self, q):
        choices = q.get("choices")
        feedback = q.get("choice_explanations")
        general = str(q.get("general_explanation", "") or "").strip()
        if not isinstance(choices, dict) or not isinstance(feedback, dict) or not feedback:
            return False
        if set(feedback) != set(choices):
            return False
        return bool(general) and all(str(value or "").strip() == general for value in feedback.values())

    def _selected_wrong_feedback_for_letter(self, q, letter, show_exam_feedback):
        if not q.get("answered") or not show_exam_feedback:
            return ""
        selected = set(q.get("selected", []))
        correct = set(q.get("correct", []))
        if letter not in selected or letter in correct:
            return ""
        feedback = q.get("choice_explanations")
        if not isinstance(feedback, dict) or self._choice_feedback_is_legacy_blanket_duplicate(q):
            return ""
        return str(feedback.get(letter, "") or "").strip()

    def _inline_explanation_for_question(self, q, show_exam_feedback):
        for letter in q.get("selected", []):
            text = self._selected_wrong_feedback_for_letter(q, letter, show_exam_feedback)
            if text:
                return letter, text
        return None, ""

    def _general_explanation_visible(self, q, show_exam_feedback):
        if not self._general_explanation_for_question(q, show_exam_feedback):
            return False
        recall_var = getattr(self, "explanation_recall_var", None)
        recall_enabled = bool(recall_var is not None and recall_var.get())
        return not (recall_enabled and self._question_correct(q) and not q.get("recall_ready", False))

    def _build_question_render_snapshot(self, q, show_exam_feedback, ladder_stage, trust_warning):
        header_text = self._question_header_text(q)
        meta_text = self._question_meta_text(q, trust_warning)
        selected = set(q.get("selected", []))
        pending = set(q.get("pending", []))
        correct = set(q.get("correct", []))
        general_explanation = self._general_explanation_for_question(q, show_exam_feedback)
        choice_snapshots = []
        for letter in sorted(q.get("choices", {})):
            state = "default"
            if q.get("answered"):
                if show_exam_feedback:
                    if letter in selected and letter in correct:
                        state = "correct"
                    elif letter in selected:
                        state = "wrong"
                    elif letter in correct:
                        state = "correct"
                elif letter in selected:
                    state = "pending"
            elif letter in pending:
                state = "pending"
            detail = self._selected_wrong_feedback_for_letter(q, letter, show_exam_feedback)
            choice_snapshots.append(
                ChoiceRenderSnapshot(
                    letter=letter,
                    text=str(q.get("choices", {}).get(letter) or ""),
                    state=state,
                    detail=detail,
                    detail_emphasis=bool(detail),
                )
            )
        width = max(0, int(self.content_canvas.winfo_width() or 0))
        snapshot = QuestionRenderSnapshot(
            question_number=int(q.get("question_number") or 0),
            header_text=header_text,
            meta_text=meta_text,
            meta_background=trust_warning["background"] if trust_warning else "#f7f9fc",
            meta_foreground=trust_warning["foreground"] if trust_warning else DARK,
            prompt=str(q.get("prompt") or ""),
            issue_notes=tuple(self.question_issue_notes(q)),
            choices=tuple(choice_snapshots),
            answered=bool(q.get("answered")),
            correct=bool(self._question_correct(q)),
            flagged=bool(q.get("flagged")),
            suspended=bool(q.get("suspended")),
            show_exam_feedback=bool(show_exam_feedback),
            dense=bool(self.dense_answers_var.get()),
            width=width,
            confidence=str(q.get("last_confidence") or ""),
            miss_reason=str(q.get("last_miss_reason") or ""),
            session_tag=str(q.get("session_tag") or ""),
            ladder_stage=str(ladder_stage or ""),
            general_explanation=general_explanation,
            general_explanation_visible=self._general_explanation_visible(q, show_exam_feedback),
        )
        cache_key = (snapshot.question_number, snapshot)
        return self.render_cache.get(cache_key) or self.render_cache.put(cache_key, snapshot)

    def _question_answer_meta(self, q, ladder_stage):
        answer_meta = []
        if q.get("session_tag"):
            answer_meta.append(f"Assist: {q.get('session_tag')}")
        if ladder_stage and ladder_stage not in ("New", "Suspended"):
            answer_meta.append(f"Stage: {ladder_stage}")
        if q.get("answered") and not self._question_correct(q) and q.get("last_miss_reason"):
            answer_meta.append(f"Pattern: {q.get('last_miss_reason')}")
        volatility = self.question_volatility(q)
        if volatility.get("label"):
            answer_meta.append(f"Volatility: {volatility['label']}")
        if q.get("suspended"):
            answer_meta.append(
                "This question is suspended and excluded from future study sets and readiness analytics."
            )
        return answer_meta

    def _render_choice_rows(self, q, show_exam_feedback):
        pending = set(q.get("pending", []))
        selected = set(q.get("selected", []))
        correct = set(q.get("correct", []))
        dense_answers = bool(self.dense_answers_var.get())
        row_pady = 2 if dense_answers else 4
        for letter, row in self.choice_rows.items():
            if q["choices"].get(letter):
                row.set_text(q["choices"][letter])
                row.set_density(dense_answers)
                row.reset()
                row.pack(fill="x", pady=row_pady)
                if q.get("answered"):
                    row.set_interactive(False)
                    if show_exam_feedback:
                        if letter in selected and letter in correct:
                            row.mark_selected_correct()
                        elif letter in selected and letter not in correct:
                            row.mark_selected_wrong()
                        elif letter in correct:
                            row.mark_correct_unselected()
                        selected_wrong_feedback = self._selected_wrong_feedback_for_letter(
                            q, letter, show_exam_feedback
                        )
                        if selected_wrong_feedback:
                            row.set_detail(
                                selected_wrong_feedback,
                                bg=row.inner.cget("bg"),
                                fg=DARK,
                                expanded=True,
                                show_toggle=False,
                                emphasis=True,
                            )
                    elif letter in selected:
                        row.mark_pending(multi=q.get("question_type") == "multi")
                else:
                    row.set_interactive(True)
                    if letter in pending:
                        row.mark_pending(multi=q.get("question_type") == "multi")
            else:
                row.pack_forget()

    def _render_general_explanation_block(self, q, show_exam_feedback):
        general_text = self._general_explanation_for_question(q, show_exam_feedback)
        if not general_text:
            self.recall_prompt_wrap.pack_forget()
            self.general_card.pack_forget()
            self.explanation_wrap.pack_forget()
            return
        self.general_card.configure(text=general_text)
        self.explanation_wrap.pack(fill="x", pady=(10, 0))
        if self._general_explanation_visible(q, show_exam_feedback):
            self.recall_prompt_wrap.pack_forget()
            self.general_card.pack(fill="x", pady=(0, 10))
        else:
            self.general_card.pack_forget()
            self.recall_prompt_wrap.pack(fill="x", pady=(0, 8))

    def _render_question_actions(self, q):
        self.flag_btn.configure(text="UNFLAG" if q.get("flagged") else "FLAG")
        self.suspend_btn.configure(text="UNSUSPEND" if q.get("suspended") else "SUSPEND")
        report_open = self.question_has_open_issue_report(q)
        self.report_issue_btn.configure(
            text=("REPORTED" if report_open else "REPORT ISSUE"), state=("disabled" if report_open else "normal")
        )
        self.redo_btn.configure(
            state=(
                "normal"
                if q.get("answered") and (self.active_session_mode != MODE_EXAM or self.exam_reveal)
                else "disabled"
            )
        )
        self.submit_btn_visible = bool(q.get("question_type") == "multi" and not q.get("answered"))
        if self.submit_btn_visible:
            self.action_hint.configure(text="Select all that apply, then Submit.")
            self.action_hint.pack(fill="x", pady=(4, 0))
        else:
            self.action_hint.configure(text="")
            self.action_hint.pack_forget()
        self._layout_action_buttons()

    def _render_review_panel(self, q, show_exam_feedback, answer_meta):
        if q.get("answered"):
            self.review_panel.pack(fill="x", pady=(10, 0))
            self.answer_meta_label.pack_forget()
            if not show_exam_feedback:
                self.status_label.configure(text="Answer recorded", bg="#eef4fb", fg=BLUE)
            elif self._question_correct(q):
                combo = self._current_combo_stats() if self.gamification_enabled() else {"correct": 0}
                streak = int(combo.get("correct") or 0)
                parts = ["Correct"]
                if streak >= 2:
                    parts.append(f"streak x{streak}")
                if q.get("last_confidence") == "Sure":
                    parts.append("confident")
                self.status_label.configure(text=" | ".join(parts), bg="#eaf7ef", fg="#17643a")
            else:
                self.status_label.configure(text="Review this one", bg="#fff0f0", fg=RED)
            self.status_label.pack(fill="x", pady=(0, 8))
            if self._confidence_review_controls_visible(show_exam_feedback=show_exam_feedback):
                current_conf = str(q.get("last_confidence") or "")
                palette = {
                    "Sure": ("#e7f7ee", "#1d6e3d"),
                    "Unsure": ("#fff6df", "#8c6116"),
                    "Guessed": ("#eef5fb", "#0b4b88"),
                    "Unknown": ("#f7f9fc", BLUE),
                }
                for option, btn in self.confidence_buttons.items():
                    bg, fg = palette.get(option, ("#f7f9fc", BLUE))
                    active = option == current_conf
                    btn.configure(
                        bg=(bg if active else "#f7f9fc"),
                        fg=(fg if active else BLUE),
                        relief="solid",
                        bd=(2 if active else 1),
                    )
                super_active = is_super_confident_active(self._progress_record(q, create=False))
                can_super = bool(self._question_correct(q))
                self.super_confident_btn.configure(
                    state=("normal" if can_super else "disabled"),
                    bg=("#dff6e8" if super_active and can_super else "#f7f9fc"),
                    fg=("#17643a" if can_super else "#8aa0b7"),
                    bd=(2 if super_active and can_super else 1),
                    text=("Super confident on" if super_active and can_super else "Super confident"),
                )
                self.confidence_wrap.pack(fill="x")
            else:
                self.confidence_wrap.pack_forget()
        else:
            self.review_panel.pack_forget()
            self.status_label.pack_forget()
            self.confidence_wrap.pack_forget()
            self.answer_meta_label.pack_forget()

    def render_question(self):
        if not self.questions:
            self._render_empty_question_state()
            if self.scroll_to_top_on_render:
                self.content_canvas.yview_moveto(0.0)
                self.scroll_to_top_on_render = False
            return
        q = self.current_question()
        if is_cand01r3_active():
            decision = revalidate_training_question(q, action="RENDER")
            intended = get_context().intended_use
            if intended == "TRAINING" and decision.role != "TRAIN":
                self._render_empty_question_state()
                return
            if intended == "MEASUREMENT" and decision.role != "PROBE":
                self._render_empty_question_state()
                return
        if not q.get("answered"):
            qnum = q.get("question_number")
            if self.active_question_started_qnum != qnum:
                self.active_question_started_qnum = qnum
                self.active_question_started_at = time.time()
        rec = self._progress_record(q, create=False)
        ladder_stage = recovery_ladder_stage(rec)
        show_exam_feedback = not (self.active_session_mode == MODE_EXAM and not self.exam_reveal)
        trust_warning = self._source_trust_warning_for_question(q)
        snapshot = self._build_question_render_snapshot(q, show_exam_feedback, ladder_stage, trust_warning)
        if snapshot != self.last_render_snapshot:
            self._render_question_header(q, trust_warning)
            answer_meta = self._question_answer_meta(q, ladder_stage)
            self._render_choice_rows(q, show_exam_feedback)
            self._render_question_actions(q)
            self._render_review_panel(q, show_exam_feedback, answer_meta)
            self._render_general_explanation_block(q, show_exam_feedback)
            self.last_render_snapshot = snapshot
        self._update_progress()
        self._apply_compact_review_visibility(q)
        if getattr(self, "question_list_dirty", True):
            self.refresh_question_list()
        else:
            self._sync_question_list_selection()
        self.prev_btn.configure(state="normal" if self.index > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.index < len(self.questions) - 1 else "disabled")
        all_answered = self._all_session_questions_resolved_for_finish()
        if self.active_session_mode == MODE_EXAM:
            self.finish_btn.configure(text="FINISH EXAM", state="normal")
        else:
            self.finish_btn.configure(text="FINISH SET", state="normal" if all_answered else "disabled")
        current_pos = None
        for pos, idx in enumerate(self.visible_indices):
            if idx == self.index:
                current_pos = pos
                break
        if current_pos is not None:
            self.question_list.selection_clear(0, tk.END)
            self.question_list.selection_set(current_pos)
            self.question_list.see(current_pos)
        self.refresh_analytics_window()
        if self.scroll_to_top_on_render:
            self.content_canvas.yview_moveto(0.0)
            self.scroll_to_top_on_render = False
