@echo off
echo ============================================
echo   Building TheFork Looker .exe
echo ============================================
cd /d "%~dp0\.."
pip install paramiko pyinstaller
pyinstaller build\thefork_looker.spec --distpath dist --workpath build\temp --clean -y
echo.
echo Done! Output: dist\TheForkLooker.exe
pause
