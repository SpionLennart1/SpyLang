@echo off
setlocal EnableExtensions EnableDelayedExpansion
:MENU
title SpyLang Launcher
color 0A

cls
echo =====================================
echo           SpyLang Launcher
echo =====================================
echo.

echo [1] Run main.spy
echo [2] Run custom file
echo [3] Run in debug mode
echo [4] Exit
echo.

set /p choice=Select option: 

if "%choice%"=="1" goto RUN_MAIN
if "%choice%"=="2" goto RUN_CUSTOM
if "%choice%"=="3" goto RUN_DEBUG
if "%choice%"=="4" exit

goto MENU

:RUN_MAIN
cls
call :RUN_FILE main.spy
goto MENU


:RUN_CUSTOM
cls
set /p file=Enter SpyLang file name (e.g. game.spy): 

if not exist "%file%" (
    echo File not found: %file%
    pause
    goto MENU
)

call :RUN_FILE "%file%"
goto MENU


:RUN_DEBUG
cls
set /p file=Enter SpyLang file for debug: 

if not exist "%file%" (
    echo File not found: %file%
    pause
    goto MENU
)

echo Running in DEBUG MODE...
echo -------------------------------------
py spy.py "%file%"
echo -------------------------------------
echo.
pause
goto MENU


:RUN_FILE
set file=%1

echo Running: %file%
echo -------------------------------------

py spy.py %file%

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Execution failed.
)

echo -------------------------------------
echo Program finished.
echo.
pause
exit /b