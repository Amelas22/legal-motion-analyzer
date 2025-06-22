import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import json

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.models.schemas import (
    MotionAnalysisResult, 
    Argument, 
    LegalCitation, 
    ResearchPriority,
    ArgumentCategory,
    StrengthLevel,
    AnalysisOptions
)
from app.core.config import settings

logger = logging.getLogger(__name__)

class MotionAnalyzer:
    def __init__(self):
        self.client = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the OpenAI client"""
        if self._initialized:
            return
            
        try:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self._initialized = True
            logger.info("Motion analyzer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize motion analyzer: {e}")
            raise

    def _get_system_prompt(self) -> str:
        return """You are an expert legal analyst specializing in personal injury law and motion practice. 
Your role is to analyze opposing counsel motions with precision and provide structured, 
actionable insights for legal response strategy.

Key Analysis Areas:
1. NEGLIGENCE ELEMENTS: Analyze duty, breach, causation, and damages arguments
2. LIABILITY ISSUES: Identify comparative fault, joint liability, and immunity claims  
3. PROCEDURAL DEFENSES: Evaluate jurisdiction, venue, statute of limitations, and service issues
4. EXPERT WITNESS CHALLENGES: Assess Daubert/Frye challenges and qualification attacks
5. EVIDENCE ADMISSIBILITY: Review Rule 702, 403, and other evidentiary challenges
6. LEGAL CITATIONS: Extract and categorize case law WITHOUT fabricating citations

Analysis Standards:
- ACCURACY: Only extract citations that appear in the document
- PRECISION: Provide specific legal principles and applications
- STRATEGY: Focus on practical response recommendations
- COMPREHENSIVENESS: Address all major legal arguments presented
- RISK ASSESSMENT: Evaluate realistic success probability for opposing motion

Legal Citation Requirements:
- Extract ONLY citations that appear in the motion text
- Include full citation format, case name, legal principle, and application
- Assess binding vs. persuasive authority based on jurisdiction
- Evaluate citation strength and relevance to current case
- NEVER create or invent citations not present in the document

