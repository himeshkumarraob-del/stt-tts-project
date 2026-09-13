from typing import List, Tuple, Optional
from app.services.pronunciation.phonetics import clean_token


class DynamicTimeWarpingAligner:
    """
    Sequence alignment engine utilizing dynamic programming (Needleman-Wunsch / Levenshtein alignment)
    to align target sentence words with spoken word tokens and timestamps.
    """

    @classmethod
    def align_words(
        cls,
        target_tokens: List[str],
        spoken_tokens: List[dict]  # list of {'word': str, 'start': float, 'end': float, 'probability': float}
    ) -> List[dict]:
        """
        Performs global alignment between target words and spoken words.
        Returns aligned word items with operation labels: MATCH, SUBSTITUTION, OMISSION, INSERTION.
        """
        n = len(target_tokens)
        m = len(spoken_tokens)

        # Distance matrix initialization
        dp = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(n + 1):
            dp[i][0] = i * 1.0  # Deletion/omission cost
        for j in range(m + 1):
            dp[0][j] = j * 1.0  # Insertion cost

        # Fill DP table
        for i in range(1, n + 1):
            t_word = clean_token(target_tokens[i - 1])
            for j in range(1, m + 1):
                s_word = clean_token(spoken_tokens[j - 1]["word"])

                if t_word == s_word:
                    cost = 0.0
                else:
                    # Partial similarity cost based on Levenshtein distance on sub-characters
                    cost = 1.0

                dp[i][j] = min(
                    dp[i - 1][j - 1] + cost,  # Match / Substitution
                    dp[i - 1][j] + 1.0,        # Omission (Target word skipped)
                    dp[i][j - 1] + 1.0         # Insertion (Extra spoken word)
                )

        # Backtrack to obtain aligned pairs
        i, j = n, m
        aligned_pairs = []

        while i > 0 or j > 0:
            if i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + (0.0 if clean_token(target_tokens[i - 1]) == clean_token(spoken_tokens[j - 1]["word"]) else 1.0):
                t_word = target_tokens[i - 1]
                s_obj = spoken_tokens[j - 1]
                is_match = (clean_token(t_word) == clean_token(s_obj["word"]))
                aligned_pairs.append({
                    "type": "MATCH" if is_match else "SUBSTITUTION",
                    "target": t_word,
                    "spoken": s_obj["word"],
                    "start": s_obj["start"],
                    "end": s_obj["end"],
                    "acoustic_prob": s_obj.get("probability", 0.9),
                })
                i -= 1
                j -= 1
            elif i > 0 and dp[i][j] == dp[i - 1][j] + 1.0:
                # Target word was omitted by user
                aligned_pairs.append({
                    "type": "OMISSION",
                    "target": target_tokens[i - 1],
                    "spoken": None,
                    "start": None,
                    "end": None,
                    "acoustic_prob": 0.0,
                })
                i -= 1
            else:
                # Spoken word was an extra insertion
                s_obj = spoken_tokens[j - 1]
                aligned_pairs.append({
                    "type": "INSERTION",
                    "target": None,
                    "spoken": s_obj["word"],
                    "start": s_obj["start"],
                    "end": s_obj["end"],
                    "acoustic_prob": s_obj.get("probability", 0.9),
                })
                j -= 1

        aligned_pairs.reverse()
        return aligned_pairs
