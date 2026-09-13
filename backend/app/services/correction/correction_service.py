"""Personalized STT Correction Memory Service."""
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any

from app.db.database import db
from app.schemas.correction import CorrectionConfirmRequest, CorrectionResponse, CorrectionListResponse

logger = logging.getLogger(__name__)


class CorrectionService:
    """Service managing persistent, user-specific, and context-aware STT corrections."""

    @classmethod
    def confirm_correction(cls, request: CorrectionConfirmRequest) -> CorrectionResponse:
        """Store or update a user-specific STT correction in the database."""
        user_id = request.user_id.strip()
        incorrect_clean = request.incorrect_text.strip()
        correct_clean = request.correct_text.strip()
        context_clean = request.context.strip() if request.context else None

        now = datetime.now(timezone.utc).isoformat()

        with db.get_connection() as conn:
            # Check for existing matching record for this user and incorrect phrase
            cur = conn.cursor()
            cur.execute(
                "SELECT id, occurrence_count, confidence, context_phrase, created_at FROM corrections "
                "WHERE user_id = ? AND LOWER(incorrect_text) = LOWER(?)",
                (user_id, incorrect_clean)
            )
            row = cur.fetchone()

            if row:
                rec_id = row["id"]
                new_count = row["occurrence_count"] + 1
                # Confidence must be monotonic non-decreasing: repeated confirmations of the same
                # correction are stronger evidence, never weaker. (Previously 0.6 + 0.1*count
                # produced 0.7 on the second confirm, LOWER than the 0.85 insert value.)
                new_conf = min(1.0, max(row["confidence"], 0.85) + 0.05)
                # Update existing record
                cur.execute(
                    """
                    UPDATE corrections
                    SET correct_text = ?, context_phrase = ?, occurrence_count = ?, confidence = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (correct_clean, context_clean or row["context_phrase"], new_count, new_conf, now, rec_id)
                )
                created_at = row["created_at"]
                logger.info(f"Updated correction for user '{user_id}': '{incorrect_clean}' -> '{correct_clean}' (Count: {new_count})")
            else:
                rec_id = str(uuid.uuid4())
                new_count = 1
                new_conf = 0.85
                created_at = now
                cur.execute(
                    """
                    INSERT INTO corrections (id, user_id, incorrect_text, correct_text, context_phrase, occurrence_count, confidence, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (rec_id, user_id, incorrect_clean, correct_clean, context_clean, new_count, new_conf, created_at, now)
                )
                logger.info(f"Created new correction for user '{user_id}': '{incorrect_clean}' -> '{correct_clean}' (Context: '{context_clean}')")

        return CorrectionResponse(
            id=rec_id,
            user_id=user_id,
            incorrect_text=incorrect_clean,
            correct_text=correct_clean,
            context_phrase=context_clean,
            occurrence_count=new_count,
            confidence=new_conf,
            created_at=created_at,
            updated_at=now,
        )

    @classmethod
    def get_user_corrections(cls, user_id: str) -> List[CorrectionResponse]:
        """Fetch all stored corrections for a specific user."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, user_id, incorrect_text, correct_text, context_phrase, occurrence_count, confidence, created_at, updated_at "
                "FROM corrections WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id.strip(),)
            )
            rows = cur.fetchall()

        return [
            CorrectionResponse(
                id=r["id"],
                user_id=r["user_id"],
                incorrect_text=r["incorrect_text"],
                correct_text=r["correct_text"],
                context_phrase=r["context_phrase"],
                occurrence_count=r["occurrence_count"],
                confidence=r["confidence"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    @classmethod
    def apply_corrections(
        cls,
        user_id: Optional[str],
        transcript: str,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Apply user-specific, context-aware corrections to an STT transcript.
        
        Guarantees:
        - Never modifies transcript if user_id is empty or no corrections exist.
        - Does NOT globally replace words outside their specified context.
        - Returns (corrected_transcript, list_of_applied_corrections).
        """
        if not user_id or not user_id.strip() or not transcript or not transcript.strip():
            return transcript, []

        corrections = cls.get_user_corrections(user_id)
        if not corrections:
            return transcript, []

        corrected_text = transcript
        applied = []

        for corr in corrections:
            target_incorrect = corr.incorrect_text.strip()
            target_correct = corr.correct_text.strip()
            context_phrase = corr.context_phrase.strip().lower() if corr.context_phrase else None

            # Word boundary pattern for incorrect text (case-insensitive)
            pattern = re.compile(rf"\b{re.escape(target_incorrect)}\b", re.IGNORECASE)

            # Check if incorrect word exists in the transcript
            matches = list(pattern.finditer(corrected_text))
            if not matches:
                continue

            for match in matches:
                should_replace = True

                # If context phrase is specified, check surrounding window (within ~40 chars)
                if context_phrase:
                    start_idx = max(0, match.start() - 40)
                    end_idx = min(len(corrected_text), match.end() + 40)
                    local_window = corrected_text[start_idx:end_idx].lower()

                    if context_phrase not in local_window:
                        # Context not matched -> skip replacement!
                        should_replace = False
                        logger.debug(
                            f"Skipping correction '{target_incorrect}' -> '{target_correct}' "
                            f"because context '{context_phrase}' was not found in window '{local_window}'."
                        )

                if should_replace:
                    # Replace with proper case matching
                    matched_str = match.group(0)
                    replacement = target_correct
                    if matched_str.isupper():
                        replacement = target_correct.upper()
                    elif matched_str[0].isupper():
                        replacement = target_correct.capitalize()

                    # Perform replacement for this occurrence
                    prefix = corrected_text[:match.start()]
                    suffix = corrected_text[match.end():]
                    corrected_text = prefix + replacement + suffix

                    applied.append({
                        "correction_id": corr.id,
                        "original": matched_str,
                        "replaced_with": replacement,
                        "context_matched": context_phrase is not None,
                    })
                    break  # Process one match per iteration to handle index shifts

        if applied:
            logger.info(f"Applied {len(applied)} personalized correction(s) for user '{user_id}': '{transcript}' -> '{corrected_text}'")

        return corrected_text, applied
