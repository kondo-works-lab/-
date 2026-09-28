@echo off
cd /d "%~dp0"

rem Python の実行コマンドを探す(py ランチャー優先)
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY goto :nopython

rem 初回のみ: 専用環境の作成とライブラリのインストール
if not exist ".venv\Scripts\python.exe" (
  echo 初回セットアップ中です。数分かかります...
  %PY% -m venv .venv || goto :error
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error
)

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

:error
echo セットアップに失敗しました。インターネット接続を確認して、もう一度 start.bat を実行してください。
echo 何度も失敗する場合は .venv フォルダを削除してから再実行してください。
pause
exit /b 1
