@echo off
rem ASCII-only launcher. All logic (and Chinese text) lives in run_task.ps1
rem to avoid cmd.exe codepage parsing bugs with chcp 65001 + CJK text.
rem
rem Usage 1: double-click this file, then paste the task JSON full path
rem Usage 2: drag a task JSON file onto this .bat icon
rem Usage 3: double-click this file, then paste the JSON CONTENT itself
rem          (single {...} or array [{...}]; multi-line supported, ends
rem          with blank line or END; written to a temp file, auto-cleaned)
rem
rem Project: eys-image batch image generation (image_generate_v5.py, Agnes AI)

setlocal
set "PSHOST=pwsh"
where pwsh >nul 2>nul
if errorlevel 1 set "PSHOST=powershell"

"%PSHOST%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_task.ps1" %*
set "EXITCODE=%errorlevel%"
endlocal & exit /b %EXITCODE%
