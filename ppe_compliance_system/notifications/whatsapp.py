"""
notifications/whatsapp.py — WhatsApp Cloud API (Meta / official)

WHAT IT DOES
────────────
  When the AlertEngine fires, this class:
    1. Uploads the screenshot directly to WhatsApp's own media endpoint
       (no external image host needed)
    2. Sends a formatted violation message + the screenshot to every
       recipient in your list — effectively a group broadcast

SETUP (10 minutes)
──────────────────
  Step 1 — Meta Developer account
    a. Go to https://developers.facebook.com
    b. Create an App → choose "Business" type
    c. Add product: WhatsApp

  Step 2 — Get credentials (WhatsApp → API Setup in your app dashboard)
    a. Copy your  "Phone Number ID"
    b. Copy your  "Temporary Access Token" (lasts 24h for testing)
       OR generate a permanent token via System Users in Business Manager

  Step 3 — Add test recipients
    a. In WhatsApp → API Setup → "To" field, add each recipient's number
    b. Each person must send any message TO your test number once to activate

  Step 4 — Set environment variables
    (Windows)
      set WHATSAPP_API_TOKEN=EAAxxxxxxxx...
      set WHATSAPP_PHONE_NUMBER_ID=1234567890
      set WHATSAPP_RECIPIENTS=919876543210,919876543211
      set WHATSAPP_CAMERA_LABEL=Gate-2 Camera

    (Mac/Linux)
      export WHATSAPP_API_TOKEN=EAAxxxxxxxx...
      export WHATSAPP_PHONE_NUMBER_ID=1234567890
      export WHATSAPP_RECIPIENTS=919876543210,919876543211

  Recipients format: country code + number, NO + sign, NO spaces
    India example: 919876543210  (91 = country code, then 10-digit mobile)

NOTE ON GROUPS
──────────────
  The WhatsApp Cloud API does NOT support sending to existing personal
  WhatsApp groups.  The workaround used here: send to each supervisor's
  number individually.  All recipients get the same alert + screenshot
  at the same time — same effect as a group broadcast.
  (WhatsApp group creation via API requires WhatsApp Business Platform
   advanced access which needs Meta Business Verification.)

API REFERENCE
─────────────
  https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages
  https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media
"""

import base64
import json
import logging
import os
import time
from pathlib import Path
from typing import List, Optional

import requests

log = logging.getLogger(__name__)

