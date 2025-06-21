import os
import asyncio
import datetime as dt
import pandas as pd
import aiohttp
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from typing import List, Dict, Tuple, Optional
import logging
from utils import sns_analyzer, token_fetcher, data_processor

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PumpFunScreener:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"X-Api-Key": api_key}
        self.transport = AIOHTTPTransport(
            url="https://streaming.bitquery.io/graphql", headers=self.headers
        )
        self.client = Client(transport=self.transport, fetch_schema_from_transport=True)

        # クエリ定義
        self.fast_stats_query = gql(
            """
        query FastStats($mint: String!, $since1m: DateTime!, $since1h: DateTime!) {
            buys: Solana {
                DEXTrades(
                    where: {
                        Trade: {
                            Side: {Type: {is: "buy"}}, 
                            Currency: {MintAddress: {is: $mint}},
                            Dex: {ProtocolName: {is: "pump"}}
                        }, 
                        Block: {Time: {since: $since1m}}
                    }
                ) {
                    count
                }
            }
            vol1h: Solana {
                DEXTradeByTokens(
                    where: {
                        Trade: {
                            Currency: {MintAddress: {is: $mint}}, 
                            Dex: {ProtocolName: {is: "pump"}}
                        },
                        Block: {Time: {since: $since1h}}
                    }
                ) {
                    volume: sum(of: Trade_Amount)
                }
            }
        }
        """
        )

        self.supply_side_query = gql(
            """
        query SupplySide($token: String!) {
            devHold: Solana {
                BalanceUpdates(
                    where: {
                        BalanceUpdate: {
                            Currency: {MintAddress: {is: $token}},
                            Account: {Owner: {is: "<CREATOR_WALLET>"}}
                        }
                    }
                ) {
                    BalanceUpdate {
                        balance: PostBalance(maximum: Block_Slot)
                    }
                }
            }
            lpLocked: Solana {
                BalanceUpdates(
                    where: {
                        BalanceUpdate: {
                            Currency: {MintAddress: {is: $token}},
                            Account: {
                                Token: {
                                    Owner: {
                                        is: "BesTLFfCP9tAuUDWnqPdtDXZRu5xK6XD8TrABXGBECuf"
                                    }
                                }
                            }
                        }
                    }
                ) {
                    BalanceUpdate {
                        balance: PostBalance(maximum: Block_Slot)
                    }
                }
            }
        }
        """
        )

        self.top_holders_query = gql(
            """
        query TopHolders($token: String!) {
            Solana {
                TokenHolders(
                    where: {
                        Token: {MintAddress: {is: $token}}
                    }
                    limit: 10
                    orderBy: {descending: Balance_Amount}
                ) {
                    Balance {
                        Amount
                        Currency {
                            Name
                            Symbol
                            MintAddress
                        }
                    }
                    Account {
                        Address
                    }
                }
            }
        }
        """
        )

        self.ohlc_query = gql(
            """
        query OHLCData($token: String!, $since: DateTime!) {
            Solana {
                DEXTrades(
                    where: {
                        Trade: {
                            Currency: {MintAddress: {is: $token}},
                            Dex: {ProtocolName: {is: "raydium"}}
                        },
                        Block: {Time: {since: $since}}
                    }
                    orderBy: {ascending: Block_Time}
                ) {
                    Block {
                        Time {
                            time(format: "%Y-%m-%d %H:%M:%S")
                        }
                    }
                    Trade {
                        Amount
                        Price
                        Side {
                            Type
                        }
                    }
                }
            }
        }
        """
        )

    async def fast_stats(self, mint: str) -> Tuple[int, float]:
        """銘柄の勢い系指標を取得"""
        try:
            now = dt.datetime.utcnow()
            vars = {
                "mint": mint,
                "since1m": (now - dt.timedelta(minutes=1)).isoformat() + "Z",
                "since1h": (now - dt.timedelta(hours=1)).isoformat() + "Z",
            }

            result = await self.client.execute_async(
                self.fast_stats_query, variable_values=vars
            )

            bpm = (
                result["buys"]["DEXTrades"][0]["count"]
                if result["buys"]["DEXTrades"]
                else 0
            )
            vol1h = (
                int(result["vol1h"]["DEXTradeByTokens"][0]["volume"] or 0) / 1e9
            )  # lamport→SOL

            return bpm, vol1h
        except Exception as e:
            logger.error(f"Error fetching fast stats for {mint}: {e}")
            return 0, 0.0

    async def get_supply_metrics(self, mint: str) -> Dict[str, float]:
        """供給サイドの指標を取得"""
        try:
            result = await self.client.execute_async(
                self.supply_side_query, variable_values={"token": mint}
            )

            # クリエイター保有率
            dev_balance = 0
            if result["devHold"]["BalanceUpdates"]:
                dev_balance = float(
                    result["devHold"]["BalanceUpdates"][0]["BalanceUpdate"]["balance"]
                    or 0
                )

            # LPロック率
            lp_balance = 0
            if result["lpLocked"]["BalanceUpdates"]:
                lp_balance = float(
                    result["lpLocked"]["BalanceUpdates"][0]["BalanceUpdate"]["balance"]
                    or 0
                )

            return {"creator_holdings": dev_balance, "lp_locked": lp_balance}
        except Exception as e:
            logger.error(f"Error fetching supply metrics for {mint}: {e}")
            return {"creator_holdings": 0, "lp_locked": 0}

    async def get_top_holders(self, mint: str) -> List[Dict]:
        """トップ10ホルダーを取得"""
        try:
            result = await self.client.execute_async(
                self.top_holders_query, variable_values={"token": mint}
            )

            holders = []
            for holder in result["Solana"]["TokenHolders"]:
                holders.append(
                    {
                        "address": holder["Account"]["Address"],
                        "amount": float(holder["Balance"]["Amount"] or 0),
                    }
                )

            return holders
        except Exception as e:
            logger.error(f"Error fetching top holders for {mint}: {e}")
            return []

    async def check_vwap_resilience(self, mint: str) -> bool:
        """VWAP回復判定（-40%急落→回復）"""
        try:
            now = dt.datetime.utcnow()
            since = (now - dt.timedelta(minutes=10)).isoformat() + "Z"

            result = await self.client.execute_async(
                self.ohlc_query, variable_values={"token": mint, "since": since}
            )

            trades = result["Solana"]["DEXTrades"]
            if len(trades) < 10:  # 十分な取引データがない
                return False

            # 価格データを時系列で整理
            prices = []
            for trade in trades:
                price = float(trade["Trade"]["Price"] or 0)
                if price > 0:
                    prices.append(price)

            if len(prices) < 5:
                return False

            # 急落判定（-40%以上）
            max_price = max(prices)
            min_price = min(prices)
            drop_pct = (max_price - min_price) / max_price

            if drop_pct >= 0.4:  # 40%以上の急落
                # 回復判定（最新価格が最低価格から20%以上回復）
                latest_price = prices[-1]
                recovery_pct = (latest_price - min_price) / min_price
                return recovery_pct >= 0.2

            return False
        except Exception as e:
            logger.error(f"Error checking VWAP resilience for {mint}: {e}")
            return False

    async def get_sns_metrics(self, mint: str, token_info: Dict) -> Dict[str, int]:
        """SNS指標を取得"""
        try:
            # トークン名とシンボルを取得
            symbol = token_info.get("symbol", "UNKNOWN")
            name = token_info.get("name", "Unknown")

            # キーワードを決定（シンボルを優先）
            keyword = symbol if symbol != "UNKNOWN" else name

            # Google Trends
            trends_data = await sns_analyzer.get_google_trends(keyword)

            # Twitter統計
            twitter_data = await sns_analyzer.get_twitter_stats(keyword)

            return {
                "x_growth": twitter_data.get("growth", 0),
                "gtrend_growth": trends_data.get("growth", 0),
            }
        except Exception as e:
            logger.error(f"Error fetching SNS metrics for {mint}: {e}")
            return {"x_growth": 0, "gtrend_growth": 0}

    async def screen_once(self, candidates: List[str]) -> pd.DataFrame:
        """一次スクリーニング実行"""
        rows = []
        sem = asyncio.Semaphore(10)  # レート制限対策

        async def process_mint(mint: str):
            async with sem:
                bpm, vol1h = await self.fast_stats(mint)

                # 一次フィルタ条件
                if bpm >= 25 and vol1h >= 2000:
                    # トークン情報を取得
                    token_info = await token_fetcher.get_token_info(mint)

                    row = {
                        "mint": mint,
                        "name": token_info.get("name", "Unknown"),
                        "symbol": token_info.get("symbol", "UNKNOWN"),
                        "buys_per_minute": bpm,
                        "volume_1h_sol": vol1h,
                        "creator_holdings_pct": 0.0,
                        "lp_lock_pct": 0.0,
                        "top10_concentration": 0.0,
                        "x_growth": 0,
                        "gtrend_growth": 0,
                        "vwap_resilience": False,
                        "score": 0.0,
                        "risk_score": 0.0,
                        "momentum_score": 0.0,
                    }
                    rows.append(row)

        # 並列処理
        await asyncio.gather(*(process_mint(mint) for mint in candidates))

        if not rows:
            return pd.DataFrame()

        # 二次スクリーニング（非同期で深堀り）
        async def deep_scan(row_idx: int, mint: str):
            try:
                # 供給サイド指標
                supply_metrics = await self.get_supply_metrics(mint)

                # トップホルダー
                top_holders = await self.get_top_holders(mint)

                # VWAP回復判定
                vwap_resilience = await self.check_vwap_resilience(mint)

                # SNS指標
                token_info = {
                    "symbol": rows[row_idx]["symbol"],
                    "name": rows[row_idx]["name"],
                }
                sns_metrics = await self.get_sns_metrics(mint, token_info)

                # 結果を更新
                rows[row_idx].update(
                    {
                        "creator_holdings_pct": supply_metrics["creator_holdings"],
                        "lp_lock_pct": supply_metrics["lp_locked"],
                        "top10_concentration": (
                            sum(h["amount"] for h in top_holders[:10])
                            if top_holders
                            else 0
                        ),
                        "vwap_resilience": vwap_resilience,
                        "x_growth": sns_metrics["x_growth"],
                        "gtrend_growth": sns_metrics["gtrend_growth"],
                    }
                )

                # スコア計算
                score = self.calculate_score(rows[row_idx])
                risk_score = data_processor.calculate_risk_score(rows[row_idx])
                momentum_score = data_processor.calculate_momentum_score(rows[row_idx])

                rows[row_idx].update(
                    {
                        "score": score,
                        "risk_score": risk_score,
                        "momentum_score": momentum_score,
                    }
                )

            except Exception as e:
                logger.error(f"Error in deep scan for {mint}: {e}")

        # 二次スクリーニングを並列実行
        deep_scan_tasks = [deep_scan(i, row["mint"]) for i, row in enumerate(rows)]
        await asyncio.gather(*deep_scan_tasks)

        df = pd.DataFrame(rows)
        return df.sort_values("score", ascending=False)

    def calculate_score(self, row: Dict) -> float:
        """総合スコア計算"""
        score = 0.0

        # 勢い系（0-4点）
        score += min(row["buys_per_minute"] / 25, 2.0)  # 買い注文数
        score += min(row["volume_1h_sol"] / 2000, 2.0)  # 1時間出来高

        # リスク系（0-3点）
        score += max(
            0, 1 - row["creator_holdings_pct"] * 100
        )  # クリエイター保有率（低いほど良い）
        score += min(row["lp_lock_pct"], 1.0)  # LPロック率
        score += max(
            0, (8 - row["top10_concentration"] * 100) / 8
        )  # トップ10集中度（低いほど良い）

        # SNS系（0-2点）
        score += min(row["x_growth"] / 300, 1.0)  # Xフォロワー増加
        score += min(row["gtrend_growth"] / 300, 1.0)  # Google Trends増加

        # 耐久系（0-1点）
        score += 1.0 if row["vwap_resilience"] else 0.0  # VWAP回復

        return score


# サンプル銘柄リスト（実際の運用では動的に取得）
SAMPLE_MINTS = [
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "So11111111111111111111111111111111111111112",  # SOL
    # 実際のPump.fun銘柄を追加
]


async def get_pump_fun_tokens() -> List[str]:
    """Pump.funの銘柄リストを取得"""
    return await token_fetcher.get_pump_fun_tokens()
