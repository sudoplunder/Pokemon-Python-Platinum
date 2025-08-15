@echo off
REM Launch the game with debug output disabled.
REM The settings system defaults to debug=false; this batch ensures it stays off.
REM If the settings file exists with debug=true, it will flip it to false before launching.

powershell -NoLogo -NoProfile -Command "try { $p = Join-Path $HOME '.platinum_settings.json'; if(Test-Path $p){ $json = Get-Content $p -Raw | ConvertFrom-Json; if($json.debug -ne $false){ $json.debug = $false; $json | ConvertTo-Json -Depth 5 | Set-Content $p } } } catch { }"

python -m platinum
