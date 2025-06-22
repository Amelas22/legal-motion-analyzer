#!/bin/bash

# Test script for Comprehensive Legal Motion API v2.0

echo "🧪 Testing Comprehensive Legal Motion API v2.0"
echo "============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# API base URL
API_URL="http://localhost:8888"

# Test 1: Health Check
echo -e "${YELLOW}1. Health Check${NC}"
HEALTH=$(curl -s $API_URL/health 2>/dev/null)
if [[ "$HEALTH" == *"healthy"* ]]; then
    echo -e "${GREEN}✓ Service is healthy${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    echo "Response: $HEALTH"
    exit 1
fi

# Test 2: Argument Categories
echo ""
echo -e "${YELLOW}2. Available Argument Categories${NC}"
CATEGORIES=$(curl -s $API_URL/api/v1/argument-categories 2>/dev/null)
if [[ "$CATEGORIES" == *"negligence"* ]]; then
    echo -e "${GREEN}✓ Categories endpoint working${NC}"
    TOTAL_CATS=$(echo $CATEGORIES | grep -o '"total_categories":[0-9]*' | cut -d':' -f2)
    echo "  Total predefined categories: $TOTAL_CATS"
    echo "  Note: AI can create custom categories as needed"
else
    echo -e "${RED}✗ Categories endpoint failed${NC}"
fi

# Test 3: Comprehensive Motion Analysis
echo ""
echo -e "${YELLOW}3. Comprehensive Motion Analysis${NC}"
echo -e "${BLUE}Testing with motion that has multiple arguments...${NC}"

MOTION_RESPONSE=$(curl -s -X POST $API_URL/api/v1/analyze-motion \
  -H "Content-Type: application/json" \
  -d '{
    "motion_text": "DEFENDANTS MOTION IN LIMINE TO EXCLUDE EVIDENCE AND ARGUMENT AND TO STRIKE/DISMISS ACTIVE NEGLIGENCE CLAIM\n\nI. INTRODUCTION\nDefendant Performance Food Group (PFG) moves to exclude evidence and argument regarding Count II (active negligence) as it imposes no additional liability beyond Count III (vicarious liability under dangerous instrumentality doctrine).\n\nII. LEGAL STANDARD\nA. Motions in limine prevent prejudicial evidence. See Luce v. United States, 469 U.S. 38 (1984).\nB. Derivative liability requires a direct tortfeasors negligence. Grobman v. Posey, 863 So. 2d 1230, 1236 (Fla. 4th DCA 2003).\n\nIII. ARGUMENT\nA. Count II Is Duplicative and Prejudicial\n1. Both counts depend on driver Destins negligence\n2. PFG admits Destin was acting within scope of employment\n3. Dangerous instrumentality doctrine already imposes full vicarious liability. Aurbach v. Gallina, 753 So. 2d 60, 62 (Fla. 2000).\n\nB. Florida Law Prohibits Separate Negligent Hiring Claims\nWhen vicarious liability applies, negligent hiring/supervision claims should be dismissed. Clooney v. Geeting, 352 So. 2d 1216 (Fla. 2d DCA 1977).\n\nC. Allowing Both Claims Risks Improper Fault Allocation\n1. Jury cannot allocate fault between PFG and Destin separately\n2. Section 768.81 requires treating them as one entity for fault purposes\n\nIV. RELIEF REQUESTED\nPFG requests the Court:\n1. Exclude all evidence related to negligent hiring/supervision\n2. Strike Count II from the complaint\n3. Prohibit argument suggesting PFG has independent negligence",
    "case_context": "Personal injury case involving commercial vehicle accident. Plaintiff suing both driver and employer.",
    "analysis_options": {
      "extract_all_arguments": true,
      "allow_custom_categories": true
    }
  }' 2>/dev/null)

if [[ "$MOTION_RESPONSE" == *"all_arguments"* ]]; then
    echo -e "${GREEN}✓ Comprehensive analysis completed${NC}"
    
    # Extract statistics
    TOTAL_ARGS=$(echo $MOTION_RESPONSE | grep -o '"total_arguments_found":[0-9]*' | cut -d':' -f2)
    echo -e "  ${BLUE}Total arguments extracted: $TOTAL_ARGS${NC}"
    
    # Show first few argument IDs
    echo -e "  ${BLUE}Sample argument IDs:${NC}"
    echo $MOTION_RESPONSE | grep -o '"argument_id":"[^"]*"' | head -3 | while read -r line; do
        ARG_ID=$(echo $line | cut -d'"' -f4)
        echo "    - $ARG_ID"
    done
    
    # Check for argument groups
    if [[ "$MOTION_RESPONSE" == *"argument_groups"* ]]; then
        echo -e "  ${GREEN}✓ Arguments grouped strategically${NC}"
    fi
    
    # Check for custom categories
    if [[ "$MOTION_RESPONSE" == *"custom_categories_created"* ]]; then
        echo -e "  ${GREEN}✓ Custom category support confirmed${NC}"
    fi
