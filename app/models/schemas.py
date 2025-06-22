from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import ConfigDict

class MotionType(str, Enum):
    MOTION_TO_DISMISS = "Motion to Dismiss"
    SUMMARY_JUDGMENT = "Motion for Summary Judgment"
    MOTION_IN_LIMINE = "Motion in Limine"
    MOTION_TO_COMPEL = "Motion to Compel"
    PROTECTIVE_ORDER = "Motion for Protective Order"
    EXCLUDE_EXPERT = "Motion to Exclude Expert"
    SANCTIONS = "Motion for Sanctions"

class ArgumentCategory(str, Enum):
    NEGLIGENCE_DUTY = "negligence_duty"
    NEGLIGENCE_BREACH = "negligence_breach"
    NEGLIGENCE_CAUSATION = "negligence_causation"
    NEGLIGENCE_DAMAGES = "negligence_damages"
    LIABILITY_ISSUES = "liability_issues"
    CAUSATION_DISPUTES = "causation_disputes"
    DAMAGES_ARGUMENTS = "damages_arguments"
    PROCEDURAL_DEFENSES = "procedural_defenses"
    EXPERT_WITNESS_CHALLENGES = "expert_witness_challenges"
    EVIDENCE_ADMISSIBILITY = "evidence_admissibility"

class StrengthLevel(str, Enum):
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

class AnalysisOptions(BaseModel):
    include_citations: bool = Field(True, description="Include case law citations analysis")
    verify_citations: bool = Field(False, description="Verify citation accuracy (slower)")
    extract_expert_challenges: bool = Field(True, description="Extract expert witness challenges")
    analyze_procedural_defenses: bool = Field(True, description="Analyze procedural defenses")

class LegalCitation(BaseModel):
    full_citation: str = Field(..., description="Complete legal citation")
    case_name: str = Field(..., description="Primary case name")
    legal_principle: str = Field(..., description="Legal principle or holding")
    application: str = Field(..., description="How citation applies to current case")
    jurisdiction: str = Field(..., description="Court jurisdiction")
    year: int = Field(..., description="Year of decision")
    is_binding: bool = Field(..., description="Whether citation is binding authority")
    citation_strength: StrengthLevel = Field(..., description="Strength of citation support")

class Argument(BaseModel):
    category: ArgumentCategory = Field(..., description="Argument category")
    argument_summary: str = Field(..., description="Summary of the argument")
    legal_basis: str = Field(..., description="Legal foundation for argument")
    strength_indicators: List[str] = Field(..., description="Factors indicating argument strength")
    cited_cases: List[LegalCitation] = Field(default_factory=list, description="Supporting case law")
    counterarguments: List[str] = Field(default_factory=list, description="Potential counterarguments")
    strength_assessment: StrengthLevel = Field(..., description="Overall argument strength")

class ResearchPriority(BaseModel):
    research_area: str = Field(..., description="Area requiring research")
    priority_level: int = Field(..., ge=1, le=5, description="Priority level (1-5)")
    suggested_sources: List[str] = Field(..., description="Recommended research sources")
    key_questions: List[str] = Field(..., description="Key questions to investigate")

class MotionAnalysisRequest(BaseModel):
    motion_text: str = Field(..., min_length=100, max_length=50000, description="Full text of the motion")
    case_context: Optional[str] = Field(None, max_length=2000, description="Additional case context")
    analysis_options: AnalysisOptions = Field(default_factory=AnalysisOptions)
    
    @validator('motion_text')
    def validate_motion_text(cls, v):
        if not v.strip():
            raise ValueError('Motion text cannot be empty')
        return v.strip()

class MotionAnalysisResult(BaseModel):
    motion_type: str = Field(..., description="Type of legal motion")
    case_number: Optional[str] = Field(None, description="Case identification number")
    parties: List[str] = Field(default_factory=list, description="Parties involved")
    filing_date: Optional[datetime] = Field(None, description="Motion filing date")
    primary_arguments: List[Argument] = Field(..., description="Primary legal arguments")
    procedural_issues: List[str] = Field(default_factory=list, description="Procedural issues identified")
    evidence_challenges: List[str] = Field(default_factory=list, description="Evidence admissibility challenges")
    expert_witness_issues: List[str] = Field(default_factory=list, description="Expert witness challenges")
    research_priorities: List[ResearchPriority] = Field(..., description="Research recommendations")
    overall_strength: StrengthLevel = Field(..., description="Overall motion strength assessment")
    risk_assessment: int = Field(..., ge=1, le=10, description="Risk level (1-10)")
    recommended_actions: List[str] = Field(..., description="Recommended response actions")

class MotionAnalysisResponse(MotionAnalysisResult):
    request_id: str = Field(..., description="Unique request identifier")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "motion_type": "Motion for Summary Judgment",
                "case_number": "2024-CV-12345",
                "parties": ["Plaintiff Corp", "Defendant LLC"],
                "primary_arguments": [
                    {
                        "category": "negligence_causation",
                        "argument_summary": "Lack of proximate cause between defendant's actions and plaintiff's injuries",
                        "legal_basis": "Proximate cause requires direct and foreseeable connection",
                        "strength_indicators": ["Multiple intervening factors", "Expert testimony challenges"],
                        "strength_assessment": "strong"
                    }
                ],
                "overall_strength": "strong",
                "risk_assessment": 7,
                "recommended_actions": ["File comprehensive opposition brief", "Conduct additional discovery"],
                "processing_time": 3.2
            }
        }
    )

class HealthCheck(BaseModel):
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="API version")