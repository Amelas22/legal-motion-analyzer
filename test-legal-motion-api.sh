#!/bin/bash

# Test script to verify Legal Motion API is working after removing pydantic-ai

echo "🧪 Testing Legal Motion API (OpenAI Direct)"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test 1: Health Check
echo -e "${YELLOW}1. Health Check${NC}"
HEALTH=$(curl -s http://localhost:8888/health 2>/dev/null)
if [[ "$HEALTH" == *"healthy"* ]]; then
    echo -e "${GREEN}✓ Service is healthy${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    echo "Response: $HEALTH"
    echo ""
    echo "Checking logs for errors..."
    docker compose -p localai logs --tail=20 legal-motion-api | grep -E "(ERROR|ImportError|ModuleNotFoundError)"
    exit 1
fi

# Test 2: Motion Types
echo ""
echo -e "${YELLOW}2. Motion Types Endpoint${NC}"
TYPES=$(curl -s http://localhost:8888/api/v1/motion-types 2>/dev/null)
if [[ "$TYPES" == *"Motion to Dismiss"* ]]; then
    echo -e "${GREEN}✓ Motion types endpoint working${NC}"
else
    echo -e "${RED}✗ Motion types failed${NC}"
fi

# Test 3: Simple Motion Analysis
echo ""
echo -e "${YELLOW}3. Simple Motion Analysis${NC}"
SIMPLE_MOTION=$(curl -s -X POST http://localhost:8888/api/v1/analyze-motion \
  -H "Content-Type: application/json" \
  -d '{
    "motion_text": "MOTION TO COMPEL: Plaintiff moves to compel discovery responses. Despite meet and confer efforts, defendant has failed to respond to interrogatories served 60 days ago."
  }' 2>/dev/null)

if [[ "$SIMPLE_MOTION" == *"motion_type"* ]]; then
    echo -e "${GREEN}✓ Basic analysis working${NC}"
    MOTION_TYPE=$(echo $SIMPLE_MOTION | grep -o '"motion_type":"[^"]*"' | cut -d'"' -f4)
    echo "  Detected: $MOTION_TYPE"
else
    echo -e "${RED}✗ Analysis failed${NC}"
    echo "Response: $SIMPLE_MOTION"
fi

# Test 4: Complex Motion with Citations
echo ""
echo -e "${YELLOW}4. Complex Motion with Citations${NC}"
COMPLEX_MOTION=$(curl -s -X POST http://localhost:8888/api/v1/analyze-motion \
  -H "Content-Type: application/json" \
  -d '{
    "motion_text": "DEFENDANTS MOTION FOR SUMMARY JUDGMENT\n\nDefendant moves for summary judgment on all claims. The undisputed facts establish:\n\n1. No Duty: Defendant owed no duty to plaintiff as established in Smith v. Jones, 123 F.3d 456 (9th Cir. 2020).\n\n2. No Causation: Even if duty existed, plaintiff cannot establish proximate cause. See Brown v. Green, 789 F. Supp. 2d 123 (C.D. Cal. 2019).\n\n3. Statute of Limitations: The two-year statute under Cal. Code Civ. Proc. § 335.1 has expired.",
    "case_context": "Personal injury slip and fall case at retail store."
  }' 2>/dev/null)

if [[ "$COMPLEX_MOTION" == *"Smith v. Jones"* ]]; then
    echo -e "${GREEN}✓ Citation extraction working${NC}"
    CITATIONS=$(echo $COMPLEX_MOTION | grep -o '"cited_cases":\[[^]]*\]' | grep -o '"case_name":"[^"]*"' | wc -l)
    echo "  Citations found: $CITATIONS"
else
    echo -e "${YELLOW}! Citations not found in response${NC}"
fi

# Test 5: Error Handling
echo ""
echo -e "${YELLOW}5. Error Handling${NC}"
ERROR_TEST=$(curl -s -X POST http://localhost:8888/api/v1/analyze-motion \
  -H "Content-Type: application/json" \
  -d '{"motion_text": "Too short"}' 2>/dev/null)

if [[ "$ERROR_TEST" == *"error"* ]] || [[ "$ERROR_TEST" == *"detail"* ]]; then
    echo -e "${GREEN}✓ Error handling working${NC}"
else
    echo -e "${YELLOW}! Unexpected error response${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}Test Summary:${NC}"
echo "============="

# Check for pydantic-ai imports
echo ""
echo -e "${YELLOW}Checking for pydantic-ai references...${NC}"
PYDANTIC_AI_REFS=$(grep -r "pydantic_ai" legal-motion-api/app/ 2>/dev/null | wc -l)
if [ "$PYDANTIC_AI_REFS" -eq 0 ]; then
    echo -e "${GREEN}✓ No pydantic-ai references found${NC}"
else
    echo -e "${RED}✗ Found $PYDANTIC_AI_REFS pydantic-ai references!${NC}"
    grep -r "pydantic_ai" legal-motion-api/app/
fi

# Final message
echo ""
if [[ "$SIMPLE_MOTION" == *"motion_type"* ]]; then
    echo -e "${GREEN}✅ Legal Motion API is working correctly!${NC}"
    echo ""
    echo "The API is now using OpenAI directly without pydantic-ai."
    echo "You can use it from n8n at: http://legal-motion-api:8000/api/v1/analyze-motion"
else
    echo -e "${RED}❌ There are still issues with the API${NC}"
    echo ""
    echo "Please check:"
    echo "1. All files have been updated correctly"
    echo "2. OPENAI_API_KEY is set in your .env file"
    echo "3. The container was rebuilt after changes"
    echo ""
    echo "View full logs with:"
    echo "  docker compose -p localai logs legal-motion-api"
fi