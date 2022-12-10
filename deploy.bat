@echo off

set RIME=%APPDATA%\Rime
set RIME_BIN=D:\Rime\weasel-0.9.30

copy rytphings.*.yaml %RIME%
"%RIME_BIN%\WeaselDeployer.exe" /deploy
