# runner.py

from dotenv import load_dotenv
import os
from app import capture_and_send

# ✅ Load environment variables from .env
load_dotenv()

# ✅ Check critical env variables before running
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")

print("🔍 Verifying environment variables...")
missing = []

if not LINE_CHANNEL_ACCESS_TOKEN:
    missing.append("LINE_CHANNEL_ACCESS_TOKEN")
if not GROUP_ID:
    missing.append("GROUP_ID")
if not CLOUDINARY_CLOUD_NAME:
    missing.append("CLOUDINARY_CLOUD_NAME")

if missing:
    print(f"❌ Missing required environment variables: {', '.join(missing)}")
    print("🛑 Aborting run.")
else:
    print("✅ All required env variables found.")
    print("🚀 Running capture_and_send() ...\n")
    capture_and_send()

