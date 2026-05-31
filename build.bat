@echo off
chcp 65001 > nul
echo ===================================================
echo   Python 專案自動化打包工具
echo ===================================================

:: ================= 配置區 =================
set MAIN_SCRIPT=desktop_pet.py
set EXE_NAME=DesktopPet
set ICON_PATH=assets/icon.ico
:: =========================================

echo.
echo [步驟 1] 清理舊的打包快取與舊檔案...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist %EXE_NAME%.spec del /f /q %EXE_NAME%.spec

echo.
echo [步驟 2] 開始使用 PyInstaller 打包成單一 EXE...
echo 正在內嵌 assets 並編譯中，請稍候...

:: 使用 --onefile 並且使用 --add-data 內嵌資源
if defined ICON_PATH (
    pyinstaller --noconfirm --onefile --windowed --name="%EXE_NAME%" --icon="%ICON_PATH%" --add-data "assets;assets" "%MAIN_SCRIPT%"
) else (
    pyinstaller --noconfirm --onefile --windowed --name="%EXE_NAME%" --add-data "assets;assets" "%MAIN_SCRIPT%"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 打包失敗！請檢查上方錯誤訊息。
    goto end
)

echo.
echo [步驟 3] 自動清理暫存與中間副產物...
:: 打包成功後，立刻刪除不需要的 build 資料夾與 .spec 檔案
if exist build rmdir /s /q build
if exist %EXE_NAME%.spec del /f /q %EXE_NAME%.spec
echo 暫存資料夾與 .spec 檔案已清理完畢！

echo.
echo ===================================================
echo   打包成功！
echo   請至產出的 "dist/" 資料夾中提取 %EXE_NAME%.exe
echo ===================================================

:end
pause