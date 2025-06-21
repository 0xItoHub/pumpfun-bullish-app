"""
Pump.fun スクリーナー設定ファイル
"""

# API設定
BITQUERY_URL = "https://streaming.bitquery.io/graphql"
PUMP_FUN_API_URL = "https://pump.fun/api"

# スクリーニング設定
DEFAULT_MIN_BUYS_PER_MINUTE = 25
DEFAULT_MIN_VOLUME_SOL = 2000
DEFAULT_MIN_SCORE = 3.0
DEFAULT_MAX_RISK_SCORE = 0.7

# 更新間隔設定
MIN_REFRESH_INTERVAL = 10  # 秒
MAX_REFRESH_INTERVAL = 300  # 秒
DEFAULT_REFRESH_INTERVAL = 30  # 秒

# 並列処理設定
MAX_CONCURRENT_REQUESTS = 10
REQUEST_TIMEOUT = 30  # 秒

# スコアリング重み
SCORE_WEIGHTS = {
    "momentum": {
        "buys_per_minute": 2.0,  # 最大2点
        "volume_1h": 2.0,  # 最大2点
    },
    "risk": {
        "creator_holdings": 1.0,  # 最大1点（低いほど良い）
        "lp_lock": 1.0,  # 最大1点
        "top10_concentration": 1.0,  # 最大1点（低いほど良い）
    },
    "social": {
        "x_growth": 1.0,  # 最大1点
        "gtrend_growth": 1.0,  # 最大1点
    },
    "resilience": {
        "vwap_recovery": 1.0,  # 最大1点
    },
}

# VWAP回復判定設定
VWAP_DROP_THRESHOLD = 0.4  # 40%以上の急落
VWAP_RECOVERY_THRESHOLD = 0.2  # 20%以上の回復
VWAP_LOOKBACK_MINUTES = 10

# SNS分析設定
GOOGLE_TRENDS_TIMEFRAME = "now 1-H"
TWITTER_SEARCH_TIMEFRAME = "since:1h"

# UI設定
PAGE_TITLE = "Pump.fun 爆上げ銘柄スクリーナー"
PAGE_ICON = "🚀"

# カラー設定
COLORS = {
    "primary": "#FF6B6B",
    "secondary": "#667eea",
    "success": "#11998e",
    "warning": "#f093fb",
    "info": "#4facfe",
    "gradient_start": "#667eea",
    "gradient_end": "#764ba2",
}

# ログ設定
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# データベース設定（将来的な拡張用）
DATABASE_CONFIG = {
    "type": "sqlite",
    "path": "data/screener.db",
    "backup_interval": 3600,  # 1時間
    "max_backups": 24,
}

# アラート設定（将来的な拡張用）
ALERT_CONFIG = {
    "discord_webhook": None,
    "telegram_bot_token": None,
    "telegram_chat_id": None,
    "email_smtp_server": None,
    "email_username": None,
    "email_password": None,
    "email_recipients": [],
}

# キャッシュ設定
CACHE_CONFIG = {"enabled": True, "ttl": 300, "max_size": 1000}  # 5分

# 開発設定
DEBUG = False
TEST_MODE = False
