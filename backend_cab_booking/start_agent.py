"""
Ashad Voice Agent — Automated Tunnel & Bot Launcher
Automatically starts Cloudflare tunnel, discovers the live HTTPS URL,
updates Telnyx TeXML Application webhook, and starts the Pipecat voice bot.
Zero manual configuration or URL copying needed!
"""

import os
import sys
import time
import socket
import re
import subprocess
import requests
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# 1. Force IPv4 resolution to prevent Windows IPv6 handshake timeouts
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

load_dotenv(override=True)

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
# Both of these used to be hardcoded here, which meant pointing this launcher at a
# different Telnyx TeXML Application or phone number required editing source code.
# Set them in .env instead.
TELNYX_APP_ID = os.getenv("TELNYX_APP_ID", "")
TELNYX_PHONE_NUMBER = os.getenv("TELNYX_PHONE_NUMBER", "")


def update_telnyx_webhook(public_url: str):
    """Updates Telnyx TeXML Application voice_url via REST API."""
    if not TELNYX_API_KEY:
        print("[!] Warning: TELNYX_API_KEY not found in .env")
        return False
    if not TELNYX_APP_ID:
        print("[!] Warning: TELNYX_APP_ID not found in .env — cannot update the webhook")
        return False

    url = f"https://api.telnyx.com/v2/texml_applications/{TELNYX_APP_ID}"
    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "voice_url": public_url,
        "voice_method": "post"
    }

    try:
        r = requests.patch(url, headers=headers, json=payload, timeout=10)
        if r.status_code == 200:
            print(f"[✓] Telnyx Webhook successfully updated to: {public_url}")
            return True
        else:
            print(f"[!] Failed to update Telnyx (HTTP {r.status_code}): {r.text}")
            return False
    except Exception as e:
        print(f"[!] Error updating Telnyx: {e}")
        return False


def start_tunnel_and_get_url():
    """Starts cloudflared tunnel and captures the live trycloudflare.com URL."""
    cf_exe = os.path.join(os.path.dirname(__file__), "cloudflared.exe")
    if not os.path.exists(cf_exe):
        cf_exe = "cloudflared"

    print("[*] Starting Cloudflare Tunnel...")
    proc = subprocess.Popen(
        [cf_exe, "tunnel", "--url", "http://localhost:7860"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )

    url = None
    start_time = time.time()
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Read output line by line until we find the public URL
    while time.time() - start_time < 20:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            match = url_pattern.search(line)
            if match:
                url = match.group(0)
                break

    if not url:
        print("[!] Could not auto-detect Cloudflare URL within 20 seconds.")
        return None, proc

    domain = url.replace("https://", "").strip()
    print(f"[✓] Cloudflare Tunnel established: {url}")
    return domain, proc


def main():
    print("=" * 60)
    print("   ASHAD VOICE AGENT — AUTO LAUNCHER")
    print("=" * 60)

    # 1. Start tunnel and get public domain
    domain, tunnel_proc = start_tunnel_and_get_url()
    if not domain:
        print("[!] Exiting due to tunnel error.")
        sys.exit(1)

    # 2. Update Telnyx webhook automatically
    public_url = f"https://{domain}"
    update_telnyx_webhook(public_url)

    # 3. Start the Pipecat bot with the configured domain
    print(f"[*] Starting Pipecat Voice Bot for domain: {domain}")
    print("=" * 60)
    if TELNYX_PHONE_NUMBER:
        print(f"📞 READY TO RECEIVE CALLS ON {TELNYX_PHONE_NUMBER}")
    else:
        print("📞 READY TO RECEIVE CALLS (set TELNYX_PHONE_NUMBER in .env to show it here)")
    print("=" * 60)

    try:
        # Run bot.py with the detected domain
        sys.argv = ["bot.py", "-t", "telnyx", "-x", domain]
        from pipecat.runner.run import main as pipecat_main
        pipecat_main()
    finally:
        if tunnel_proc:
            print("[*] Terminating tunnel...")
            tunnel_proc.terminate()


if __name__ == "__main__":
    main()
