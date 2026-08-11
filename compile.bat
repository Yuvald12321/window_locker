call ".venv\Scripts\pyinstaller.exe" --onefile --noconsole --icon "logo.ico" -n "window locker" main.py
rd /S /Q "build"