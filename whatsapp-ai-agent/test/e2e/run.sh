#!/usr/bin/env bash
# Runs the real n8n workflow end-to-end against local mock APIs (no accounts,
# no API keys, nothing leaves your machine).
#
# Needs: Node.js 24+, openssl, and n8n installed (npm i -g n8n, or set N8N_BIN).
#   ./test/e2e/run.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK_DIR:-$(mktemp -d)}"
N8N_BIN="${N8N_BIN:-n8n}"
PROXY_PORT=8899
CONTROL_PORT=8898
mkdir -p "$WORK"
echo "Working directory: $WORK"

# 1. A throw-away TLS certificate so n8n trusts the mock "api.anthropic.com" etc.
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$WORK/key.pem" -out "$WORK/cert.pem" -days 2 \
  -subj "/CN=local-mock" \
  -addext "subjectAltName=DNS:api.anthropic.com,DNS:graph.facebook.com,DNS:www.googleapis.com,DNS:sheets.googleapis.com,DNS:oauth2.googleapis.com" \
  -addext "basicConstraints=critical,CA:TRUE" 2>/dev/null

# 2. n8n settings: isolated data folder, and send all outgoing HTTPS through the mock.
export N8N_USER_FOLDER="$WORK/n8n" N8N_PORT=5678 N8N_LISTEN_ADDRESS=127.0.0.1
export N8N_ENCRYPTION_KEY=e2e-test-key N8N_DIAGNOSTICS_ENABLED=false N8N_VERSION_NOTIFICATIONS_ENABLED=false
export GENERIC_TIMEZONE=Asia/Karachi NODE_EXTRA_CA_CERTS="$WORK/cert.pem"
MOCK="http://127.0.0.1:$PROXY_PORT"
export HTTPS_PROXY=$MOCK https_proxy=$MOCK HTTP_PROXY=$MOCK http_proxy=$MOCK
export npm_config_https_proxy=$MOCK npm_config_http_proxy=$MOCK npm_config_proxy=$MOCK
export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1 npm_config_no_proxy=localhost,127.0.0.1
unset npm_config_noproxy GLOBAL_AGENT_HTTPS_PROXY || true

cleanup() { kill "${N8N_PID:-}" "${MOCK_PID:-}" 2>/dev/null || true; }
trap cleanup EXIT

node "$HERE/mock-apis.mjs" $PROXY_PORT $CONTROL_PORT "$WORK" > "$WORK/mock.log" 2>&1 &
MOCK_PID=$!

# 3. Import the workflow with fake credentials and publish it.
node "$HERE/prepare.mjs" "$WORK"
"$N8N_BIN" import:credentials --input="$WORK/credentials.json" > "$WORK/import.log" 2>&1
"$N8N_BIN" import:workflow --input="$WORK/workflow.json" >> "$WORK/import.log" 2>&1
"$N8N_BIN" publish:workflow --id=waAgentTest00001 >> "$WORK/import.log" 2>&1

# 4. Start n8n and wait for it.
"$N8N_BIN" start > "$WORK/n8n.log" 2>&1 &
N8N_PID=$!
for _ in $(seq 1 90); do
  curl -sf http://localhost:5678/healthz > /dev/null 2>&1 && break
  sleep 1
done
sleep 3

# 5. Run the scenarios.
node "$HERE/run-e2e.mjs"
