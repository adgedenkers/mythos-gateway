#!/bin/bash
# debug_check.sh
# Quickly check all Mythos Gateway debug endpoints

API_KEY="0000000000123456789"
BASE_URL="http://localhost:8001/debug"

echo "=== 1. Last 50 lines of Mythos Gateway journal ==="
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/journal"
echo -e "\n\n"

echo "=== 2. Sanitized environment variables ==="
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/env" | python3 -m json.tool
echo -e "\n\n"

echo "=== 3. Python dependencies in virtualenv ==="
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/dependencies"
echo -e "\n\n"

echo "=== 4. Disk usage ==="
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/disk"
echo -e "\n\n"

echo "=== 5. Ping Neo4j database ==="
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/ping-db" | python3 -m json.tool
echo -e "\n\n"

echo "=== 6. System status ==="
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/status" | python3 -m json.tool
echo -e "\n\n"
