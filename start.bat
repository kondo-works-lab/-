@echo off
cd /d "%~dp0"
set "LOG=%~dp0setup_log.txt"

rem Python の実行コマンドを探す(py ランチャー優先)
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY goto :nopython

rem Python のバージョンと 64bit かどうかを確認
%PY% -c "import sys,struct; print(sys.version); sys.exit(0 if struct.calcsize('P')==8 else 3)"
if errorlevel 3 goto :bit32
if errorlevel 1 goto :nopython

rem セットアップ(完了印 .venv\setup_ok が無ければ毎回やり直す)
if exist ".venv\setup_ok" goto :run
echo 初回セットアップ中です。数分かかります...
echo 途中経過は setup_log.txt に記録されます。
if exist ".venv" rmdir /s /q ".venv"
%PY% -m venv .venv > "%LOG%" 2>&1 || goto :error
".venv\Scripts\python.exe" -m pip install --upgrade pip >> "%LOG%" 2>&1
".venv\Scripts\python.exe" -m pip install -r requirements.txt >> "%LOG%" 2>&1 || goto :error
echo ok> ".venv\setup_ok"
echo セットアップが完了しました。

:run
rem 起動を待ってからブラウザを開く
start "" cmd /c "timeout /t 6 >nul & start http://localhost:8501"
echo.
echo ツールを起動しました。ブラウザが開かない場合は http://localhost:8501 を開いてください。
echo 終了するときはこの黒い画面を閉じてください。
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
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
powershell -NoProfile -Command "Get-Content -Tail 30 '%LOG%'"
echo ------------------------------------------------------------
echo この内容、またはフォルダ内の setup_log.txt を送ってください。
pause
exit /b 1