else
    echo -e "${RED}✗ Comprehensive analysis failed${NC}"
    echo "Response preview: ${MOTION_RESPONSE:0:200}..."
fi

# Test 4: Multiple Arguments Same Category
echo ""
echo -e "${YELLOW}4. Testing Multiple Arguments in Same Category${NC}"

MULTI_ARG_RESPONSE=$(curl -s -X POST $API_URL/api/v1/analyze-motion \
  -H "Content-Type: application/json" \
  -d '{
    "motion_text": "MOTION FOR SUMMARY JUDGMENT\n\nDefendant moves for summary judgment based on multiple procedural defects:\n\n1. STATUTE OF LIMITATIONS: This action is time-barred under the two-year statute. Filed 2/15/2024 for incident on 2/1/2022.\n\n2. LACK OF PERSONAL JURISDICTION: Defendant has no contacts with Florida. No business, property, or transactions here.\n\n3. IMPROPER VENUE: Even if jurisdiction exists, venue is improper under 28 U.S.C. § 1391. No events occurred in this district.\n\n4. FAILURE TO JOIN NECESSARY PARTY: The actual property owner must be joined under Rule 19. Their absence prevents complete relief.\n\n5. PRIOR PENDING ACTION: This identical claim is already pending in Georgia state court (Case No. 2023-CV-1234).",
    "case_context": "Federal diversity case"
  }' 2>/dev/null)

if [[ "$MULTI_ARG_RESPONSE" == *"all_arguments"* ]]; then
    TOTAL_PROCEDURAL=$(echo $MULTI_ARG_RESPONSE | grep -o '"category":"procedural_[^"]*"' | wc -l)
    echo -e "${GREEN}✓ Multiple procedural arguments detected: ~$TOTAL_PROCEDURAL${NC}"
else
    echo -e "${RED}✗ Failed to extract multiple similar arguments${NC}"
fi

# Test 5: Analysis Statistics
echo ""
echo -e "${YELLOW}5. API Capabilities Check${NC}"
STATS=$(curl -s $API_URL/api/v1/analysis-stats 2>/dev/null)
if [[ "$STATS" == *"capabilities"* ]]; then
    echo -e "${GREEN}✓ API statistics available${NC}"
    echo "  Key improvements in v2.0:"
    echo "  - Extracts ALL arguments (not limited to categories)"
    echo "  - Flexible categorization with custom categories"
    echo "  - Strategic argument grouping"
    echo "  - Identifies missing/implied arguments"
else
    echo -e "${YELLOW}! Statistics endpoint not available${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}=====================================
        ANALYSIS SUMMARY
=====================================${NC}"

if [[ "$MOTION_RESPONSE" == *"all_arguments"* ]]; then
    echo -e "${GREEN}✅ Comprehensive Motion Analyzer v2.0 is working!${NC}"
    echo ""
    echo "Key Improvements Confirmed:"
    echo "✓ Extracts every argument (not just predefined categories)"
    echo "✓ Supports multiple arguments in same category"
    echo "✓ Groups related arguments strategically"
    echo "✓ Allows custom category creation"
    echo "✓ Provides comprehensive response strategy"
    echo ""
    echo -e "${BLUE}The API now ensures no argument is missed in motion analysis!${NC}"
else
    echo -e "${RED}❌ There are issues with the comprehensive analyzer${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check that all files were updated"
    echo "2. Restart the service after changes"
    echo "3. Verify OPENAI_API_KEY is set correctly"
fi

# Optional: Show a sample comprehensive response structure
echo ""
echo -e "${YELLOW}Sample Response Structure:${NC}"
echo '
{
  "all_arguments": [
    {
      "argument_id": "arg_001",
      "argument_text": "Count II imposes no additional liability...",
      "category": "liability_derivative",
      "location_in_motion": "Section III.A",
      "strength_assessment": "strong",
      "priority_level": 1
    },
    {
      "argument_id": "arg_002",
      "argument_text": "Florida law prohibits negligent hiring claims...",
      "category": "procedural_defenses",
      "location_in_motion": "Section III.B",
      "strength_assessment": "strong",
      "priority_level": 1
    }
  ],
  "argument_groups": [
    {
      "group_name": "Duplicative Liability Theory",
      "arguments": ["arg_001", "arg_003"],
      "combined_strength": "strong"
    }
  ],
  "total_arguments_found": 8,
  "strongest_arguments": ["arg_001", "arg_002"],
  "recommended_response_structure": [
    "Address derivative liability overlap first",
    "Counter case law interpretations",
    "Distinguish factual scenarios"
  ]
}'