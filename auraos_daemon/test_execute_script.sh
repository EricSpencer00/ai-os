# test_execute_script.sh
# Test suite for AuraOS /execute_script endpoint
# Usage: sh test_execute_script.sh

API_URL="http://localhost:5050/execute_script"

run_test() {
  desc="$1"
  data="$2"
  echo "\n=== $desc ==="
  curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d "$data" | jq
}

# 1. Safe shell script
data1='{ "script": "echo Hello, AuraOS!", "context": {} }'
run_test "Safe shell script (should execute)" "$data1"

# 2. Safe Python script
data2='{ "script": "python3 -c \"print(42)\"", "context": {} }'
run_test "Safe Python script (should execute)" "$data2"

# 3. Malicious shell script
data3='{ "script": "rm -rf /", "context": {} }'
run_test "Malicious shell script (should be blocked)" "$data3"

# 4. Malicious Python script
data4='{ "script": "python3 -c \"import os; os.system(\\\"rm -rf /\\\")\"", "context": {} }'
run_test "Malicious Python script (should be blocked)" "$data4"

# 5. Empty script
data5='{ "script": "", "context": {} }'
run_test "Empty script (should return error)" "$data5"

# 6. Script with display context
data6='{ "script": "echo $DISPLAY", "context": { "display": ":0" } }'
run_test "Script with display context (should execute and show :0)" "$data6"

# 7. Script with forbidden keyword in a comment
data7='{ "script": "echo safe # rm -rf /", "context": {} }'
run_test "Script with forbidden keyword in comment (should execute)" "$data7"
