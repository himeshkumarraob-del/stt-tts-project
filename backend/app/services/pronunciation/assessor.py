import io
import time
from typing import List, Dict, Any, Optional
from app.services.pronunciation.base import BasePronunciationAssessor
from app.services.pronunciation.phonetics import (
    clean_token,
    tokenize_sentence,
    get_word_phonemes,
    INDIAN_ENGLISH_PHONEME_EQUIVALENCES,
)
from app.services.pronunciation.aligner import DynamicTimeWarpingAligner
from app.schemas.pronunciation import (
    PronunciationAssessmentResponse,
    WordAssessment,
    PhonemeAssessment,
    PronunciationIssue,
    WordStatus,
)
from app.core.config import settings
from app.core.errors import PronunciationModelError
from app.core.logging import logger


class AcousticPronunciationAssessor(BasePronunciationAssessor):
    """
    Pronunciation Assessment engine combining acoustic feature posterior probabilities,
    word-level time alignment, and phonological distance metrics.
    
    METHODOLOGY & TRANSPARENCY NOTICE:
    1. Word-level scores are derived directly from the speech model's acoustic posterior probabilities
       and sequence alignment operations.
    2. Phoneme assessments are G2P lexicon projections where the word-level acoustic confidence is
       mapped across constituent phonemes (`is_derived=True`). They are NOT independent forced alignment boundaries.
    3. The overall score is an engineering composite metric (0-100), not a human-expert validated rating.
    """

    def __init__(self, model_size: Optional[str] = None):
        self._model_size = model_size or settings.STT_MODEL
        self._model = None

    @property
    def model_name(self) -> str:
        return f"acoustic-whisper-aligner:{self._model_size}"

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                logger.info(f"Initializing acoustic alignment model '{self._model_size}'...")
                self._model = WhisperModel(
                    self._model_size,
                    device=settings.STT_DEVICE,
                    compute_type=settings.STT_COMPUTE_TYPE,
                )
            except Exception as e:
                logger.error(f"Failed to load acoustic pronunciation model: {str(e)}", exc_info=True)
                raise PronunciationModelError(f"Acoustic pronunciation model initialization failed: {str(e)}")
        return self._model

    def assess(
        self,
        target_text: str,
        audio_bytes: bytes,
        audio_duration_seconds: float,
        filename: Optional[str] = None,
    ) -> PronunciationAssessmentResponse:
        start_time = time.perf_counter()
        logger.info(f"Running pronunciation assessment against target: '{target_text}'")

        model = self._get_model()

        try:
            audio_stream = io.BytesIO(audio_bytes)
            # Run model with word-level acoustic timestamps enabled
            segments_gen, info = model.transcribe(
                audio_stream,
                word_timestamps=True,
                beam_size=settings.STT_BEAM_SIZE,
                language="en",
                vad_filter=True,
            )

            spoken_tokens = []
            transcript_pieces = []

            for seg in segments_gen:
                if seg.text.strip():
                    transcript_pieces.append(seg.text.strip())
                for w in getattr(seg, "words", []):
                    clean_w = clean_token(w.word)
                    if clean_w:
                        spoken_tokens.append({
                            "word": w.word.strip(),
                            "start": round(w.start, 3),
                            "end": round(w.end, 3),
                            "probability": round(w.probability, 4),
                        })

            transcript = " ".join(transcript_pieces).strip()
            target_tokens = tokenize_sentence(target_text)

            # Align target words with spoken acoustic tokens
            aligned_pairs = DynamicTimeWarpingAligner.align_words(target_tokens, spoken_tokens)

            word_assessments: List[WordAssessment] = []
            all_phonemes: List[PhonemeAssessment] = []
            issues: List[PronunciationIssue] = []

            total_target_words = max(len(target_tokens), 1)
            word_scores: List[float] = []

            for idx, pair in enumerate(aligned_pairs):
                pair_type = pair["type"]
                target_word = pair["target"]
                spoken_word = pair["spoken"]
                prob = pair.get("acoustic_prob", 0.9)
                start_t = pair.get("start")
                end_t = pair.get("end")

                target_phonemes = get_word_phonemes(target_word) if target_word else []
                word_phoneme_assessments: List[PhonemeAssessment] = []

                if pair_type == "MATCH":
                    # Acoustic probability translated to 0-100 score
                    # High probability (e.g. >0.90) yields 90-100 score
                    base_acoustic_score = min(100.0, max(0.0, prob * 100.0))
                    
                    # Map word acoustic confidence to constituent phonemes
                    for p in target_phonemes:
                        p_score = round(base_acoustic_score, 1)
                        p_ass = PhonemeAssessment(
                            phoneme=p,
                            score=p_score,
                            status="correct" if p_score >= 70.0 else "distorted",
                            start=start_t,
                            end=end_t,
                            is_derived=True,
                        )
                        word_phoneme_assessments.append(p_ass)
                        all_phonemes.append(p_ass)

                    word_score = round(base_acoustic_score, 1)
                    word_scores.append(word_score)

                    word_assessments.append(
                        WordAssessment(
                            target=target_word,
                            spoken=spoken_word,
                            score=word_score,
                            status=WordStatus.CORRECT,
                            start=start_t,
                            end=end_t,
                            acoustic_confidence=prob,
                            phonemes=word_phoneme_assessments,
                            notes=None,
                        )
                    )

                elif pair_type == "SUBSTITUTION":
                    # Check if substitution represents an acceptable Indian-English accent variation
                    is_accent_variant = False
                    variant_note = None

                    spoken_phonemes = get_word_phonemes(spoken_word) if spoken_word else []
                    
                    # Check phonetic equivalence matrix for acceptable accent variations
                    if settings.PRONUNCIATION_ACCEPT_INDIAN_ENGLISH_VARIANTS and target_phonemes and spoken_phonemes:
                        for (p1, p2), desc in INDIAN_ENGLISH_PHONEME_EQUIVALENCES.items():
                            if p1 in target_phonemes and p2 in spoken_phonemes:
                                is_accent_variant = True
                                variant_note = desc
                                break

                    if is_accent_variant:
                        word_score = round(min(85.0, prob * 85.0), 1)
                        status = WordStatus.ACCEPTABLE_VARIANT
                    else:
                        word_score = round(min(40.0, prob * 40.0), 1)
                        status = WordStatus.SUBSTITUTION
                        issues.append(
                            PronunciationIssue(
                                index=idx,
                                word=target_word or spoken_word,
                                issue_type="substitution",
                                description=f"Expected '{target_word}' but heard '{spoken_word}'",
                                severity="medium" if word_score > 20 else "high",
                            )
                        )

                    for p in (target_phonemes or spoken_phonemes):
                        p_ass = PhonemeAssessment(
                            phoneme=p,
                            score=word_score,
                            status="acceptable_variant" if is_accent_variant else "substituted",
                            start=start_t,
                            end=end_t,
                            is_derived=True,
                        )
                        word_phoneme_assessments.append(p_ass)
                        all_phonemes.append(p_ass)

                    word_scores.append(word_score)
                    word_assessments.append(
                        WordAssessment(
                            target=target_word,
                            spoken=spoken_word,
                            score=word_score,
                            status=status,
                            start=start_t,
                            end=end_t,
                            acoustic_confidence=prob,
                            phonemes=word_phoneme_assessments,
                            notes=variant_note,
                        )
                    )

                elif pair_type == "OMISSION":
                    # Word in target sentence was skipped by user
                    word_score = 0.0
                    word_scores.append(word_score)
                    issues.append(
                        PronunciationIssue(
                            index=idx,
                            word=target_word,
                            issue_type="omission",
                            description=f"Target word '{target_word}' was omitted from speech",
                            severity="high",
                        )
                    )
                    for p in target_phonemes:
                        p_ass = PhonemeAssessment(
                            phoneme=p,
                            score=0.0,
                            status="omitted",
                            start=None,
                            end=None,
                            is_derived=True,
                        )
                        word_phoneme_assessments.append(p_ass)
                        all_phonemes.append(p_ass)

                    word_assessments.append(
                        WordAssessment(
                            target=target_word,
                            spoken=None,
                            score=0.0,
                            status=WordStatus.OMISSION,
                            start=None,
                            end=None,
                            acoustic_confidence=0.0,
                            phonemes=word_phoneme_assessments,
                            notes="Omitted word",
                        )
                    )

                elif pair_type == "INSERTION":
                    # Extra word spoken not in target
                    issues.append(
                        PronunciationIssue(
                            index=idx,
                            word=spoken_word,
                            issue_type="insertion",
                            description=f"Extra word '{spoken_word}' inserted into utterance",
                            severity="low",
                        )
                    )
                    word_assessments.append(
                        WordAssessment(
                            target=None,
                            spoken=spoken_word,
                            score=0.0,
                            status=WordStatus.INSERTION,
                            start=start_t,
                            end=end_t,
                            acoustic_confidence=prob,
                            phonemes=[],
                            notes="Inserted word",
                        )
                    )

            # Compute overall composite score (0 - 100)
            if word_scores:
                raw_score = sum(word_scores) / float(len(word_scores))
                overall_score = round(max(0.0, min(100.0, raw_score)), 1)
            else:
                overall_score = 0.0

            # Mean acoustic confidence across non-zero recognized words
            probs = [w.acoustic_confidence for w in word_assessments if w.acoustic_confidence > 0]
            mean_conf = sum(probs) / len(probs) if probs else 0.5
            overall_confidence = round(max(0.1, min(1.0, mean_conf)), 3)

            processing_time = round(time.perf_counter() - start_time, 4)

            return PronunciationAssessmentResponse(
                target_text=target_text,
                transcript=transcript,
                overall_score=overall_score,
                confidence=overall_confidence,
                duration_seconds=round(audio_duration_seconds, 3),
                processing_time_seconds=processing_time,
                words=word_assessments,
                phonemes=all_phonemes,
                issues=issues,
                metadata={
                    "model": self.model_name,
                    "target_token_count": len(target_tokens),
                    "spoken_token_count": len(spoken_tokens),
                    "scoring_engine": "acoustic_alignment_dtw",
                    "phoneme_methodology": "word_posterior_mapped_to_lexicon_phonemes",
                    "filename": filename,
                }
            )
        except Exception as e:
            logger.error(f"Pronunciation assessment execution failed: {str(e)}", exc_info=True)
            raise PronunciationModelError(f"Pronunciation assessment failed: {str(e)}")
