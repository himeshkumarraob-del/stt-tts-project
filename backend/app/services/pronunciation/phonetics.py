import re
from typing import List, Dict, Optional

# Basic CMU-based phoneme dictionary mapping for common English words
# Extended with common Indian-English phonological patterns
PHONEME_LEXICON: Dict[str, List[str]] = {
    "hello": ["HH", "AH", "L", "OW"],
    "world": ["W", "ER", "L", "D"],
    "this": ["DH", "IH", "S"],
    "is": ["IH", "Z"],
    "a": ["AH"],
    "test": ["T", "EH", "S", "T"],
    "audio": ["AA", "D", "IY", "OW"],
    "recording": ["R", "IH", "K", "AO", "R", "D", "IH", "NG"],
    "and": ["AE", "N", "D"],
    "so": ["S", "OW"],
    "my": ["M", "AY"],
    "fellow": ["F", "EH", "L", "OW"],
    "americans": ["AH", "M", "EH", "R", "AH", "K", "AH", "N", "Z"],
    "ask": ["AE", "S", "K"],
    "not": ["N", "AA", "T"],
    "what": ["W", "AH", "T"],
    "your": ["Y", "AO", "R"],
    "country": ["K", "AH", "N", "T", "R", "IY"],
    "can": ["K", "AE", "N"],
    "do": ["D", "UW"],
    "for": ["F", "AO", "R"],
    "you": ["Y", "UW"],
    "the": ["DH", "AH"],
    "quick": ["K", "W", "IH", "K"],
    "brown": ["B", "R", "AW", "N"],
    "fox": ["F", "AA", "K", "S"],
    "jumps": ["JH", "AH", "M", "P", "S"],
    "over": ["OW", "V", "ER"],
    "lazy": ["L", "EY", "Z", "IY"],
    "dog": ["D", "AO", "G"],
    "good": ["G", "UH", "D"],
    "morning": ["M", "AO", "R", "N", "IH", "NG"],
    "evening": ["IY", "V", "N", "IH", "NG"],
    "speech": ["S", "P", "IY", "CH"],
    "voice": ["V", "OY", "S"],
    "learning": ["L", "ER", "N", "IH", "NG"],
    "pronunciation": ["P", "R", "OW", "N", "AH", "N", "S", "IY", "EY", "SH", "AH", "N"],
    "assessment": ["AH", "S", "EH", "S", "M", "AH", "N", "T"],
    "system": ["S", "IH", "S", "T", "AH", "M"],
    "india": ["IH", "N", "D", "IY", "AH"],
    "english": ["IH", "NG", "G", "L", "IH", "SH"],
    "accent": ["AE", "K", "S", "EH", "N", "T"],
}

# Standard Indian-English phonological variants (e.g. /v/ and /w/ mergers, /dh/ and /d/, /th/ and /t/)
INDIAN_ENGLISH_PHONEME_EQUIVALENCES = {
    ("V", "W"): "Acceptable liquid/approximant variation common in Indian-English",
    ("W", "V"): "Acceptable liquid/approximant variation common in Indian-English",
    ("DH", "D"): "Dental plosive substitution common in Indian-English",
    ("TH", "T"): "Dental plosive substitution common in Indian-English",
    ("Z", "S"): "Voicing variation common in Indian-English",
    ("ZH", "J"): "Postalveolar fricative variation common in Indian-English",
}


def clean_token(token: str) -> str:
    """Normalize word token by lowercasing and removing punctuation."""
    return re.sub(r"[^\w\s]", "", token.strip().lower())


def tokenize_sentence(sentence: str) -> List[str]:
    """Tokenize a sentence into clean lowercase words."""
    cleaned = re.sub(r"[^\w\s]", " ", sentence.lower())
    return [w for w in cleaned.split() if w]


def get_word_phonemes(word: str) -> List[str]:
    """
    Retrieve phoneme breakdown for a given word from dictionary or generate rule-based grapheme-to-phoneme fallback.
    """
    clean_w = clean_token(word)
    if clean_w in PHONEME_LEXICON:
        return PHONEME_LEXICON[clean_w]
    
    # Rule-based fallback grapheme-to-phoneme mapping for OOV words
    phonemes = []
    i = 0
    while i < len(clean_w):
        ch = clean_w[i]
        # Digraphs
        if i + 1 < len(clean_w):
            digraph = clean_w[i:i+2]
            if digraph == "th":
                phonemes.append("TH")
                i += 2
                continue
            elif digraph == "sh":
                phonemes.append("SH")
                i += 2
                continue
            elif digraph == "ch":
                phonemes.append("CH")
                i += 2
                continue
            elif digraph == "ph":
                phonemes.append("F")
                i += 2
                continue
            elif digraph == "ea" or digraph == "ee":
                phonemes.append("IY")
                i += 2
                continue
            elif digraph == "oo":
                phonemes.append("UW")
                i += 2
                continue
        
        # Single chars
        char_map = {
            "a": "AE", "b": "B", "c": "K", "d": "D", "e": "EH", "f": "F",
            "g": "G", "h": "HH", "i": "IH", "j": "JH", "k": "K", "l": "L",
            "m": "M", "n": "N", "o": "AA", "p": "P", "q": "K", "r": "R",
            "s": "S", "t": "T", "u": "AH", "v": "V", "w": "W", "x": "K",
            "y": "Y", "z": "Z"
        }
        phonemes.append(char_map.get(ch, "AH"))
        i += 1
        
    return phonemes if phonemes else ["AH"]
