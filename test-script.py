#!/usr/bin/env python3
"""
Example: Using the Comprehensive Legal Motion Analyzer API v2.0

This script demonstrates how to use the new comprehensive analysis
that extracts ALL arguments from a motion.
"""

import requests
import json
from typing import Dict, List, Any
from datetime import datetime


class MotionAnalyzerClient:
    """Client for the Comprehensive Motion Analyzer API"""
    
    def __init__(self, base_url: str = "http://localhost:8888"):
        self.base_url = base_url
        self.api_path = f"{base_url}/api/v1"
        
    def analyze_motion(
        self, 
        motion_text: str, 
        case_context: str = None,
        extract_all: bool = True,
        allow_custom_categories: bool = True
    ) -> Dict[str, Any]:
        """Analyze a legal motion comprehensively"""
        
        payload = {
            "motion_text": motion_text,
            "case_context": case_context,
            "analysis_options": {
                "extract_all_arguments": extract_all,
                "allow_custom_categories": allow_custom_categories,
                "include_citations": True
            }
        }
        
        response = requests.post(
            f"{self.api_path}/analyze-motion",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Analysis failed: {response.status_code} - {response.text}")
    
    def print_analysis_summary(self, result: Dict[str, Any]):
        """Print a formatted summary of the analysis"""
        
        print("\n" + "="*60)
        print("COMPREHENSIVE MOTION ANALYSIS SUMMARY")
        print("="*60)
        
        print(f"\nMotion Type: {result.get('motion_type', 'Unknown')}")
        print(f"Case Number: {result.get('case_number', 'Not specified')}")
        print(f"Total Arguments Found: {result.get('total_arguments_found', 0)}")
        print(f"Analysis Confidence: {result.get('confidence_in_analysis', 0):.0%}")
        
        # Show arguments by category
        print("\n" + "-"*40)
        print("ARGUMENTS BY CATEGORY:")
        print("-"*40)
        
        args_by_cat = result.get('arguments_by_category', {})
        for category, args in args_by_cat.items():
            print(f"\n{category.upper()} ({len(args)} arguments):")
            for arg in args[:3]:  # Show first 3 per category
                print(f"  [{arg['argument_id']}] {arg['argument_summary'][:60]}...")
                print(f"       Strength: {arg['strength_assessment']} | Priority: {arg['priority_level']}")
        
        # Show argument groups
        if result.get('argument_groups'):
            print("\n" + "-"*40)
            print("STRATEGIC ARGUMENT GROUPS:")
            print("-"*40)
            
            for group in result['argument_groups']:
                print(f"\n{group['group_name']}:")
                print(f"  Theme: {group['theme']}")
                print(f"  Combined Strength: {group['combined_strength']}")
                print(f"  Arguments: {', '.join(arg['argument_id'] for arg in group['arguments'])}")
        
        # Show strongest/weakest
        print("\n" + "-"*40)
        print("CRITICAL ARGUMENTS:")
        print("-"*40)
        
        print(f"\nStrongest Arguments to Address:")
        for arg_id in result.get('strongest_arguments', [])[:3]:
            # Find the argument
            for arg in result.get('all_arguments', []):
                if arg['argument_id'] == arg_id:
                    print(f"  - [{arg_id}] {arg['argument_summary'][:60]}...")
                    break
        
        print(f"\nWeakest Arguments (Opportunities):")
        for arg_id in result.get('weakest_arguments', [])[:3]:
            # Find the argument
            for arg in result.get('all_arguments', []):
                if arg['argument_id'] == arg_id:
                    print(f"  - [{arg_id}] {arg['argument_summary'][:60]}...")
                    break
        
        # Show missing/implied
        if result.get('implied_arguments') or result.get('notable_omissions'):
            print("\n" + "-"*40)
            print("IMPLIED/MISSING ARGUMENTS:")
            print("-"*40)
            
            for implied in result.get('implied_arguments', []):
                print(f"  - Implied: {implied}")
            
            for omission in result.get('notable_omissions', []):
                print(f"  - Missing: {omission}")
        
        # Response recommendations
        print("\n" + "-"*40)
        print("RECOMMENDED RESPONSE STRATEGY:")
        print("-"*40)
        
        print("\nResponse Structure:")
        for i, step in enumerate(result.get('recommended_response_structure', [])[:5], 1):
            print(f"  {i}. {step}")
        
        print("\nKey Actions:")
        for action in result.get('recommended_actions', [])[:5]:
            print(f"  • {action}")
        
        # Custom categories if any
        if result.get('custom_categories_created'):
            print("\n" + "-"*40)
            print("CUSTOM CATEGORIES CREATED:")
            print("-"*40)
            for cat in result['custom_categories_created']:
                print(f"  - {cat}")
    
    def export_argument_outline(self, result: Dict[str, Any], filename: str):
        """Export arguments to a structured file for response drafting"""
        
        outline = {
            "motion_type": result.get('motion_type'),
            "case_number": result.get('case_number'),
            "analysis_date": datetime.now().isoformat(),
            "total_arguments": result.get('total_arguments_found'),
            "arguments_to_address": []
        }
        
        # Organize arguments by priority
        all_args = result.get('all_arguments', [])
        sorted_args = sorted(all_args, key=lambda x: x.get('priority_level', 5))
        
        for arg in sorted_args:
            outline_arg = {
                "id": arg['argument_id'],
                "category": arg['category'],
                "summary": arg['argument_summary'],
                "location": arg.get('location_in_motion'),
                "strength": arg['strength_assessment'],
                "priority": arg['priority_level'],
                "our_response": "",  # To be filled by attorney
                "evidence_needed": arg.get('required_evidence', []),
                "citations_to_distinguish": [
                    cite['case_name'] for cite in arg.get('cited_cases', [])
                ],
                "notes": ""
            }
            outline['arguments_to_address'].append(outline_arg)
        
        with open(filename, 'w') as f:
            json.dump(outline, f, indent=2)
        
        print(f"\nArgument outline exported to: {filename}")


def main():
    """Example usage of the comprehensive analyzer"""
    
    # Initialize client
    client = MotionAnalyzerClient()
    
    # Example motion text (based on the real motion from your example)
    motion_text = """
    DEFENDANT'S MOTION IN LIMINE TO EXCLUDE EVIDENCE AND ARGUMENT 
    AND TO STRIKE/DISMISS ACTIVE NEGLIGENCE CLAIM

    Defendant Performance Transportation, LLC d/b/a Performance Food Group ("PFG") 
    respectfully moves this Court for an order excluding evidence and argument 
    regarding Count II (active negligence) of Plaintiff's Second Amended Complaint.

    I. INTRODUCTION
    Count II alleges PFG was actively negligent in the operation and maintenance 
    of the vehicle. However, this claim is entirely derivative of the alleged 
    negligence of the driver, Jones Destin, and imposes no additional liability 
    beyond Count III (dangerous instrumentality doctrine/vicarious liability).

    II. LEGAL ARGUMENT

    A. Count II Is Redundant and Prejudicial
    Under Florida law, derivative liability requires a direct tortfeasor's 
    negligence for liability to attach. Grobman v. Posey, 863 So. 2d 1230, 1236 
    (Fla. 4th DCA 2003). Both Count II and Count III depend entirely on 
    establishing Destin's negligence.

    B. Dangerous Instrumentality Doctrine Already Imposes Full Liability
    The dangerous instrumentality doctrine imposes vicarious liability on vehicle 
    owners for operators' negligence. Aurbach v. Gallina, 753 So. 2d 60, 62 
    (Fla. 2000). PFG admits Destin was acting within the scope of employment.

    C. Negligent Hiring/Supervision Claims Are Improper
    Where negligent hiring/supervision claims impose no additional liability 
    beyond vicarious liability, such claims should not be presented to the jury. 
    Clooney v. Geeting, 352 So. 2d 1216 (Fla. 2d DCA 1977).

    D. Risk of Improper Fault Allocation
    Allowing both claims risks the jury improperly allocating fault between PFG 
    and Destin, which is prohibited under Florida law for derivative liability.

    III. RELIEF REQUESTED
    PFG respectfully requests the Court:
    1. Exclude all evidence and argument regarding active negligence
    2. Strike Count II from the operative complaint
    3. Enter an order prohibiting reference to independent PFG negligence
    """
    
    case_context = """
    Personal injury case arising from commercial vehicle accident. 
    Plaintiff is estate of deceased. Both driver (Destin) and employer (PFG) 
    are defendants. Second Amended Complaint includes both active negligence 
    and vicarious liability claims against PFG.
    """
    
    try:
        print("Analyzing motion...")
        result = client.analyze_motion(motion_text, case_context)
        
        # Print comprehensive summary
        client.print_analysis_summary(result)
        
        # Export outline for response drafting
        client.export_argument_outline(result, "motion_response_outline.json")
        
        # Show processing stats
        print("\n" + "="*60)
        print("PROCESSING STATISTICS")
        print("="*60)
        print(f"Request ID: {result.get('request_id')}")
        print(f"Processing Time: {result.get('processing_time', 0):.2f} seconds")
        print(f"Categories Used: {len(result.get('categories_used', []))}")
        print(f"Custom Categories: {len(result.get('custom_categories_created', []))}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()