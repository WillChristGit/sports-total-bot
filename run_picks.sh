#!/bin/bash
# SportsTotalBot - Cron-compatible runner
export PATH=/root/SportsTotalBot/venv_linux/bin:/c/Users/GFIWill/bin:/mingw64/bin:/usr/local/bin:/usr/bin:/bin:/mingw64/bin:/usr/bin:/c/Users/GFIWill/bin:/c/windows/system32:/c/windows:/c/windows/System32/Wbem:/c/windows/System32/WindowsPowerShell/v1.0:/c/windows/System32/OpenSSH:/c/Program Files/HP/HP One Agent:/c/WINDOWS/system32:/c/WINDOWS:/c/WINDOWS/System32/Wbem:/c/WINDOWS/System32/WindowsPowerShell/v1.0:/c/WINDOWS/System32/OpenSSH:/cmd:/c/Users/GFIWill/AppData/Local/Programs/Python/Python312/Scripts:/c/Users/GFIWill/AppData/Local/Programs/Python/Python312:/c/Users/GFIWill/AppData/Local/Programs/Python/Launcher:/c/Users/GFIWill/AppData/Local/Microsoft/WindowsApps:/c/Users/GFIWill/AppData/Local/Microsoft/WinGet/Packages/Anthropic.ClaudeCode_Microsoft.Winget.Source_8wekyb3d8bbwe:/usr/bin/vendor_perl:/usr/bin/core_perl
cd /root/SportsTotalBot
echo Tue, Feb 3, 2026 8:51:33 AM - Running SportsTotalBot... >> logs/cron.log
/root/SportsTotalBot/venv_linux/bin/python main_v2.py >> logs/cron.log 2>&1
echo Tue, Feb 3, 2026 8:51:34 AM - Done. >> logs/cron.log
