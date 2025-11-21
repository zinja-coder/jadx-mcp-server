#!/usr/bin/env bash

###
# This is the test script to test the working on Jadx MCP Server.
# 1. Start the jadx
# 2. Load DVAC apk into jadx -> https://github.com/zinja-coder/Damn-Vulnerable-Android-Components/
# 3. Start the jadx on port 8652 (or your choice or the leave it default 8650)
# 4. Start the jadx mcp server in http stream mode on port 9000 
# 5. Command for step 4. -> `uv run jadx_mcp_server.py --http --port 9000 --jadx--port 8652`
###

set -euo pipefail

MCP_URL="${MCP_URL:-http://127.0.0.1:9000/mcp}"
ACCEPT_HDR="application/json, text/event-stream"
CONTENT_HDR="application/json"

# Helper: extract data: JSON items from SSE and drop [DONE]
sse_to_json() {
  grep '^data: ' | sed 's/^data: //' | grep -v '^\[DONE\]$'
}

# 1) initialize, capture session id header
echo "== initialize =="
INIT_RESP_HEADERS=$(mktemp)
curl -i -s -X POST "$MCP_URL" \
  -H "Content-Type: $CONTENT_HDR" \
  -H "Accept: $ACCEPT_HDR" \
  -d '{
    "jsonrpc":"2.0",
    "method":"initialize",
    "params":{
      "protocolVersion":"2024-11-05",
      "capabilities":{},
      "clientInfo":{"name":"curl-automation","version":"1.0.0"}
    },
    "id":1
  }' | tee "$INIT_RESP_HEADERS" >/dev/null

SESSION_ID=$(awk -F': ' 'BEGIN{IGNORECASE=1} /^mcp-session-id:/ {print $2}' "$INIT_RESP_HEADERS" | tr -d '\r')
if [[ -z "${SESSION_ID:-}" ]]; then
  echo "Failed to obtain MCP-Session-Id header" >&2
  exit 1
fi
echo "Session: $SESSION_ID"

# 2) send notifications/initialized (no output expected)
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: $CONTENT_HDR" \
  -H "Accept: $ACCEPT_HDR" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' >/dev/null

# Optional: discover tools dynamically
echo "== tools/list =="
TOOLS_JSON=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: $CONTENT_HDR" \
  -H "Accept: $ACCEPT_HDR" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}' \
  | sse_to_json | tail -n 1)
echo "$TOOLS_JSON" | jq -r '.result.tools[].name'

# Helper: call a tool with a JSON arguments object string
call_tool() {
  local name="$1"
  local args_json="$2"   # must be a valid JSON object string
  local id="${3:-1000}"

  curl -s -X POST "$MCP_URL" \
    -H "Content-Type: $CONTENT_HDR" \
    -H "Accept: $ACCEPT_HDR" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    -d "{
      \"jsonrpc\":\"2.0\",
      \"method\":\"tools/call\",
      \"params\":{
        \"name\":\"$name\",
        \"arguments\":$args_json
      },
      \"id\":$id
    }" \
  | sse_to_json
}

echo "== Run selected tools =="

# 3) fetch_current_class (no args)
echo "--- fetch_current_class ---"
call_tool "fetch_current_class" '{}' 10 | jq -r '.result | .content?, .name? // . | tostring'

# 4) get_selected_text (no args)
echo "--- get_selected_text ---"
call_tool "get_selected_text" '{}' 11 | jq -r '.result | .selectedText // .'

# 5) get_android_manifest (no args)
echo "--- get_android_manifest ---"
call_tool "get_android_manifest" '{}' 12 | jq -r '.result.content'

# 6) get_main_activity_class (no args)
echo "--- get_main_activity_class ---"
call_tool "get_main_activity_class" '{}' 13 | jq -r '.result.name, .result.content'

# 7) get_all_classes (supports offset/count)
echo "--- get_all_classes (offset=0,count=50) ---"
call_tool "get_all_classes" '{"offset":0,"count":50}' 14 | jq -r '.result.items[]? // .result.classes[]? // .'

