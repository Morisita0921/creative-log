"""
CreativeLog - 支援記録アシスタント（EXE版エントリーポイント）
ダブルクリックで起動 → ブラウザが自動で開く
"""

import webbrowser
import threading
import sys
import os

# EXE化した場合のパスを正しく解決
if getattr(sys, 'frozen', False):
    # PyInstallerで固めた場合
    BASE_DIR = sys._MEIPASS
    os.chdir(os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# テンプレートフォルダをFlaskに教える
os.environ.setdefault('CREATIVE_LOG_BASE', BASE_DIR)

from app import app

def open_browser():
    """サーバー起動後にブラウザを自動で開く"""
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    print('=' * 50)
    print('  CreativeLog - 支援記録アシスタント')
    print('  メタゲーム明石')
    print('=' * 50)
    print()
    print('  ブラウザが自動で開きます...')
    print('  閉じるにはこのウィンドウを閉じてください')
    print('=' * 50)

    # 1.5秒後にブラウザを開く
    threading.Timer(1.5, open_browser).start()

    # サーバー起動（本番用: debug=False）
    app.run(debug=False, port=5000, use_reloader=False)
