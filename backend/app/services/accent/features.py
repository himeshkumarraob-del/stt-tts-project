"""Acoustic and prosodic feature extraction service for accent analysis."""
import logging
from typing import Dict, Any, Tuple, List, Optional
import numpy as np
import soundfile as sf
from app.schemas.accent import AcousticFeatures

logger = logging.getLogger(__name__)


def hz_to_mel(hz: float | np.ndarray) -> float | np.ndarray:
    """Convert frequency in Hertz to Mel scale."""
    return 2595.0 * np.log10(1.0 + hz / 700.0)


def mel_to_hz(mel: float | np.ndarray) -> float | np.ndarray:
    """Convert Mel scale value back to Hertz."""
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def create_mel_filterbank(sr: int, n_fft: int, n_mels: int = 26, fmin: float = 0.0, fmax: Optional[float] = None) -> np.ndarray:
    """Generate triangular Mel-scale filterbank matrix."""
    if fmax is None:
        fmax = sr / 2.0
    
    mel_min = hz_to_mel(fmin)
    mel_max = hz_to_mel(fmax)
    mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_points = mel_to_hz(mel_points)
    bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)
    
    n_freq_bins = n_fft // 2 + 1
    filterbank = np.zeros((n_mels, n_freq_bins), dtype=np.float64)
    
    for m in range(1, n_mels + 1):
        f_left = bin_points[m - 1]
        f_center = bin_points[m]
        f_right = bin_points[m + 1]
        
        if f_center > f_left:
            for k in range(f_left, f_center):
                filterbank[m - 1, k] = (k - f_left) / (f_center - f_left)
        if f_right > f_center:
            for k in range(f_center, f_right):
                filterbank[m - 1, k] = (f_right - k) / (f_right - f_center)
                
    return filterbank


def dct_matrix(n_mels: int = 26, n_mfcc: int = 13) -> np.ndarray:
    """Compute Discrete Cosine Transform (DCT-II) orthonormal matrix."""
    basis = np.empty((n_mfcc, n_mels), dtype=np.float64)
    basis[0, :] = 1.0 / np.sqrt(n_mels)
    samples = np.arange(1, 2 * n_mels, 2) * np.pi / (2.0 * n_mels)
    for i in range(1, n_mfcc):
        basis[i, :] = np.cos(i * samples) * np.sqrt(2.0 / n_mels)
    return basis