# 8) get_class_source
echo "--- get_class_source ---"
call_tool "get_class_source" '{"class_name":"com.zin.dvac.AuthActivity"}' 15 | jq -r '.result // .error?.message // .'

# 8.2) get_class_source -> innerclass
echo "-- get_class_source ---"
call_tool "get_class_source" '{"class_name":"androidx.activity.OnBackPressedDispatcher$addCancellableCallback$1"}' 16 | jq -r '.result // .error?.message // .'

# 9) get_method_by_name
echo "--- get_method_by_name ---"
call_tool "get_method_by_name" '{"class_name":"com.zin.dvac.AuthActivity","method_name":"onCreate"}' 17 | jq -r '.result.code // .error?.message // .'

# 10) search_method_by_name
echo "--- search_method_by_name ---"
call_tool "search_method_by_name" '{"method_name":"onCreate"}' 18 | jq -r '.result[]? // .result.matches[]? // .'

# 11) get_methods_of_class
echo "--- get_methods_of_class ---"
call_tool "get_methods_of_class" '{"class_name":"com.zin.dvac.AuthActivity"}' 19 | jq -r '.result[]? // .'

# 12) get_fields_of_class
echo "--- get_fields_of_class ---"
call_tool "get_fields_of_class" '{"class_name":"com.zin.dvac.DatabaseHelper"}' 20 | jq -r '.result[]? // .'

# 13) get_smali_of_class
echo "--- get_smali_of_class ---"
call_tool "get_smali_of_class" '{"class_name":"com.zin.dvac.AuthActivity"}' 21 | jq -r '.result // .'

# 14) get_strings (pagination)
echo "--- get_strings (offset=0,count=100) ---"
call_tool "get_strings" '{"offset":0,"count":100}' 22 | jq -r '
  .result.items? // .result.strings? // .result.file? // .result // .
'

# 15) get_all_resource_file_names
echo "--- get_all_resource_file_names ---"
call_tool "get_all_resource_file_names" '{}' 23 | jq -r '.result.files[]? // .'

# 16) get_resource_file
echo "--- get_resource_file ---"
call_tool "get_resource_file" '{"resource_name":"res/xml/network_security_config.xml"}' 24 | jq -r '.result.file.content // .'

# 17) get_main_application_classes_names
echo "--- get_main_application_classes_names ---"
call_tool "get_main_application_classes_names" '{}' 25 | jq -r '.result[]? // .result.classes[]?.name // .'

# 18) get_main_application_classes_code (pagination)
echo "--- get_main_application_classes_code (offset=0,count=3) ---"
call_tool "get_main_application_classes_code" '{"offset":0,"count":3}' 26 | jq -r '.result[]? // .result.classes[]?.name, .result.classes[]?.content'

# 19) rename operations (use with care; examples commented)
#echo "--- rename_class ---"
#call_tool "rename_class"  '{"class_name":"com.zin.dvac.AuthActivity","new_name":"WebViewActivity"}' 27 | jq
#echo "--- rename_method ---"
#call_tool "rename_method" '{"method_name":"com.zin.dvac.AuthActivity.onCreate","new_name":"initializeWebView"}' 28 | jq
#echo "--- rename_field ---"
#call_tool "rename_field"  '{"class_name":"com.zin.dvac.LoginActivity","field_name":"editTextLoginPassword","new_name":"passwordInputField"}' 29 | jq

# 20) get stack frames from debugger
echo "--- debug_get_stack_frames ---"
call_tool "debug_get_stack_frames" '{}' 30 | jq -r '.result[]? // .'

# 22) get threads from debugger
echo "--- debug_get_threads ---"
call_tool "debug_get_threads" '{}' 31 | jq -r '.result[]? // .'

# 23) get debugger variables from debugger
echo "--- debug_get_variables ---"
call_tool "debug_get_variables" '{}' 32 | jq -r '.result[]? // .'

#24) get list of classes that contains specific keyword
echo "--- search_classes_by_keyword ---"
call_tool "search_classes_by_keyword" '{"search_term":"login","offset":0,"count":5}' 33 | jq -r '.result[]? // .'


echo "== done =="
