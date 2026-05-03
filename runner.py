# runner.py
# One-shot entry point for manual testing.
# Usage: python runner.py [bbl|superrich|combined]

import sys
from dotenv import load_dotenv
import os

load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("GROUP_ID") or os.getenv("LINE_GROUP_ID")

print("🔍 Verifying environment variables...")
missing = []
if not LINE_CHANNEL_ACCESS_TOKEN:
    missing.append("LINE_CHANNEL_ACCESS_TOKEN")
if not GROUP_ID:
    missing.append("GROUP_ID / LINE_GROUP_ID")

if missing:
    print(f"❌ Missing required environment variables: {', '.join(missing)}")
    print("🛑 Aborting run.")
    exit(1)

print("✅ All required env variables found.")

msg_type = sys.argv[1] if len(sys.argv) > 1 else None
if msg_type not in ("bbl", "superrich", "combined"):
    print("❌ Usage: python runner.py [bbl|superrich|combined]")
    exit(1)

from app import send_bbl, send_superrich, send_combined

print(f"🚀 Running send_{msg_type}() ...\n")
try:
    if msg_type == "bbl":
        send_bbl()
    elif msg_type == "superrich":
        send_superrich()
    elif msg_type == "combined":
        send_combined()
    print(f"\n✅ Done — type={msg_type}")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
