#!/bin/bash
Xvfb :99 -screen 0 1280x800x16 &
export DISPLAY=:99
python main.py
