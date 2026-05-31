@echo off
chcp 65001 > nul
echo ===================================================
echo   Python 專案自動化打包工具 (通用相對路徑版)
echo ===================================================

:: 取得目前 .bat 檔所在的根目錄路徑
set "BASE_DIR=%~dp0"

:: ================= 配置區 =================
set "MAIN_SCRIPT=%BASE_DIR%desktop_pet.py"
set "EXE_NAME=DesktopPet"
set "ICON_PATH=%BASE_DIR%assets\icon.ico"

:: Python 執行檔解析順序：
:: 1. 外部指定的 PYTHON_EXE
:: 2. 專案本機 .venv
:: 3. Windows py launcher
:: 4. PATH 裡的 python
set "PYTHON_CMD="

if defined PYTHON_EXE (
    if exist "%PYTHON_EXE%" (
        set "PYTHON_CMD="%PYTHON_EXE%""
    ) else (
        echo [ERROR] PYTHON_EXE does not exist: %PYTHON_EXE%
        goto end
    )
)

if not defined PYTHON_CMD (
    if exist "%BASE_DIR%.venv\Scripts\python.exe" (
        set "PYTHON_CMD="%BASE_DIR%.venv\Scripts\python.exe""
    )
)

if not defined PYTHON_CMD (
    py -3 --version > nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
    python --version > nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [ERROR] Python not found. Create .venv or install Python, then run build.bat again.
    goto end
)

echo Using Python: %PYTHON_CMD%
:: =========================================

echo.
echo [步驟 1] 清理舊的打包快取與舊檔案...
if exist "%BASE_DIR%build" rmdir /s /q "%BASE_DIR%build"
if exist "%BASE_DIR%dist" rmdir /s /q "%BASE_DIR%dist"
if exist "%BASE_DIR%%EXE_NAME%.spec" del /f /q "%BASE_DIR%%EXE_NAME%.spec"

echo.
echo [步驟 2] 檢查並安裝 PyInstaller...
%PYTHON_CMD% -m pip install pyinstaller --break-system-packages > nul

echo.
echo [步驟 3] 開始使用 Python 3.13 環境打包成單一 EXE...
echo 正在內嵌 assets 並編譯中，請稍候...

:: 執行打包，所有路徑皆動態綁定
if exist "%ICON_PATH%" (
    %PYTHON_CMD% -m PyInstaller --noconfirm --onefile --windowed --name="%EXE_NAME%" --icon="%ICON_PATH%" --add-data "%BASE_DIR%assets;assets" "%MAIN_SCRIPT%"
) else (
    %PYTHON_CMD% -m PyInstaller --noconfirm --onefile --windowed --name="%EXE_NAME%" --add-data "%BASE_DIR%assets;assets" "%MAIN_SCRIPT%"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 打包失敗！請檢查上方錯誤訊息。
    goto end
)

echo.
echo [步驟 4] 自動清理暫存與中間副產物...
if exist "%BASE_DIR%build" rmdir /s /q "%BASE_DIR%build"
if exist "%BASE_DIR%%EXE_NAME%.spec" del /f /q "%BASE_DIR%%EXE_NAME%.spec"
echo 🧹 暫存資料夾與 .spec 檔案已清理完畢！

echo.
echo ===================================================
echo   🎉 打包成功！
echo   請至產出的 "dist/" 資料夾中執行 %EXE_NAME%.exe
echo ===================================================

:end
pause
