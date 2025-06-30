#!/bin/bash

# Install Chrome dependencies
apt-get update
apt-get install -y wget unzip xvfb libxi6 libgconf-2-4

# Install Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt install -y ./google-chrome-stable_current_amd64.deb

# Install ChromeDriver
wget https://chromedriver.storage.googleapis.com/122.0.6261.69/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
mv chromedriver /usr/local/bin/
chmod +x /usr/local/bin/chromedriver

# Start Xvfb
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# Run app
python app.py
