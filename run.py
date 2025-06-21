#!/usr/bin/env python3
"""
Pump.fun スクリーナー起動スクリプト
"""

import os
import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """依存関係をチェック"""
    required_packages = [
        "streamlit",
        "pandas",
        "aiohttp",
        "gql",
        "pytrends",
        "snscrape",
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ 不足しているパッケージ: {', '.join(missing_packages)}")
        print("以下のコマンドでインストールしてください:")
        print("pip install -r requirements.txt")
        return False

    return True


def check_config():
    """設定ファイルをチェック"""
    secrets_file = Path(".streamlit/secrets.toml")

    if not secrets_file.exists():
        print("❌ .streamlit/secrets.toml ファイルが見つかりません")
        print("以下の手順で設定してください:")
        print("1. .streamlit/secrets.toml ファイルを作成")
        print("2. BITQUERY_KEY = 'your_api_key_here' を追加")
        return False

    # シークレットファイルの内容をチェック
    with open(secrets_file, "r") as f:
        content = f.read()
        if "your_bitquery_api_key_here" in content:
            print("❌ Bitquery API キーが設定されていません")
            print(
                "https://bitquery.io/ でAPIキーを取得し、.streamlit/secrets.toml に設定してください"
            )
            return False

    return True


def main():
    """メイン関数"""
    print("🚀 Pump.fun スクリーナーを起動中...")

    # 依存関係チェック
    if not check_dependencies():
        sys.exit(1)

    # 設定チェック
    if not check_config():
        sys.exit(1)

    print("✅ すべてのチェックが完了しました")
    print("🌐 ブラウザで http://localhost:8501 にアクセスしてください")
    print("🛑 停止するには Ctrl+C を押してください")
    print("-" * 50)

    # Streamlitアプリを起動
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app/app.py",
                "--server.port",
                "8501",
                "--server.address",
                "localhost",
            ]
        )
    except KeyboardInterrupt:
        print("\n👋 アプリケーションを停止しました")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
