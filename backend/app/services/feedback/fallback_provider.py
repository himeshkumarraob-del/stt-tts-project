"""Deterministic, rule-based fallback feedback provider."""
import logging
from typing import List
from app.schemas.feedback import (
    FeedbackGenerationRequest,
    FeedbackResponse,
    PracticeExercise,
    ScoresSummary,
)
from app.services.feedback.base import BaseFeedbackProvider

logger = logging.getLogger(__name__)


class DeterministicFallbackProvider(BaseFeedbackProvider):
    """
    Deterministic fallback feedback generator.
    Produces structured, high-quality personalized feedback purely from verified assessment data
    without requiring an active external LLM connection.
    """

    @property
    def provider_name(self) -> str:
        return "deterministic_fallback"

    @property
    def model_name(self) -> str:
        return "rule_based_v1"

    async def generate_feedback(self, request: FeedbackGenerationRequest) -> FeedbackResponse:
        """Generate rule-based feedback directly from assessment metrics."""
        pron = request.pronunciation_result
        accent = request.accent_result
        stt = request.stt_result

        overall_score = pron.overall_score
        words_total = len(pron.words)
        correct_words = [w for w in pron.words if w.status.value in ["correct", "acceptable_variant"]]
        # NOTE: Insertion pairs carry `target=None`; they are extra spoken words, not mispronounced
        # target words. Including them here previously produced None entries that crashed downstream
        # joins (e.g. ", ".join(target_list)) with an unhandled TypeError -> HTTP 500.
        mispronounced_words = [
            w for w in pron.words
            if w.status.value in ["incorrect", "mispronounced"] or (w.score < 60.0 and w.target is not None)
        ]
        omitted_words = [w for w in pron.words if w.status.value in ["omitted", "omission"]]
        substituted_words = [w for w in pron.words if w.status.value in ["substituted", "substitution"]]

        # 1. Overall Summary
        if overall_score >= 85.0:
            summary = (
                f"Excellent delivery! Your overall pronunciation score is {overall_score:.1f}/100. "
                "Your spoken words demonstrated high acoustic clarity and intelligibility throughout the passage."
            )
        elif overall_score >= 65.0:
            summary = (
                f"Good effort! Your overall pronunciation score is {overall_score:.1f}/100. "
                "Most words were clear and intelligible, with a few specific target sounds that can benefit from focused practice."
            )
        else:
            summary = (
                f"Keep going! Your pronunciation score is {overall_score:.1f}/100. "
                "With targeted practice on word pacing and key phonemes, your clarity will improve significantly."
            )

        # 2. Pronunciation Feedback
        pron_feedback_parts = []
        if mispronounced_words:
            targets = ", ".join([f"'{w.target}'" for w in mispronounced_words[:4]])
            pron_feedback_parts.append(f"Focus on clarifying the phonetic sounds in {targets}.")
        if omitted_words:
            om_targets = ", ".join([f"'{w.target}'" for w in omitted_words[:3]])
            pron_feedback_parts.append(f"Ensure you do not drop words such as {om_targets} during continuous speech.")
        if substituted_words:
            sub_targets = ", ".join([f"'{w.spoken}' for '{w.target}'" for w in substituted_words[:3]])
            pron_feedback_parts.append(f"Watch out for word substitutions: {sub_targets}.")
        if not pron_feedback_parts:
            pron_feedback_parts.append("Your pronunciation aligned closely with the target prompt with zero critical word-level errors.")

        pronunciation_feedback = " ".join(pron_feedback_parts)

        # 3. Accent Feedback
        if accent.model_status.value == "not_calibrated":
            accent_feedback = (
                f"Acoustic analysis shows an articulation rate of {accent.features.articulation_rate:.1f} syllables/sec "
                f"with a mean fundamental pitch of {accent.features.pitch_f0_mean_hz:.1f} Hz. "
                "Note: Accent classification is in development status ('not_calibrated') and regional labels are not assigned."
            )
        else:
            accent_feedback = (
                f"Speech exhibited acoustic characteristics consistent with {accent.accent.value} "
                f"(confidence: {accent.confidence:.2f})."
            )

        # 4. Strengths
        strengths: List[str] = []
        if len(correct_words) > 0:
            strengths.append(f"Correctly and clearly enunciated {len(correct_words)} out of {words_total} target words.")
        if pron.confidence >= 0.80:
            strengths.append("High acoustic confidence and distinct voice clarity.")
        if 2.5 <= accent.features.speech_rate_syllables_per_sec <= 4.5:
            strengths.append("Natural, well-controlled overall speaking rate.")
        if not strengths:
            strengths.append("Steady vocal projection and attempt to complete the full sentence prompt.")

        # 5. Areas to Improve
        areas: List[str] = []
        for w in (mispronounced_words + substituted_words + omitted_words)[:3]:
            areas.append(f"Practice the pronunciation and clarity of '{w.target}'.")
        if accent.features.pause_duration_ratio > 0.40:
            areas.append("Reduce extended pause intervals between phrases to improve natural speech flow.")
        elif accent.features.articulation_rate > 5.5:
            areas.append("Pace yourself slightly slower to give each vowel and consonant sufficient duration.")
        if not areas:
            areas.append("Continue practicing varied text passages to maintain natural prosody and intonation.")

        # 6. Practice Recommendations
        recommendations = [
            "Read aloud at a steady, deliberate tempo while recording yourself.",
            "Break multi-syllable challenging words into individual syllables before speaking full sentences.",
        ]
        if omitted_words or substituted_words:
            recommendations.append("Follow the text prompt closely with your eyes to avoid skipping connecting words.")

        # 7. Suggested Exercises
        exercises: List[PracticeExercise] = []
        if mispronounced_words:
            target_list = [w.target for w in mispronounced_words[:3] if w.target]
            if target_list:
                exercises.append(
                    PracticeExercise(
                        title="Target Word Focus Drill",
                        exercise_type="repetition",
                        target_words=target_list,
                        instructions="Repeat each word slowly 3 times, emphasizing clear vowel length and ending consonants.",
                        sample_sentence=f"Focus on speaking clearly: {', '.join(target_list)}.",
                    )
                )

        if accent.features.articulation_rate > 5.0 or accent.features.pause_duration_ratio > 0.35:
            exercises.append(
                PracticeExercise(
                    title="Rhythm and Phrasing Practice",
                    exercise_type="pacing",
                    target_words=[],
                    instructions="Speak the target sentence using metronome pacing, pausing only at natural comma or clause boundaries.",
                    sample_sentence=pron.target_text,
                )
            )
        else:
            exercises.append(
                PracticeExercise(
                    title="Sentence Intonation and Flow",
                    exercise_type="intonation",
                    target_words=[],
                    instructions="Read the sentence with expressive pitch contour, raising pitch slightly before commas and lowering at periods.",
                    sample_sentence=pron.target_text,
                )
            )

        scores_summary = ScoresSummary(
            overall_pronunciation_score=round(pron.overall_score, 1),
            pronunciation_confidence=round(pron.confidence, 3),
            accent_label=accent.accent.value,
            accent_model_status=accent.model_status.value,
            accent_confidence=round(accent.confidence, 3),
            words_total=words_total,
            words_correct=len(correct_words),
            issues_detected_count=len(pron.issues),
        )

        return FeedbackResponse(
            overall_summary=summary,
            pronunciation_feedback=pronunciation_feedback,
            accent_feedback=accent_feedback,
            strengths=strengths,
            areas_to_improve=areas,
            practice_recommendations=recommendations,
            suggested_exercises=exercises,
            scores_summary=scores_summary,
            is_fallback=True,
            provider=self.provider_name,
            model=self.model_name,
        )
