@echo off
echo ==========================================
echo   CreativeLog - 支援記録アシスタント
echo   メタゲーム明石
echo ==========================================
echo.

if "%ANTHROPIC_API_KEY%"=="" (
    echo [!] ANTHROPIC_API_KEY が設定されていません
    echo.
    set /p ANTHROPIC_API_KEY="Anthropic APIキーを入力してください: "
)

echo.
echo サーバーを起動します...
echo ブラウザで http://localhost:5000 を開いてください
echo 終了するには Ctrl+C を押してください
echo.

python app.py
pause
