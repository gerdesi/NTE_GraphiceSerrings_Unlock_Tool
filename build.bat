@echo off
chcp 65001 >nul
title NTE Graphics Settings Unlock Tool - Build Script

:menu
cls
echo ==================================================
echo         NTE Graphics Settings Unlock Tool         
echo ==================================================
echo.
echo Please select the language version to build:
echo.
echo  [1] English Version (ENG)
echo  [2] Simplified Chinese Version (CHS)
echo  [3] Traditional Chinese Version (CHT)
echo  [4] Build All Versions (ENG + CHS + CHT)
echo  [5] Exit
echo.
echo ==================================================
set /p choice=Enter your choice (1-5): 

if "%choice%"=="1" goto build_eng
if "%choice%"=="2" goto build_chs
if "%choice%"=="3" goto build_cht
if "%choice%"=="4" goto build_all
if "%choice%"=="5" goto exit

echo Invalid selection, please try again.
timeout /t 2 >nul
goto menu

:build_eng
echo.
echo [1/1] Building English version...
pyinstaller --noconfirm --onefile --windowed --clean --icon=icon.ico --add-data "icon.ico;." NTE_GraphiceSerrings_Unlock_Tool.py
goto check_result

:build_chs
echo.
echo [1/1] Building Simplified Chinese version...
pyinstaller --noconfirm --onefile --windowed --clean --icon=icon.ico --add-data "icon.ico;." NTE_GraphiceSettings_Unlock_Tool_CHS.py
goto check_result

:build_cht
echo.
echo [1/1] Building Traditional Chinese version...
pyinstaller --noconfirm --onefile --windowed --clean --icon=icon.ico --add-data "icon.ico;." NTE_GraphiceSettings_Unlock_Tool_CHT.py
goto check_result

:build_all
echo.
echo [1/3] Building English version...
pyinstaller --noconfirm --onefile --windowed --clean --icon=icon.ico --add-data "icon.ico;." NTE_GraphiceSerrings_Unlock_Tool.py
echo.
echo [2/3] Building Simplified Chinese version...
pyinstaller --noconfirm --onefile --windowed --clean --icon=icon.ico --add-data "icon.ico;." NTE_GraphiceSettings_Unlock_Tool_CHS.py
echo.
echo [3/3] Building Traditional Chinese version...
pyinstaller --noconfirm --onefile --windowed --clean --icon=icon.ico --add-data "icon.ico;." NTE_GraphiceSettings_Unlock_Tool_CHT.py
goto check_result

:check_result
echo.
echo ==================================================
echo Build completed! Output files are saved in the [dist] folder.
echo ==================================================
pause
goto exit

:exit
exit