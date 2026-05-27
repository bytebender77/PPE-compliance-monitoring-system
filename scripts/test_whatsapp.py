"""
Quick WhatsApp API test — run this standalone to verify credentials.
Usage:  python scripts/test_whatsapp.py
"""
import os, sys, json, requests

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

TOKEN    = os.getenv("WHATSAPP_API_TOKEN", "")
PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
TO       = os.getenv("WHATSAPP_RECIPIENTS", "").split(",")[0].strip()

print("── WhatsApp API Diagnostic ──────────────────────")
print(f"Token     : {'SET (' + TOKEN[:12] + '...)' if TOKEN else 'MISSING ❌'}")
print(f"Phone ID  : {PHONE_ID if PHONE_ID else 'MISSING ❌'}")
print(f"Recipient : {TO if TO else 'MISSING ❌'}")
print()

if not TOKEN or not PHONE_ID or not TO:
    print("ERROR: Missing env vars. Set them first:")
    print("  export WHATSAPP_API_TOKEN=...")
    print("  export WHATSAPP_PHONE_NUMBER_ID=...")
    print("  export WHATSAPP_RECIPIENTS=91XXXXXXXXXX")
    sys.exit(1)

# ── Test 1: verify token is valid ─────────────────────────────────────────────
print("Test 1: Checking token validity...")
r = requests.get(
    f"https://graph.facebook.com/v19.0/{PHONE_ID}",
    headers={"Authorization": f"Bearer {TOKEN}"},
    timeout=10,
)
print(f"  Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"  Phone number: {data.get('display_phone_number', '?')}")
    print(f"  ✅ Token valid")
else:
    print(f"  ❌ Token error: {r.text[:300]}")
    sys.exit(1)

# ── Test 2: send a plain text message ─────────────────────────────────────────
print(f"\nTest 2: Sending text message to {TO}...")
payload = {
    "messaging_product": "whatsapp",
    "to": TO,
    "type": "text",
    "text": {"body": "✅ PPE Monitor test message — WhatsApp API working!"}
}
r = requests.post(
    f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    data=json.dumps(payload),
    timeout=15,
)
print(f"  Status: {r.status_code}")
print(f"  Response: {r.text[:400]}")
if r.status_code == 200:
    print(f"  ✅ Message sent! Check your WhatsApp.")
else:
    print(f"  ❌ Send failed — see error above")
