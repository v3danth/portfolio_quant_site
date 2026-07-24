#!/bin/bash
# http://127.0.0.1:8000/api/v1/users
# http://127.0.0.1:8000/api/v1/stocks
# http://127.0.0.1:8000/api/v1/stocks/149
# http://127.0.0.1:8000/api/v1/stocks/149/prices
# http://127.0.0.1:8000/api/v1/stocks/149/quote
# http://127.0.0.1:8000/api/v1/portfolios?userId=1
USER_ID=${1:-1}
PORTFOLIO_NAME=${2:-"My Portfolio"}
API_URL=${3:-"http://127.0.0.1:8000"}

endpoint="$API_URL/api/v1/portfolios"
body=$(cat <<EOF
{
  "user_id": $USER_ID,
  "name": "$PORTFOLIO_NAME"
}
EOF
)

echo "Creating portfolio: $PORTFOLIO_NAME for user $USER_ID"
echo "Endpoint: $endpoint"
echo "Body: $body"
echo ""

curl -X POST "$endpoint" \
  -H "Content-Type: application/json" \
  -d "$body"

echo ""
