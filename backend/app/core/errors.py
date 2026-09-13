from typing import Any, Optional


class AppBaseException(Exception):
    def __init__(self, message: str, status_code: int = 400, details: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


# Audio Validation Errors
class AudioValidationError(AppBaseException):
    def __init__(self, message: str, status_code: int = 400, details: Optional[Any] = None):
        super().__init__(message=message, status_code=status_code, details=details)


class AudioFormatNotSupportedError(AudioValidationError):
    def __init__(self, message: str = "Unsupported audio format", details: Optional[Any] = None):
        super().__init__(message=message, status_code=415, details=details)


class AudioFileSizeExceededError(AudioValidationError):
    def __init__(self, message: str = "Audio file size exceeds allowed limit", details: Optional[Any] = None):
        super().__init__(message=message, status_code=413, details=details)


class AudioCorruptError(AudioValidationError):
    def __init__(self, message: str = "Audio file is corrupt or unreadable", details: Optional[Any] = None):
        super().__init__(message=message, status_code=400, details=details)


class AudioMimeTypeMismatchError(AudioValidationError):
    def __init__(self, message: str = "Audio MIME type or extension does not match actual audio header/content", details: Optional[Any] = None):
        super().__init__(message=message, status_code=400, details=details)


# STT (Speech-to-Text) Errors
class STTBaseError(AppBaseException):
    def __init__(self, message: str, status_code: int = 500, details: Optional[Any] = None):
        super().__init__(message=message, status_code=status_code, details=details)


class STTConfigurationError(STTBaseError):
    def __init__(self, message: str = "Invalid STT provider or model configuration", details: Optional[Any] = None):
        super().__init__(message=message, status_code=500, details=details)


class STTModelLoadError(STTBaseError):
    def __init__(self, message: str = "Failed to load STT model", details: Optional[Any] = None):
        super().__init__(message=message, status_code=500, details=details)


class STTTranscriptionError(STTBaseError):
    def __init__(self, message: str = "Audio transcription failed", details: Optional[Any] = None):
        super().__init__(message=message, status_code=500, details=details)


# Pronunciation Assessment Errors
class PronunciationBaseError(AppBaseException):
    def __init__(self, message: str, status_code: int = 400, details: Optional[Any] = None):
        super().__init__(message=message, status_code=status_code, details=details)


class TargetTextValidationError(PronunciationBaseError):
    def __init__(self, message: str = "Invalid target text provided for pronunciation assessment", details: Optional[Any] = None):
        super().__init__(message=message, status_code=400, details=details)


class AlignmentError(PronunciationBaseError):
    def __init__(self, message: str = "Failed to align spoken utterance with target text", details: Optional[Any] = None):
        super().__init__(message=message, status_code=422, details=details)


class PronunciationModelError(PronunciationBaseError):
    def __init__(self, message: str = "Pronunciation assessment model failure", details: Optional[Any] = None):
        super().__init__(message=message, status_code=500, details=details)
