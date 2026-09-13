"""API endpoint for the complete End-to-End Voice Learning Pipeline."""
import time
import json
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, status, HTTPException

from app.schemas.voice_learning import VoiceLearningProcessResponse, PipelineTimings
from app.schemas.feedback import FeedbackGenerationRequest
from app.services.audio_validator import AudioValidatorService
from app.services.stt import STTService
from app.services.correction import CorrectionService
from app.services.pronunciation import PronunciationService
from app.services.accent import AccentService
from app.services.feedback import FeedbackService
from app.services.tts import TTSService
from app.db.database import db
from app.core.logging import logger

router = APIRouter()


@router.post(
    "/process",
    response_model=VoiceLearningProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process Complete Voice Learning Loop",
    description="Orchestrates the complete end-to-end voice learning workflow: "
                "Audio Validation (Phase 1) -> STT (Phase 2) -> Personalized Correction Memory (Phase 6) -> "
                "Pronunciation Assessment (Phase 3) -> Accent Analysis (Phase 4) -> AI Feedback (Phase 5) -> "
                "TTS Synthesis (Phase 6) -> Persistent Storage.",
    tags=["Voice Learning Loop"]
)
async def process_voice_learning_loop(
    target_text: str = Form(..., description="Target sentence the user was prompted to speak"),
    file: UploadFile = File(..., description="Audio recording of user speech"),
    user_id: Optional[str] = Form(None, description="Optional user ID for personalized correction memory and session tracking"),
    synthesize_tts: bool = Form(True, description="Whether to synthesize speech feedback via TTS"),
) -> VoiceLearningProcessResponse:
    """Execute the full end-to-end voice learning loop."""
    t_start_total = time.perf_counter()

    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": True, "message": "No audio file uploaded or filename is missing."}
        )

    if not target_text or not target_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": True, "message": "Target text cannot be empty."}
        )

    cleaned_target = target_text.strip()
    attempt_id = str(uuid.uuid4())
    filename = file.filename
    content_type = file.content_type

    try:
        audio_bytes = await file.read()
    finally:
        await file.close()

    # --- 1. Audio Validation (Phase 1) ---
    t0 = time.perf_counter()
    validation_res = AudioValidatorService.validate_audio(
        file_bytes=audio_bytes,
        filename=filename,
        content_type=content_type,
    )
    t_val = round(time.perf_counter() - t0, 4)

    # --- 2. Speech-to-Text (Phase 2) ---
    t0 = time.perf_counter()
    stt_res = STTService.transcribe_audio(
        audio_bytes=audio_bytes,
        filename=filename,
        content_type=content_type,
    )
    original_transcript = stt_res.text
    t_stt = round(time.perf_counter() - t0, 4)

    # --- 3. Personalized STT Correction Memory (Phase 6) ---
    t0 = time.perf_counter()
    corrected_transcript, applied_corrections = CorrectionService.apply_corrections(
        user_id=user_id,
        transcript=original_transcript,
    )
    t_corr = round(time.perf_counter() - t0, 4)

    # --- 4. Pronunciation Assessment (Phase 3) ---
    t0 = time.perf_counter()
    pron_res = PronunciationService.assess_pronunciation(
        target_text=cleaned_target,
        audio_bytes=audio_bytes,
        filename=filename,
        content_type=content_type,
    )
    t_pron = round(time.perf_counter() - t0, 4)

    # --- 5. Accent Analysis (Phase 4) ---
    t0 = time.perf_counter()
    accent_res = AccentService.analyze_accent(
        audio_bytes=audio_bytes,
        filename=filename,
        content_type=content_type,
    )
    t_accent = round(time.perf_counter() - t0, 4)

    # --- 6. AI Feedback & Personalized Drills (Phase 5) ---
    t0 = time.perf_counter()
    feedback_req = FeedbackGenerationRequest(
        stt_result=stt_res,
        pronunciation_result=pron_res,
        accent_result=accent_res,
        user_id=user_id,
        session_id=attempt_id,
    )
    feedback_res = await FeedbackService.generate_feedback(feedback_req)
    t_fb = round(time.perf_counter() - t0, 4)

    # --- 7. Text-to-Speech (Phase 6) ---
    t_tts = 0.0
    tts_res = None
    if synthesize_tts and feedback_res.overall_summary:
        t0 = time.perf_counter()
        try:
            _, tts_res = await TTSService.synthesize(
                text=feedback_res.overall_summary,
            )
        except Exception as e:
            logger.warning(f"TTS synthesis non-fatal failure in voice learning loop: {e}")
            tts_res = None
        t_tts = round(time.perf_counter() - t0, 4)

    # Total Pipeline Latency
    t_total = round(time.perf_counter() - t_start_total, 4)

    timings = PipelineTimings(
        audio_validation_seconds=t_val,
        stt_seconds=t_stt,
        correction_seconds=t_corr,
        pronunciation_seconds=t_pron,
        accent_seconds=t_accent,
        feedback_seconds=t_fb,
        tts_seconds=t_tts,
        total_pipeline_seconds=t_total,
    )

    # --- 8. Persistence to Database ---
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            # Speech Attempt
            cur.execute(
                """
                INSERT INTO speech_attempts (id, session_id, user_id, target_text, original_transcript, corrected_transcript, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    attempt_id,
                    user_id,
                    cleaned_target,
                    original_transcript,
                    corrected_transcript,
                    validation_res.metadata.duration_seconds,
                )
            )
            # Pronunciation Result
            cur.execute(
                """
                INSERT INTO pronunciation_results (id, attempt_id, overall_score, confidence, words_json, issues_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    attempt_id,
                    pron_res.overall_score,
                    pron_res.confidence,
                    json.dumps([w.model_dump() for w in pron_res.words]),
                    json.dumps([i.model_dump() for i in pron_res.issues]),
                )
            )
            # Accent Result
            cur.execute(
                """
                INSERT INTO accent_results (id, attempt_id, accent_label, confidence, model_status, features_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    attempt_id,
                    accent_res.accent.value,
                    accent_res.confidence,
                    accent_res.model_status.value,
                    json.dumps(accent_res.features.model_dump()),
                )
            )
            # Feedback Record
            cur.execute(
                """
                INSERT INTO feedback_records (id, attempt_id, summary, pronunciation_feedback, accent_feedback, strengths_json, areas_json, exercises_json, provider, is_fallback)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    attempt_id,
                    feedback_res.overall_summary,
                    feedback_res.pronunciation_feedback,
                    feedback_res.accent_feedback,
                    json.dumps(feedback_res.strengths),
                    json.dumps(feedback_res.areas_to_improve),
                    json.dumps([ex.model_dump() for ex in feedback_res.suggested_exercises]),
                    feedback_res.provider,
                    1 if feedback_res.is_fallback else 0,
                )
            )
    except Exception as e:
        logger.warning(f"Database persistence non-fatal warning: {e}")

    logger.info(
        f"Voice Learning Loop completed for '{filename}': "
        f"Attempt={attempt_id}, PronScore={pron_res.overall_score}/100, "
        f"Original='{original_transcript}', Corrected='{corrected_transcript}', TotalTime={t_total}s"
    )

    return VoiceLearningProcessResponse(
        attempt_id=attempt_id,
        user_id=user_id,
        original_transcript=original_transcript,
        corrected_transcript=corrected_transcript,
        applied_corrections=applied_corrections,
        pronunciation_result=pron_res,
        accent_result=accent_res,
        feedback_result=feedback_res,
        tts_result=tts_res,
        timings=timings,
    )