class AcousticFeatureExtractor:
    """Extracts acoustic, spectral, prosodic, and cepstral features from speech audio."""

    def __init__(self, n_fft: int = 1024, hop_length: int = 512, n_mels: int = 26, n_mfcc: int = 13):
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels
        self.n_mfcc = n_mfcc

    def extract_from_file(self, audio_path: str) -> Tuple[AcousticFeatures, Dict[str, Any]]:
        """Load audio file and extract all acoustic and prosodic features."""
        try:
            data, sr = sf.read(audio_path)
        except Exception as e:
            logger.error(f"Failed to read audio file for feature extraction: {e}")
            raise ValueError(f"Could not read audio file: {e}")

        if data is None or len(data) == 0:
            raise ValueError("Audio data is empty or unreadable")

        if data.ndim > 1:
            data = np.mean(data, axis=1)

        if len(data) == 0:
            raise ValueError("Audio channel data is empty")

        # Standardize amplitude to [-1.0, 1.0]
        max_val = np.max(np.abs(data)) if len(data) > 0 else 0.0
        if max_val > 0:
            data = data / max_val

        return self.extract_from_signal(data, sr)

    def extract_from_signal(self, y: np.ndarray, sr: int) -> Tuple[AcousticFeatures, Dict[str, Any]]:
        """Extract acoustic features from audio signal array."""
        duration = float(len(y)) / float(sr)
        if duration < 0.1 or len(y) < self.n_fft:
            raise ValueError("Audio duration too short for acoustic feature extraction")

        # Frame blocking
        num_frames = max(1, 1 + (len(y) - self.n_fft) // self.hop_length)
        frames = np.lib.stride_tricks.as_strided(
            y,
            shape=(num_frames, self.n_fft),
            strides=(y.strides[0] * self.hop_length, y.strides[0])
        ).copy()

        # Windowing and STFT
        window = np.hanning(self.n_fft)
        windowed_frames = frames * window
        stft = np.fft.rfft(windowed_frames, axis=1)
        mag_spec = np.abs(stft).T  # Shape: (freq_bins, num_frames)
        power_spec = (mag_spec ** 2) / float(self.n_fft)
        freq_bins = np.fft.rfftfreq(self.n_fft, d=1.0 / sr)

        # 1. MFCC Extraction
        filterbank = create_mel_filterbank(sr, self.n_fft, self.n_mels)
        mel_energies = np.dot(filterbank, power_spec)
        log_mel_energies = np.log(np.maximum(mel_energies, 1e-9))
        dct_mat = dct_matrix(self.n_mels, self.n_mfcc)
        mfccs = np.dot(dct_mat, log_mel_energies)  # Shape: (13, num_frames)
        
        mfcc_mean = [float(val) for val in np.mean(mfccs, axis=1)]
        mfcc_std = [float(val) for val in np.std(mfccs, axis=1)]

        # 2. Spectral Centroid
        mag_sum = np.maximum(np.sum(mag_spec, axis=0), 1e-9)
        spectral_centroids = np.sum(freq_bins[:, np.newaxis] * mag_spec, axis=0) / mag_sum
        spectral_centroid_mean = float(np.mean(spectral_centroids))

        # 3. Spectral Rolloff (85%)
        cum_power = np.cumsum(power_spec, axis=0)
        total_power = cum_power[-1, :]
        rolloff_threshold = 0.85 * total_power
        rolloff_bins = np.argmax(cum_power >= rolloff_threshold[np.newaxis, :], axis=0)
        spectral_rolloff = freq_bins[rolloff_bins]
        spectral_rolloff_mean = float(np.mean(spectral_rolloff))

        # 4. Spectral Flatness (Geometric Mean / Arithmetic Mean)
        # Add epsilon to prevent log(0)
        eps = 1e-12
        geom_mean = np.exp(np.mean(np.log(power_spec + eps), axis=0))
        arith_mean = np.maximum(np.mean(power_spec, axis=0), eps)
        spectral_flatness = geom_mean / arith_mean
        spectral_flatness_mean = float(np.mean(spectral_flatness))

        # 5. Zero Crossing Rate
        zero_crossings = np.sum(np.abs(np.diff(np.sign(frames), axis=1)) > 0, axis=1) / (2.0 * self.n_fft)
        zcr_mean = float(np.mean(zero_crossings))

        # 6. RMS Energy & Pause Ratio
        frame_rms = np.sqrt(np.mean(frames ** 2, axis=1))
        energy_rms_mean = float(np.mean(frame_rms))
        energy_rms_std = float(np.std(frame_rms))

        # Silence/pause detection: frames below 10% of maximum RMS
        silence_threshold = 0.10 * np.maximum(np.max(frame_rms), 1e-6)
        silent_frames = np.sum(frame_rms < silence_threshold)
        pause_duration_ratio = float(silent_frames / len(frame_rms)) if len(frame_rms) > 0 else 0.0

        # 7. Fundamental Frequency (F0) / Pitch Tracking via Autocorrelation
        f0_values = self._track_f0(y, sr)
        if len(f0_values) > 0:
            f0_mean = float(np.mean(f0_values))
            f0_std = float(np.std(f0_values))
            f0_p95 = float(np.percentile(f0_values, 95))
            f0_p05 = float(np.percentile(f0_values, 5))
            f0_range = float(f0_p95 - f0_p05)
        else:
            f0_mean = 0.0
            f0_std = 0.0
            f0_range = 0.0

        # 8. Speech Rate & Articulation Rate (Syllable Nuclei Estimation)
        syllable_count = self._estimate_syllables(frame_rms, silence_threshold)
        speech_rate = float(syllable_count / duration) if duration > 0 else 0.0
        active_duration = duration * (1.0 - pause_duration_ratio)
        articulation_rate = float(syllable_count / active_duration) if active_duration > 0.1 else speech_rate

        features = AcousticFeatures(
            pitch_f0_mean_hz=round(f0_mean, 2),
            pitch_f0_std_hz=round(f0_std, 2),
            pitch_f0_range_hz=round(f0_range, 2),
            speech_rate_syllables_per_sec=round(speech_rate, 2),
            articulation_rate=round(articulation_rate, 2),
            pause_duration_ratio=round(pause_duration_ratio, 3),
            spectral_centroid_mean=round(spectral_centroid_mean, 2),
            spectral_rolloff_mean=round(spectral_rolloff_mean, 2),
            spectral_flatness_mean=round(spectral_flatness_mean, 4),
            zero_crossing_rate_mean=round(zcr_mean, 4),
            energy_rms_mean=round(energy_rms_mean, 4),
            energy_rms_std=round(energy_rms_std, 4),
            mfcc_mean=[round(v, 4) for v in mfcc_mean],
            mfcc_std=[round(v, 4) for v in mfcc_std],
        )

        metadata = {
            "duration_seconds": round(duration, 3),
            "sample_rate": sr,
            "num_frames": int(num_frames),
            "voiced_frames": len(f0_values),
            "estimated_syllables": syllable_count,
        }

        return features, metadata

    def _track_f0(self, y: np.ndarray, sr: int, fmin: float = 65.0, fmax: float = 400.0) -> List[float]:
        """Track pitch (F0) using normalized autocorrelation on short frames."""
        frame_len = int(sr * 0.035)  # 35ms frame
        hop_len = int(sr * 0.010)    # 10ms hop
        min_lag = int(sr / fmax)
        max_lag = int(sr / fmin)

        if len(y) < frame_len or max_lag >= frame_len:
            return []

        f0_list = []
        for start in range(0, len(y) - frame_len, hop_len):
            frame = y[start : start + frame_len]
            # Center frame
            frame = frame - np.mean(frame)
            norm = np.sum(frame ** 2)
            if norm < 1e-6:
                continue

            # Normalized autocorrelation
            corr = np.correlate(frame, frame, mode="full")
            corr = corr[len(frame) - 1 :]
            corr = corr / norm

            # Search within lag bounds
            search_window = corr[min_lag:max_lag]
            if len(search_window) == 0:
                continue

            peak_idx = np.argmax(search_window)
            peak_val = search_window[peak_idx]

            # Voiced frame threshold
            if peak_val > 0.35:
                lag = min_lag + peak_idx
                f0 = float(sr) / float(lag)
                if fmin <= f0 <= fmax:
                    f0_list.append(f0)

        return f0_list

    def _estimate_syllables(self, frame_rms: np.ndarray, threshold: float) -> int:
        """Estimate syllable count using energy peak prominence in the speech signal."""
        if len(frame_rms) < 3:
            return 1

        # Smooth RMS envelope
        kernel_size = 5
        kernel = np.ones(kernel_size) / kernel_size
        smooth_rms = np.convolve(frame_rms, kernel, mode="same")

        # Find local peaks above threshold
        peaks = 0
        min_peak_distance = 6  # Minimum frames between syllable nuclei (~70ms)
        last_peak = -min_peak_distance

        for i in range(1, len(smooth_rms) - 1):
            if smooth_rms[i] > smooth_rms[i - 1] and smooth_rms[i] > smooth_rms[i + 1]:
                if smooth_rms[i] > threshold and (i - last_peak) >= min_peak_distance:
                    peaks += 1
                    last_peak = i

        return max(1, peaks)
