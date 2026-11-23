#!/usr/bin/env bash
# Sends a fake "customer message" to your n8n workflow — exactly the shape
# WhatsApp sends — so you can test without touching your phone.
#
# Usage:
#   ./scripts/send-test-message.sh <your-n8n-webhook-url> <phone-number> "<message>" [phone-number-id]
#
# Example:
#   ./scripts/send-test-message.sh https://you.app.n8n.cloud/webhook/whatsapp 923001234567 "Hi, what are your hours?" 109876543210
#
# • phone-number: a WhatsApp number in international format, digits only. The AI's
#   reply is really sent there, so use your own number (and while you're on
#   Meta's free test number, it must be in your allowed "To" list).
# • phone-number-id: your WhatsApp "Phone number ID" from Meta → WhatsApp → API Setup.
#   Needed for the reply to be sent; without it you can still watch the
#   execution in n8n.
set -euo pipefail

URL="${1:?Give your n8n webhook URL, e.g. https://you.app.n8n.cloud/webhook/whatsapp}"
FROM="${2:?Give a phone number, e.g. 923001234567}"
TEXT="${3:-Hi! What are your opening hours?}"
PHONE_ID="${4:-000000000000000}"
MSG_ID="wamid.test$(date +%s)$RANDOM"
NOW="$(date +%s)"

# Build the JSON safely (handles quotes in your message).
BODY=$(python3 - "$FROM" "$TEXT" "$PHONE_ID" "$MSG_ID" "$NOW" <<'PY'
import json, sys
frm, text, phone_id, msg_id, now = sys.argv[1:]
print(json.dumps({
  "object": "whatsapp_business_account",
  "entry": [{"id": "TEST", "changes": [{"field": "messages", "value": {
    "messaging_product": "whatsapp",
    "metadata": {"display_phone_number": "TEST", "phone_number_id": phone_id},
    "contacts": [{"profile": {"name": "Test Customer"}, "wa_id": frm}],
    "messages": [{"from": frm, "id": msg_id, "timestamp": now, "type": "text", "text": {"body": text}}]
  }}]}]
}))
PY
)

echo "→ Sending to $URL"
curl -sS -X POST "$URL" -H 'Content-Type: application/json' -d "$BODY" -w '\n← HTTP %{http_code}\n'
echo "Now open n8n → Executions to watch it run."
