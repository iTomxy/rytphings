@echo off

@REM Configure the behavour of Ctrl + Space for version >= 0.16.2
@REM https://github.com/rime/weasel/releases/tag/0.16.2

set RIME_BASE=%LOCALAPPDATA%\Programs\Rime
for /d %%d in ("%RIME_BASE%\*") do set RIME_BIN=%%d

echo to disable/enable IME
"%RIME_BIN%\WeaselSetup.exe" /toggleime

echo to switch ascii mode
@REM "%RIME_BIN%\WeaselSetup.exe" /toggleascii

