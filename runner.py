from app import capture_and_send
capture_and_send()
from dotenv import load_dotenv
load_dotenv()

import os
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

if __name__ == "__main__":
    capture_and_send()




