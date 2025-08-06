@echo off
cd /d %~dp0
echo 🔄 Switching to main branch...
git checkout main

echo 🔄 Pulling latest changes...
git pull origin main

echo ✅ Synced with remote.
pause
