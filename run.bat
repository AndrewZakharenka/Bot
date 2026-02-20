@echo off
start "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
timeout /t 2 /nobreak >nul
start "" "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" voice_bot\ui.py
