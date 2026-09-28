@echo off
cd /d "%~dp0"

rem ライブラリの設置先。ツールのフォルダが深い場所にあっても
rem Windows のパス長制限(260文字)を超えないよう、短い場所に固定する
set "VENV=%LOCALAPPDATA%\expense-journal\venv"
set "VPY=%VENV%\Scripts\python.exe"
set "LOG=%LOCALAPPDATA%\expense-journal\setup_log.txt"

rem Python の実行コマンドを探す(py ランチャー優先)
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY goto :nopython

rem Python のバージョンと 64bit かどうかを確認
%PY% -c "import sys,struct; print(sys.version); sys.exit(0 if struct.calcsize('P')==8 else 3)"
set "RC=%errorlevel%"
if "%RC%"=="3" goto :bit32
if not "%RC%"=="0" goto :nopython

rem 必要なライブラリが正しく入っていれば起動へ
if exist "%VPY%" (
  "%VPY%" -c "import streamlit.proto, pandas, openpyxl" >nul 2>nul && goto :run
)

echo 初回セットアップ中です。数分かかります...
if not exist "%LOCALAPPDATA%\expense-journal" mkdir "%LOCALAPPDATA%\expense-journal"
if exist "%VENV%" rmdir /s /q "%VENV%"
%PY% -m venv "%VENV%" > "%LOG%" 2>&1 || goto :error
"%VPY%" -m pip install --upgrade pip >> "%LOG%" 2>&1
"%VPY%" -m pip install -r requirements.txt >> "%LOG%" 2>&1 || goto :error
"%VPY%" -c "import streamlit.proto, pandas, openpyxl" >> "%LOG%" 2>&1 || goto :error
echo セットアップが完了しました。

:run
rem 起動を待ってからブラウザを開く
start "" cmd /c "timeout /t 6 >nul & start http://localhost:8501"
echo.
echo ツールを起動しました。
echo ブラウザが開かない場合は http://localhost:8501 を開いてください。
echo 終了するときは、この黒い画面を閉じてください。
echo.
"%VPY%" -m streamlit run app.py
pause
exit /b 0

:nopython
echo Python が見つかりません。python.org から Python をインストールしてください。
echo インストール時に「Add python.exe to PATH」にチェックを入れてください。
pause
exit /b 1

:bit32
echo 32bit 版の Python が入っています。このツールは 64bit 版が必要です。
echo python.org から「Windows installer (64-bit)」を入れ直してください。
pause
exit /b 1

:error
echo.
echo セットアップに失敗しました。エラー内容(最後の 30 行):
echo ------------------------------------------------------------
powershell -NoProfile -Command "Get-Content -Tail 30 -LiteralPath $env:LOG"
echo ------------------------------------------------------------
echo この画面の内容を送ってください。
pause
exit /b 1
