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

:: 透過相對路徑定位使用者目錄下的 uv Python 3.13 執行檔
set "PYTHON_EXE=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.13.12-windows-x86_64-none\python.exe"
:: =========================================

echo.
echo [步驟 1] 清理舊的打包快取與舊檔案...
if exist "%BASE_DIR%build" rmdir /s /q "%BASE_DIR%build"
if exist "%BASE_DIR%dist" rmdir /s /q "%BASE_DIR%dist"
if exist "%BASE_DIR%%EXE_NAME%.spec" del /f /q "%BASE_DIR%%EXE_NAME%.spec"

echo.
echo [步驟 2] 檢查並安裝 PyInstaller...
"%PYTHON_EXE%" -m pip install pyinstaller --break-system-packages > nul

echo.
echo [步驟 3] 開始使用 Python 3.13 環境打包成單一 EXE...
echo 正在內嵌 assets 並編譯中，請稍候...

:: 執行打包，所有路徑皆動態綁定
if exist "%ICON_PATH%" (
    "%PYTHON_EXE%" -m PyInstaller --noconfirm --onefile --windowed --name="%EXE_NAME%" --icon="%ICON_PATH%" --add-data "%BASE_DIR%assets;assets" "%MAIN_SCRIPT%"
) else (
    "%PYTHON_EXE%" -m PyInstaller --noconfirm --onefile --windowed --name="%EXE_NAME%" --add-data "%BASE_DIR%assets;assets" "%MAIN_SCRIPT%"
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