@echo off

set RIME=%APPDATA%\Rime
set RIME_BIN=D:\Rime
for /d %%d in ("%RIME_BASE%\*") do set RIME_BIN=%%d

copy rytphings.*.yaml %RIME%
"%RIME_BIN%\WeaselDeployer.exe" /deploy

