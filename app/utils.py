import asyncio
import aiohttp
import pandas as pd
from typing import List, Dict, Optional
from pytrends.request import TrendReq
import snscrape.modules.twitter as sntwitter
import logging

logger = logging.getLogger(__name__)


class SNSAnalyzer:
    """SNS分析クラス"""

    def __init__(self):
        self.pytrends = TrendReq(hl="ja-JP", tz=540)  # 日本時間

    async def get_google_trends(self, keyword: str) -> Dict[str, int]:
        """Google Trendsデータを取得"""
        try:
            # 非同期で実行するため、別スレッドで実行
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._get_trends_sync, keyword)
            return result
        except Exception as e:
            logger.error(f"Error fetching Google Trends for {keyword}: {e}")
            return {"interest": 0, "growth": 0}

    def _get_trends_sync(self, keyword: str) -> Dict[str, int]:
        """同期版Google Trends取得"""
        try:
            self.pytrends.build_payload([keyword], timeframe="now 1-H")
            interest_over_time = self.pytrends.interest_over_time()

            if not interest_over_time.empty:
                current_interest = interest_over_time[keyword].iloc[-1]
                avg_interest = interest_over_time[keyword].mean()
                growth = current_interest - avg_interest

                return {"interest": int(current_interest), "growth": int(growth)}
            else:
                return {"interest": 0, "growth": 0}
        except Exception as e:
            logger.error(f"Error in sync trends fetch: {e}")
            return {"interest": 0, "growth": 0}

    async def get_twitter_stats(self, keyword: str) -> Dict[str, int]:
        """Twitter統計を取得"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._get_twitter_sync, keyword)
            return result
        except Exception as e:
            logger.error(f"Error fetching Twitter stats for {keyword}: {e}")
            return {"followers": 0, "posts": 0, "growth": 0}

    def _get_twitter_sync(self, keyword: str) -> Dict[str, int]:
        """同期版Twitter統計取得"""
        try:
            # 過去1時間のツイート数を取得
            tweets = list(
                sntwitter.TwitterSearchScraper(f"{keyword} since:1h").get_items()
            )

            # ユーザー情報を取得（最初のツイートから）
            if tweets:
                user = tweets[0].user
                return {
                    "followers": user.followersCount,
                    "posts": len(tweets),
                    "growth": len(tweets),  # 簡易的な成長指標
                }
            else:
                return {"followers": 0, "posts": 0, "growth": 0}
        except Exception as e:
            logger.error(f"Error in sync Twitter fetch: {e}")
            return {"followers": 0, "posts": 0, "growth": 0}


class TokenInfoFetcher:
    """トークン情報取得クラス"""

    def __init__(self):
        self.session = None

    async def get_session(self):
        """aiohttpセッションを取得"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def get_token_info(self, mint_address: str) -> Dict[str, str]:
        """トークン基本情報を取得"""
        try:
            session = await self.get_session()

            # Pump.fun APIからトークン情報を取得
            url = f"https://pump.fun/api/coins/{mint_address}"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "name": data.get("name", "Unknown"),
                        "symbol": data.get("symbol", "UNKNOWN"),
                        "description": data.get("description", ""),
                        "image": data.get("image", ""),
                        "website": data.get("website", ""),
                        "twitter": data.get("twitter", ""),
                        "telegram": data.get("telegram", ""),
                    }
                else:
                    return {
                        "name": "Unknown",
                        "symbol": "UNKNOWN",
                        "description": "",
                        "image": "",
                        "website": "",
                        "twitter": "",
                        "telegram": "",
                    }
        except Exception as e:
            logger.error(f"Error fetching token info for {mint_address}: {e}")
            return {
                "name": "Unknown",
                "symbol": "UNKNOWN",
                "description": "",
                "image": "",
                "website": "",
                "twitter": "",
                "telegram": "",
            }

    async def get_pump_fun_tokens(self) -> List[str]:
        """Pump.funの銘柄リストを取得"""
        try:
            session = await self.get_session()

            # Pump.fun APIから銘柄リストを取得
            url = "https://pump.fun/api/coins"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # 最新の銘柄を取得（例：過去24時間で作成されたもの）
                    recent_tokens = []
                    for coin in data.get("coins", []):
                        if coin.get("mintAddress"):
                            recent_tokens.append(coin["mintAddress"])

                    return recent_tokens[:50]  # 最新50銘柄
                else:
                    # フォールバック：サンプル銘柄
                    return self._get_sample_tokens()
        except Exception as e:
            logger.error(f"Error fetching pump.fun tokens: {e}")
            return self._get_sample_tokens()

    def _get_sample_tokens(self) -> List[str]:
        """サンプル銘柄リスト（フォールバック用）"""
        return [
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "So11111111111111111111111111111111111111112",  # SOL
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # Bonk
            "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",  # POPCAT
        ]


class DataProcessor:
    """データ処理クラス"""

    @staticmethod
    def calculate_risk_score(row: Dict) -> float:
        """リスクスコア計算"""
        risk_score = 0.0

        # クリエイター保有率（高いほどリスク）
        creator_risk = min(row.get("creator_holdings_pct", 0) * 100, 1.0)
        risk_score += creator_risk * 0.4

        # トップ10集中度（高いほどリスク）
        concentration_risk = min(row.get("top10_concentration", 0) * 100, 1.0)
        risk_score += concentration_risk * 0.3

        # LPロック率（低いほどリスク）
        lp_risk = 1.0 - min(row.get("lp_lock_pct", 0), 1.0)
        risk_score += lp_risk * 0.3

        return risk_score

    @staticmethod
    def calculate_momentum_score(row: Dict) -> float:
        """勢いスコア計算"""
        momentum_score = 0.0

        # 買い注文数
        buys = row.get("buys_per_minute", 0)
        momentum_score += min(buys / 25, 2.0)

        # 出来高
        volume = row.get("volume_1h_sol", 0)
        momentum_score += min(volume / 2000, 2.0)

        return momentum_score

    @staticmethod
    def format_number(value: float, decimals: int = 2) -> str:
        """数値フォーマット"""
        if value >= 1_000_000:
            return f"{value/1_000_000:.{decimals}f}M"
        elif value >= 1_000:
            return f"{value/1_000:.{decimals}f}K"
        else:
            return f"{value:.{decimals}f}"

    @staticmethod
    def format_percentage(value: float) -> str:
        """パーセンテージフォーマット"""
        return f"{value * 100:.1f}%"

    @staticmethod
    def create_summary_stats(df: pd.DataFrame) -> Dict:
        """サマリー統計作成"""
        if df.empty:
            return {}

        return {
            "total_tokens": len(df),
            "avg_score": df["score"].mean(),
            "max_score": df["score"].max(),
            "total_volume": df["volume_1h_sol"].sum(),
            "avg_volume": df["volume_1h_sol"].mean(),
            "high_risk_count": len(df[df["score"] < 3]),
            "medium_risk_count": len(df[(df["score"] >= 3) & (df["score"] < 7)]),
            "low_risk_count": len(df[df["score"] >= 7]),
        }


# グローバルインスタンス
sns_analyzer = SNSAnalyzer()
token_fetcher = TokenInfoFetcher()
data_processor = DataProcessor()
