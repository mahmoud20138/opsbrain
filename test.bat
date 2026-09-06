@echo off
REM Shortcut to execute OpsBrain test suite
call "%~dp0run.bat" test %*
exit /b %errorlevel%
