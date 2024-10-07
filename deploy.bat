@echo off

set RIME=%APPDATA%\Rime
set RIME_BASE=D:\Rime
for /d %%d in ("%RIME_BASE%\weasel-*") do set RIME_BIN=%%d

copy rytphings.*.yaml %RIME%
"%RIME_BIN%\WeaselDeployer.exe" /deploy

