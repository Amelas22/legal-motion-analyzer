import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import json
import uuid

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.models.schemas import (
    ComprehensiveMotionAnalysis,
    ExtractedArgument,
    ArgumentGroup,
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
        return """You are an expert legal analyst specializing in comprehensive motion analysis. Your primary goal is to extract EVERY SINGLE ARGUMENT from the opposing counsel's motion, no matter how minor, then categorize and analyze each one.

CRITICAL INSTRUCTION: Extract ALL arguments first, then assign categories. Do not limit yourself to predefined categories.

Analysis Process:
1. READ THOROUGHLY: Read the entire motion carefully
2. EXTRACT EVERYTHING: Identify every distinct argument, claim, or legal position
3. QUOTE OR PARAPHRASE: For each argument, provide the actual text or close paraphrase
4. CATEGORIZE FLEXIBLY: Assign the most appropriate category, create custom ones if needed
5. ANALYZE COMPREHENSIVELY: Evaluate strength, identify weaknesses, note citations
6. GROUP STRATEGICALLY: Identify related arguments that work together
7. IDENTIFY PATTERNS: Note overall strategies and themes

Argument Extraction Rules:
- Extract MAJOR arguments (primary claims, key legal theories)
- Extract MINOR arguments (supporting points, subsidiary claims)  
- Extract PROCEDURAL arguments (jurisdiction, venue, timing, etc.)
- Extract IMPLIED arguments (positions implied but not explicitly stated)
- Extract FACTUAL assertions that support legal arguments
- Note MISSING arguments (what they could have argued but didn't)

Categories to Consider (but not limited to):
- Negligence elements (duty, breach, causation, damages)
- Liability theories (vicarious, direct, derivative, comparative, etc.)
- Causation types (proximate, factual, intervening, superseding)
- Damages (economic, non-economic, punitive, mitigation)
- Procedural (jurisdiction, venue, service, statute of limitations, standing)
- Evidence (admissibility, relevance, prejudice, hearsay, privilege)
- Expert witness (qualification, methodology, reliability, Daubert)
- Contract, insurance, constitutional issues
- Create CUSTOM categories as needed for arguments that don't fit

For Each Argument Include:
- Unique ID (arg_001, arg_002, etc.)
- Direct quote or close paraphrase from motion
- Location in motion (section/paragraph)
- Category (use existing or create custom)
- Strength assessment with specific reasons
- Citations used to support it
- Potential weaknesses
- Counter-arguments available
- Priority for response (1-5)

Legal Citation Requirements:
- Extract ONLY citations that appear in the motion text
- Never fabricate citations
- Include full citation, case name, principle, and application
- Note if citation is binding or persuasive authority

Strategic Analysis:
- Group related arguments that build on each other
- Identify overarching themes and strategies
- Note which arguments are strongest/weakest
- Identify what evidence or experts would be needed to counter
- Suggest optimal response structure

You must respond with a valid JSON object following the exact structure provided, capturing EVERY argument in the motion."""

    def _get_extraction_prompt(self) -> str:
        return """Focus on extracting arguments using these patterns:

1. Look for argument indicators:
   - "Plaintiff/Defendant argues..."
   - "The undisputed facts show..."
   - "As a matter of law..."
   - "Courts have held..."
   - "The evidence demonstrates..."
   - "Plaintiff fails to..."
   - "There is no genuine issue..."

2. Extract from motion structure:
   - Introduction/Background arguments
   - Each numbered or lettered section
   - Legal standard arguments
   - Application of law to facts
   - Policy arguments
   - Conclusion requests

3. Don't miss:
   - Arguments in footnotes
   - Arguments embedded in fact sections
   - Implicit arguments from case citations
   - Arguments about burden of proof
   - Procedural arguments mixed with substantive ones

Remember: When in doubt, extract it as a separate argument. Better to have too many than miss one."""

    async def _extract_legal_citations(self, motion_text: str) -> List[Dict[str, Any]]:
        """Extract legal citations from motion text without fabrication"""
        citations = []
        
        # Comprehensive pattern for legal citations
        citation_patterns = [
            # Federal cases: 123 F.3d 456 (9th Cir. 2020)
            r'(\w+(?:\s+\w+)*)\s*v\.\s*(\w+(?:\s+\w+)*),?\s*(\d+)\s+(F\.\d?d|F\.\s?Supp\.?\s?\d?d?|U\.S\.)\s+(\d+)(?:\s*\(([^)]+)\s*(\d{4})\))?',
            # State cases with various reporters
            r'(\w+(?:\s+\w+)*)\s*v\.\s*(\w+(?:\s+\w+)*),?\s*(\d+)\s+([A-Z][^,\d]*?)\s+(\d+)(?:\s*\(([^)]+)\s*(\d{4})\))?',
            # Statutory citations
            r'(\d+)\s+(U\.S\.C\.|C\.F\.R\.|[A-Z][a-z]+\.\s*(?:Civ\.|Crim\.|Evid\.|R\.)\s*(?:Proc\.|Code)?)\s*§+\s*(\d+(?:\.\d+)*(?:\([a-zA-Z0-9]+\))*)',
        ]
        
        for pattern in citation_patterns:
            for match in re.finditer(pattern, motion_text, re.IGNORECASE):
                try:
                    if "U.S.C." in match.group(0) or "C.F.R." in match.group(0) or "Code" in match.group(0):
                        # Statutory citation
                        citations.append({
                            "full_citation": match.group(0).strip(),
                            "type": "statute",
                            "title": match.group(1),
                            "code": match.group(2),
                            "section": match.group(3)
                        })
                    else:
                        # Case citation
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
                            "year": year,
                            "type": "case"
                        })
                except (ValueError, AttributeError):
                    continue
                    
        return citations[:50]  # Limit to prevent overwhelming responses

    async def analyze_motion(
        self, 
        motion_text: str, 
        case_context: Optional[str] = None,
        analysis_options: Optional[AnalysisOptions] = None
    ) -> ComprehensiveMotionAnalysis:
        """
        Analyze legal motion and extract ALL arguments with comprehensive structure
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Extract citations separately for validation
            extracted_citations = await self._extract_legal_citations(motion_text)
            
            # Prepare the user prompt
            user_prompt = f"""Please analyze this legal motion and extract EVERY SINGLE ARGUMENT, no matter how minor.

