@echo off
REM Windows 启动脚本，确保使用 UTF-8 编码
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
python "%~dp0src\index.py"
