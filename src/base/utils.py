import re

from src.base.models import MinimalSource


class RagUtils:
    """Provide utility methods shared across the RAG project."""
    @staticmethod
    def split_words(text: str, max_length: int) -> list[str]:
        """
        Split text into visual lines without exceeding a maximum line length.
        Existing line breaks and empty lines are preserved.
        """
        if max_length <= 0:
            raise ValueError("max_length must be greater than zero")
        result: list[str] = []

        def split_line(line: str) -> list[str]:
            """
            Split a single line into visual segments no longer than max_length.
            Words longer than the maximum length are split
            into multiple segments.
            """
            if not line.strip():
                return [""]
            segments: list[str] = []
            current: list[str] = []
            current_length = 0
            for word in line.split():
                while len(word) > max_length:
                    if current:
                        segments.append(" ".join(current))
                        current = []
                        current_length = 0
                    segments.append(word[:max_length])
                    word = word[max_length:]
                new_length = current_length + len(word)
                if current:
                    new_length += 1
                if new_length > max_length:
                    segments.append(" ".join(current))
                    current = [word]
                    current_length = len(word)
                else:
                    current.append(word)
                    current_length = new_length
            if current:
                segments.append(" ".join(current))
            return segments
        original_lines = re.split(r"\r\n|\r|\n", text)
        for line in original_lines:
            result.extend(split_line(line))
        return result

    @staticmethod
    def calculate_overlap(r: MinimalSource, g: MinimalSource) -> float:
        """
        Calculate the overlap ratio between two source fragments.
        The returned ratio is relative to the ground-truth fragment length.
        """
        if r.file_path != g.file_path:
            return 0.0
        start_overlap = max(r.first_character_index, g.first_character_index)
        end_overlap = min(r.last_character_index, g.last_character_index)
        intersection = max(0, end_overlap - start_overlap)
        ref_length = max(1, g.last_character_index - g.first_character_index)
        return intersection / ref_length