You must respond with a valid JSON object that follows this exact structure:
{
    "motion_type": "string (e.g., Motion to Dismiss, Motion for Summary Judgment)",
    "case_number": "string or null",
    "parties": ["array of party names"],
    "filing_date": null,
    "primary_arguments": [
        {
            "category": "negligence_duty|negligence_breach|negligence_causation|negligence_damages|liability_issues|causation_disputes|damages_arguments|procedural_defenses|expert_witness_challenges|evidence_admissibility",
            "argument_summary": "Brief summary of the argument",
            "legal_basis": "Legal foundation for the argument",
            "strength_indicators": ["List of factors indicating argument strength"],
            "cited_cases": [
                {
                    "full_citation": "Complete legal citation",
                    "case_name": "Case name",
                    "legal_principle": "Legal principle or holding",
                    "application": "How it applies to current case",
                    "jurisdiction": "Court jurisdiction",
                    "year": 2020,
                    "is_binding": true,
                    "citation_strength": "very_weak|weak|moderate|strong|very_strong"
                }
            ],
            "counterarguments": ["Potential counterarguments"],
            "strength_assessment": "very_weak|weak|moderate|strong|very_strong"
        }
    ],
    "procedural_issues": ["List of procedural issues identified"],
    "evidence_challenges": ["Evidence admissibility challenges"],
    "expert_witness_issues": ["Expert witness challenges"],
    "research_priorities": [
        {
            "research_area": "Area requiring research",
            "priority_level": 1,
            "suggested_sources": ["Recommended research sources"],
            "key_questions": ["Key questions to investigate"]
        }
    ],
    "overall_strength": "very_weak|weak|moderate|strong|very_strong",
    "risk_assessment": 7,
    "recommended_actions": ["List of recommended response actions"]
}"""

    async def _extract_legal_citations(self, motion_text: str) -> List[Dict[str, Any]]:
        """Extract legal citations from motion text without fabrication"""
        citations = []
        
        # Comprehensive pattern for legal citations
        citation_patterns = [
            # Federal cases: 123 F.3d 456 (9th Cir. 2020)
            r'(\w+(?:\s+\w+)*)\s*v\.\s*(\w+(?:\s+\w+)*),?\s*(\d+)\s+(F\.\d?d|F\.\s?Supp\.?\s?\d?d?|U\.S\.)\s+(\d+)(?:\s*\(([^)]+)\s*(\d{4})\))?',
            # State cases with various reporters
            r'(\w+(?:\s+\w+)*)\s*v\.\s*(\w+(?:\s+\w+)*),?\s*(\d+)\s+([A-Z][^,\d]*?)\s+(\d+)(?:\s*\(([^)]+)\s*(\d{4})\))?',
        ]
        
        for pattern in citation_patterns:
            for match in re.finditer(pattern, motion_text, re.IGNORECASE):
                try:
                    case_name = f"{match.group(1).strip()} v. {match.group(2).strip()}"
                    volume = match.group(3)
                    reporter = match.group(4).strip()
                    page = match.group(5)
                    court = match.group(6) if match.group(6) else "Unknown"
                    year = int(match.group(7)) if match.group(7) else 0
                    
                    citations.append({
                        "full_citation": match.group(0).strip(),
                        "case_name": case_name,
                        "volume": volume,
                        "reporter": reporter,
                        "page": page,
                        "court": court,
                        "year": year
                    })
                except (ValueError, AttributeError):
                    continue
                    
        return citations[:20]  # Limit to prevent overwhelming responses

    async def analyze_motion(
        self, 
        motion_text: str, 
        case_context: Optional[str] = None,
        analysis_options: Optional[AnalysisOptions] = None
    ) -> MotionAnalysisResult:
        """
        Analyze legal motion and extract structured data
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Extract citations separately for validation
            extracted_citations = await self._extract_legal_citations(motion_text)
            
            # Prepare the user prompt
            user_prompt = f"""Please analyze the following legal motion and provide a comprehensive structured response.

MOTION TEXT:
{motion_text}

{"CASE CONTEXT: " + case_context if case_context else ""}

EXTRACTED CITATIONS (use only these):
{json.dumps(extracted_citations, indent=2)}

Analyze all arguments, identify the motion type, assess strength and risk, and provide actionable recommendations.
Remember to ONLY use citations that appear in the motion text."""

            # Make the API call with JSON mode
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                max_tokens=3000
            )
            
            # Parse the response
            result_data = json.loads(response.choices[0].message.content)
            
            # Validate and create the result object
            motion_result = MotionAnalysisResult(**result_data)
            
            # Post-process to validate citations
            processed_result = await self._post_process_analysis(motion_result, motion_text, extracted_citations)
            
            # Log usage
            if response.usage:
                logger.info(
                    f"Motion analysis completed - Tokens used: {response.usage.total_tokens} "
                    f"(prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens})"
                )
            
            return processed_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            raise Exception("Analysis failed: Invalid response format from AI model")
            
        except ValidationError as e:
            logger.error(f"Response validation failed: {e}")
            raise Exception("Analysis failed: Response did not match expected format")
            
        except Exception as e:
            logger.error(f"Motion analysis failed: {e}")
            raise Exception(f"Analysis failed: {str(e)}")

    async def _post_process_analysis(
        self, 
        result: MotionAnalysisResult, 
        motion_text: str,
        extracted_citations: List[Dict[str, Any]]
    ) -> MotionAnalysisResult:
        """Post-process analysis results for quality and completeness"""
        
        # Create a set of valid citation names for quick lookup
        valid_citations = {cite['case_name'].lower() for cite in extracted_citations}
        
        # Validate and clean citations
        for arg in result.primary_arguments:
            clean_citations = []
            for citation in arg.cited_cases:
                # Validate citation appears in motion text or extracted citations
                if (citation.case_name.lower() in motion_text.lower() or 
                    citation.case_name.lower() in valid_citations):
                    clean_citations.append(citation)
                else:
                    logger.warning(f"Removed potentially fabricated citation: {citation.case_name}")
            arg.cited_cases = clean_citations
            
        # Ensure minimum argument coverage
        covered_categories = {arg.category for arg in result.primary_arguments}
        required_categories = [
            ArgumentCategory.NEGLIGENCE_CAUSATION,
            ArgumentCategory.LIABILITY_ISSUES,
            ArgumentCategory.PROCEDURAL_DEFENSES
        ]
        
        for category in required_categories:
            if category not in covered_categories:
                # Add placeholder argument if major category missing
                result.primary_arguments.append(
                    Argument(
                        category=category,
                        argument_summary=f"No specific {category.value} arguments identified in motion",
                        legal_basis="Standard personal injury law analysis",
                        strength_indicators=["Analysis pending"],
                        cited_cases=[],
                        counterarguments=[],
                        strength_assessment=StrengthLevel.MODERATE
                    )
                )
        
        # Ensure research priorities exist
        if not result.research_priorities:
            result.research_priorities = [
                ResearchPriority(
                    research_area="General motion response",
                    priority_level=1,
                    suggested_sources=["Case law databases", "Legal precedents"],
                    key_questions=["What are the strongest counterarguments?"]
                )
            ]
        
        return result

    async def health_check(self) -> bool:
        """Perform health check on the motion analyzer"""
        if not self._initialized:
            return False
            
        try:
            # Simple test to verify OpenAI connection
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def cleanup(self):
        """Cleanup resources"""
        self._initialized = False
        self.client = None
        logger.info("Motion analyzer cleaned up")