MOTION TEXT:
{motion_text}

{"CASE CONTEXT: " + case_context if case_context else ""}

EXTRACTED CITATIONS (use only these):
{json.dumps(extracted_citations, indent=2)}

{self._get_extraction_prompt()}

Remember:
1. Extract ALL arguments first (aim for comprehensive coverage)
2. Assign appropriate categories (create custom ones if needed)
3. Each argument gets a unique ID (arg_001, arg_002, etc.)
4. Group related arguments
5. Identify strategic themes
6. Note what's missing or implied
7. Prioritize arguments for response

The goal is to ensure we don't miss ANY argument that needs to be addressed in our response."""

            # Make the API call with JSON mode
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                max_tokens=4000  # Increased for comprehensive extraction
            )
            
            # Parse the response
            result_data = json.loads(response.choices[0].message.content)
            
            # Ensure proper structure for the new schema
            result_data = self._ensure_comprehensive_structure(result_data)
            
            # Validate and create the result object
            motion_result = ComprehensiveMotionAnalysis(**result_data)
            
            # Post-process to validate citations and organize
            processed_result = await self._post_process_comprehensive_analysis(
                motion_result, motion_text, extracted_citations
            )
            
            # Log usage
            if response.usage:
                logger.info(
                    f"Motion analysis completed - Arguments found: {processed_result.total_arguments_found} - "
                    f"Tokens used: {response.usage.total_tokens}"
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

    def _ensure_comprehensive_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure the response data has all required fields for ComprehensiveMotionAnalysis"""
        
        # Ensure all_arguments have proper IDs
        if 'all_arguments' in data:
            for i, arg in enumerate(data['all_arguments']):
                if 'argument_id' not in arg:
                    arg['argument_id'] = f"arg_{i+1:03d}"
                if 'confidence_score' not in arg:
                    arg['confidence_score'] = 0.8
                if 'priority_level' not in arg:
                    arg['priority_level'] = 3
                if 'subcategories' not in arg:
                    arg['subcategories'] = []
                if 'weaknesses' not in arg:
                    arg['weaknesses'] = []
                if 'cited_statutes' not in arg:
                    arg['cited_statutes'] = []
        
        # Build arguments_by_category if not present
        if 'arguments_by_category' not in data and 'all_arguments' in data:
            data['arguments_by_category'] = {}
            for arg in data['all_arguments']:
                category = arg.get('category', 'other')
                if category not in data['arguments_by_category']:
                    data['arguments_by_category'][category] = []
                data['arguments_by_category'][category].append(arg)
        
        # Ensure required fields
        data['total_arguments_found'] = len(data.get('all_arguments', []))
        
        if 'categories_used' not in data:
            data['categories_used'] = list(data.get('arguments_by_category', {}).keys())
        
        if 'confidence_in_analysis' not in data:
            data['confidence_in_analysis'] = 0.85
            
        return data

    async def _post_process_comprehensive_analysis(
        self, 
        result: ComprehensiveMotionAnalysis, 
        motion_text: str,
        extracted_citations: List[Dict[str, Any]]
    ) -> ComprehensiveMotionAnalysis:
        """Post-process comprehensive analysis for quality and completeness"""
        
        # Create a set of valid citation names for quick lookup
        valid_case_citations = {
            cite['case_name'].lower() 
            for cite in extracted_citations 
            if cite.get('type') == 'case'
        }
        valid_statute_citations = {
            cite['full_citation'].lower() 
            for cite in extracted_citations 
            if cite.get('type') == 'statute'
        }
        
        # Validate and clean citations in each argument
        for arg in result.all_arguments:
            # Clean case citations
            clean_citations = []
            for citation in arg.cited_cases:
                if (citation.case_name.lower() in motion_text.lower() or 
                    citation.case_name.lower() in valid_case_citations):
                    clean_citations.append(citation)
                else:
                    logger.warning(f"Removed potentially fabricated citation: {citation.case_name}")
            arg.cited_cases = clean_citations
            
            # Validate statute citations
            clean_statutes = []
            for statute in arg.cited_statutes:
                if (statute.lower() in motion_text.lower() or 
                    any(statute.lower() in cite for cite in valid_statute_citations)):
                    clean_statutes.append(statute)
            arg.cited_statutes = clean_statutes
        
        # Identify any arguments that might have been missed
        potential_missed = self._check_for_missed_arguments(motion_text, result)
        if potential_missed:
            result.notable_omissions.extend(potential_missed)
        
        # Ensure research priorities reference actual arguments
        for priority in result.research_priorities:
            if not priority.related_arguments:
                # Link to relevant arguments based on research area
                related = [
                    arg.argument_id for arg in result.all_arguments
                    if priority.research_area.lower() in arg.argument_summary.lower()
                ]
                priority.related_arguments = related[:3]  # Top 3 related
        
        # Update metadata
        result.total_arguments_found = len(result.all_arguments)
        result.categories_used = list(result.arguments_by_category.keys())
        
        # Identify custom categories (those not in ArgumentCategory enum)
        standard_categories = {cat.value for cat in ArgumentCategory}
        result.custom_categories_created = [
            cat for cat in result.categories_used 
            if cat not in standard_categories
        ]
        
        return result

    def _check_for_missed_arguments(
        self, 
        motion_text: str, 
        result: ComprehensiveMotionAnalysis
    ) -> List[str]:
        """Check for potentially missed arguments based on common patterns"""
        missed = []
        
        # Check for common argument patterns not covered
        patterns_to_check = [
            (r"statute of limitations", "Statute of limitations argument"),
            (r"failure to state a claim", "Failure to state a claim argument"),
            (r"lack of standing", "Standing challenge"),
            (r"improper venue", "Venue challenge"),
            (r"personal jurisdiction", "Personal jurisdiction challenge"),
            (r"failure to join.*party", "Failure to join necessary party"),
            (r"res judicata|collateral estoppel", "Preclusion argument"),
            (r"arbitration clause|agreement", "Arbitration argument"),
            (r"qualified immunity", "Qualified immunity defense"),
            (r"governmental immunity", "Governmental immunity defense"),
        ]
        
        existing_summaries = " ".join([
            arg.argument_summary.lower() for arg in result.all_arguments
        ])
        
        for pattern, description in patterns_to_check:
            if re.search(pattern, motion_text, re.IGNORECASE):
                if not re.search(pattern, existing_summaries, re.IGNORECASE):
                    missed.append(f"Potential {description} not fully extracted")
        
        return missed[:5]  # Limit to top 5 to avoid noise

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