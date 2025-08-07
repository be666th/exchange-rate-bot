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
    # ✅ ยังสร้าง fallback ไว้ให้แน่ใจว่า Artifact Upload ได้
    with open("fallback.txt", "w", encoding="utf-8") as f:
        f.write("❌ Missing env vars: " + ", ".join(missing))
    exit(1)

print("✅ All required env variables found.")
print("🚀 Running capture_and_send() ...\n")


def create_fallback_file(reason: str = "No debug files generated"):
    try:
        with open("fallback.txt", "w", encoding="utf-8") as f:
            f.write(f"⚠️ Fallback created: {reason}\n")
        print("✅ fallback.txt created.")
    except Exception as e:
        print(f"❌ Failed to create fallback.txt: {e}")


try:
    capture_and_send()
except Exception as e:
    print(f"❌ Error occurred in capture_and_send(): {e}")
    create_fallback_file(reason=f"Exception: {e}")
finally:
    html_exists = os.path.exists("page_source.html")
    png_exists = os.path.exists("table_not_found.png")

    if not html_exists and not png_exists:
        create_fallback_file(reason="Missing both page_source.html and table_not_found.png")
    else:
        print("✅ At least one debug file exists. No fallback needed.")