GRAPH_API_VERSION = "v19.0"
GRAPH_BASE        = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class WhatsAppNotifier:
    """
    Sends PPE violation alerts via the official WhatsApp Cloud API.

    Args
    ----
    api_token       : Meta access token (env: WHATSAPP_API_TOKEN)
    phone_number_id : WhatsApp Business phone number ID (env: WHATSAPP_PHONE_NUMBER_ID)
    recipients      : List of phone numbers — country code + number, no '+' or spaces
                      e.g. ["919876543210", "919876543211"]
    cooldown_s      : Min seconds between messages to the same number (default 300)
    camera_label    : Shown in the alert message, e.g. "Gate-2 Camera"
    """

    def __init__(
        self,
        api_token:       str,
        phone_number_id: str,
        recipients:      List[str],
        cooldown_s:      int  = 300,
        camera_label:    str  = "Camera 1",
    ) -> None:
        self._token     = api_token
        self._phone_id  = phone_number_id
        self._recipients = recipients
        self._cooldown  = cooldown_s
        self._camera    = camera_label

        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type":  "application/json",
        }
        # Per-recipient last-sent timestamp for cooldown
        self._last_sent: dict[str, float] = {}

        if not recipients:
            log.warning("WhatsAppNotifier: no recipients — alerts will not be sent")
        else:
            log.info(
                f"WhatsAppNotifier ready  recipients={len(recipients)}  "
                f"cooldown={cooldown_s}s  camera='{camera_label}'"
            )

    # ── Public API ────────────────────────────────────────────────────────────

    def send_alert(self, alert, screenshot_path: Optional[Path] = None) -> bool:
        """
        Send a violation alert to all recipients.

        Parameters
        ----------
        alert           : Alert object from AlertEngine
        screenshot_path : Path to the saved screenshot PNG (optional)

        Returns True if at least one message delivered successfully.
        """
        if not self._recipients:
            return False

        # Check cooldown BEFORE uploading — don't waste an API upload call
        ready = [n for n in self._recipients if not self._on_cooldown(n)]
        if not ready:
            log.debug("All recipients on cooldown — alert skipped (no upload)")
            return False

        # Upload screenshot once, reuse media_id for all ready recipients
        media_id = self._upload_media(screenshot_path) if screenshot_path else None
        caption  = self._format_caption(alert)
        success  = False

        for number in ready:
            sent = self._send_to(number, caption, media_id)
            if sent:
                self._last_sent[number] = time.time()
                success = True

        return success

    def send_test(self) -> bool:
        """Send a plain text ping to verify credentials and recipient activation."""
        if not self._recipients:
            return False

        body = (
            f"✅ *PPE Monitor — System Online*\n"
            f"📍 {self._camera}\n"
            f"Monitoring active. Violation alerts will appear here."
        )
        success = False
        for number in self._recipients:
            if self._send_text(number, body):
                log.info(f"Test message delivered to {number}")
                success = True
        return success

    # ── Core send helpers ─────────────────────────────────────────────────────

    def _send_to(self, number: str, caption: str, media_id: Optional[str]) -> bool:
        """Send one message (image+caption or text-only) to one recipient."""
        try:
            if media_id:
                return self._send_image(number, media_id, caption)
            else:
                return self._send_text(number, caption)
        except Exception as exc:
            log.error(f"Send failed to {number}: {exc}")
            return False

    def _send_text(self, number: str, text: str) -> bool:
        """Send a plain text WhatsApp message."""
        payload = {
            "messaging_product": "whatsapp",
            "to":                number,
            "type":              "text",
            "text":              {"preview_url": False, "body": text},
        }
        return self._post_message(payload, number)

    def _send_image(self, number: str, media_id: str, caption: str) -> bool:
        """Send an image message using an already-uploaded media_id."""
        payload = {
            "messaging_product": "whatsapp",
            "to":                number,
            "type":              "image",
            "image":             {"id": media_id, "caption": caption},
        }
        return self._post_message(payload, number)

    def _post_message(self, payload: dict, number: str) -> bool:
        """POST to /messages endpoint, log result, return success bool."""
        url = f"{GRAPH_BASE}/{self._phone_id}/messages"
        try:
            resp = requests.post(
                url,
                headers=self._headers,
                data=json.dumps(payload),
                timeout=15,
            )
            if resp.status_code == 200:
                msg_id = resp.json().get("messages", [{}])[0].get("id", "?")
                log.info(f"WhatsApp delivered to {number}  msg_id={msg_id}")
                return True
            else:
                log.error(
                    f"WhatsApp API error {resp.status_code} for {number}: "
                    f"{resp.text[:300]}"
                )
                return False
        except requests.RequestException as exc:
            log.error(f"Network error sending to {number}: {exc}")
            return False

    # ── Media upload ──────────────────────────────────────────────────────────

    def _upload_media(self, path: Optional[Path]) -> Optional[str]:
        """
        Upload a local image file to WhatsApp's media endpoint.
        Returns the media_id string, or None on failure.

        WhatsApp stores the media and gives back an ID you reuse for each
        recipient — no external image host needed.
        """
        if not path or not Path(path).exists():
            return None

        url = f"{GRAPH_BASE}/{self._phone_id}/media"
        headers = {"Authorization": f"Bearer {self._token}"}   # no Content-Type — multipart

        try:
            with open(path, "rb") as f:
                files   = {"file": (Path(path).name, f, "image/png")}
                data    = {"messaging_product": "whatsapp", "type": "image/png"}
                resp    = requests.post(url, headers=headers, files=files, data=data, timeout=30)

            if resp.status_code == 200:
                media_id = resp.json().get("id")
                log.info(f"Screenshot uploaded to WhatsApp media  id={media_id}")
                return media_id
            else:
                log.warning(
                    f"Media upload failed {resp.status_code}: {resp.text[:200]} "
                    f"— alert will be sent without image"
                )
                return None

        except Exception as exc:
            log.warning(f"Media upload error: {exc} — alert will be sent without image")
            return None

    # ── Message formatting ────────────────────────────────────────────────────

    def _format_caption(self, alert) -> str:
        """Format the violation alert message body."""
        missing  = ", ".join(alert.missing_ppe).upper() if alert.missing_ppe else "UNKNOWN"
        emoji    = "🚨" if alert.severity == "CRITICAL" else "⚠️"

        return (
            f"{emoji} *PPE VIOLATION DETECTED*\n"
            f"{'─' * 30}\n"
            f"📍 *Location* : {self._camera}\n"
            f"❌ *Missing*  : {missing}\n"
            f"🕐 *Time*     : {alert.time_str}\n"
            f"⚡ *Severity* : {alert.severity}\n"
            f"{'─' * 30}\n"
            f"_Take immediate corrective action._"
        )

    # ── Cooldown ──────────────────────────────────────────────────────────────

    def _on_cooldown(self, number: str) -> bool:
        return (time.time() - self._last_sent.get(number, 0.0)) < self._cooldown


# ── Factory — build from environment variables ────────────────────────────────

def notifier_from_env(camera_label: str = "Camera 1") -> Optional["WhatsAppNotifier"]:
    """
    Build a WhatsAppNotifier from environment variables.
    Returns None (with a warning) if credentials are missing.

    Required env vars:
      WHATSAPP_API_TOKEN        — Meta access token
      WHATSAPP_PHONE_NUMBER_ID  — phone number ID from Meta dashboard
      WHATSAPP_RECIPIENTS       — comma-separated numbers (e.g. 919876543210,919876543211)

    Optional:
      WHATSAPP_COOLDOWN_S       — seconds between alerts per recipient (default 300)
      WHATSAPP_CAMERA_LABEL     — overrides the camera_label argument
    """
    token    = os.getenv("WHATSAPP_API_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    raw_rcpt = os.getenv("WHATSAPP_RECIPIENTS", "")

    if not token or not phone_id or not raw_rcpt:
        log.warning(
            "WhatsApp not configured — set WHATSAPP_API_TOKEN, "
            "WHATSAPP_PHONE_NUMBER_ID, and WHATSAPP_RECIPIENTS to enable alerts"
        )
        return None

    recipients = [r.strip() for r in raw_rcpt.split(",") if r.strip()]
    cooldown   = int(os.getenv("WHATSAPP_COOLDOWN_S", "300"))
    label      = os.getenv("WHATSAPP_CAMERA_LABEL", camera_label)

    return WhatsAppNotifier(
        api_token=token,
        phone_number_id=phone_id,
        recipients=recipients,
        cooldown_s=cooldown,
        camera_label=label,
    )
