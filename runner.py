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


- name: Run Screenshot + LINE Notify
  run: python runner.py
  env:
    CLOUDINARY_CLOUD_NAME: ${{ secrets.CLOUDINARY_CLOUD_NAME }}
    CLOUDINARY_API_KEY: ${{ secrets.CLOUDINARY_API_KEY }}
    CLOUDINARY_API_SECRET: ${{ secrets.CLOUDINARY_API_SECRET }}
    LINE_CHANNEL_ACCESS_TOKEN: ${{ secrets.LINE_CHANNEL_ACCESS_TOKEN }}
    LINE_USER_ID: ${{ secrets.LINE_USER_ID }}

