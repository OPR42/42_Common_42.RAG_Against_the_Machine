import uuid
from typing import Sequence

from pydantic import BaseModel, Field


class MinimalSource(BaseModel):
    """Identify a text fragment within a source file."""
    file_path: str
    first_character_index: int
    last_character_index: int


class UnansweredQuestion(BaseModel):
    """Represent a dataset question awaiting an answer."""
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str


class AnsweredQuestion(UnansweredQuestion):
    """Represent a dataset question with its answer and reference sources."""
    sources: list[MinimalSource]
    answer: str


class RagDataset(BaseModel):
    """Store answered and unanswered questions from a RAG dataset."""
    rag_questions: list[AnsweredQuestion | UnansweredQuestion]


class MinimalSearchResults(BaseModel):
    """Store the sources retrieved for a single question."""
    question_id: str
    question: str
    retrieved_sources: list[MinimalSource]


class MinimalAnswer(MinimalSearchResults):
    """Store retrieved sources and the generated answer for one question."""
    answer: str


class StudentSearchResults(BaseModel):
    """Store retrieval results produced for a collection of questions."""
    search_results: Sequence[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(StudentSearchResults):
    """Store retrieval results and generated answers for multiple questions."""
    search_results: Sequence[MinimalAnswer]


class EvaluateResult(BaseModel):
    """Store dataset validation information and retrieval recall metrics."""
    student_valid: bool
    total_questions: int
    questions_with_sources: int
    questions_with_student_sources: int
    k: int
    recall1: float | None
    recall3: float | None
    recall5: float | None
    recallk: float | None


class LogEvent(BaseModel):
    """
    Carry structured information from processing code
    to the user interface.
    """
    source: str = ""
    type: str = ""
    message: str = ""
    duration: float = 0.0
    text_var: str = ""
    message_end: str = ""
    value: float = 0.0
    left_box: str = ""
    right_box: str = ""
    int_a: int = 0
    int_b: int = 0
    int_c: int = 0
    float_a: float = 0.0
    float_b: float = 0.0
    float_c: float = 0.0
    fields: list[str] = Field(default_factory=list)


class ColorTheme(BaseModel):
    """Define the terminal colors used by the user interface."""
    frame: str = ""
    main_background: str = ""
    labels: str = ""
    dim_labels: str = ""
    inv_labels: str = ""
    text: str = ""
    ita_text: str = ""
    inv_text: str = ""
    dim_text: str = ""
    highlight_text: str = ""
    alt_text: str = ""
    alt_inv_text: str = ""
    dim_alt_text: str = ""
    highlight_alt_text: str = ""
    log_background: str = ""
    button: str = ""
    disabled_button: str = ""
    scroll_bar: str = ""
    log_item: str = ""
