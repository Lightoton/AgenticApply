from typing import TypedDict, Optional
from agents.evaluator_agent import EvaluationResult

class AgenticApplyState(TypedDict):
    """
    Represents the state of our LangGraph workflow.
    This data is passed between nodes.
    """
    url: str
    job_description: str
    master_cv: str
    evaluation: Optional[EvaluationResult]
    tailored_cv_path: Optional[str]
    cover_letter: Optional[str]
    cover_letter_pdf_path: Optional[str]
    company_name: str
    human_approved: Optional[bool]
