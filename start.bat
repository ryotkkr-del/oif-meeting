@echo off
cd /d "%~dp0"
if not exist .venv (
  echo .venv がありません。READMEのセットアップを先に実行してください。
  pause
  exit /b 1
)
call .venv\Scripts\activate
python app.py
