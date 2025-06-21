import streamlit as st
import asyncio
import pandas as pd
import datetime as dt
from screen import PumpFunScreener, get_pump_fun_tokens
import webbrowser
import time

# ページ設定
st.set_page_config(
    page_title="Pump.fun 爆上げ銘柄スクリーナー",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# カスタムCSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #FF6B6B;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .score-high {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    .score-medium {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    .score-low {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    .stDataFrame {
        font-size: 0.9rem;
    }
    .token-info {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

# セッション状態の初期化
if "screener" not in st.session_state:
    st.session_state.screener = None
if "last_update" not in st.session_state:
    st.session_state.last_update = None
if "candidates_df" not in st.session_state:
    st.session_state.candidates_df = pd.DataFrame()


def initialize_screener():
    """スクリーナーの初期化"""
    api_key = st.secrets.get("BITQUERY_KEY")
    if not api_key:
        st.error(
            "⚠️ BITQUERY_KEYが設定されていません。.streamlit/secrets.tomlに設定してください。"
        )
        st.stop()

    if st.session_state.screener is None:
        st.session_state.screener = PumpFunScreener(api_key)


def get_score_color(score):
    """スコアに基づいて色を返す"""
    if score >= 7:
        return "score-high"
    elif score >= 4:
        return "score-medium"
    else:
        return "score-low"


def format_dataframe(df):
    """DataFrameの表示形式を整える"""
    if df.empty:
        return df

    # 数値のフォーマット
    df_display = df.copy()

    # スコアでソート
    df_display = df_display.sort_values("score", ascending=False)

    # 列名を日本語に
    column_mapping = {
        "mint": "銘柄アドレス",
        "name": "トークン名",
        "symbol": "シンボル",
        "buys_per_minute": "1分間買い注文数",
        "volume_1h_sol": "1時間出来高(SOL)",
        "creator_holdings_pct": "クリエイター保有率",
        "lp_lock_pct": "LPロック率",
        "top10_concentration": "トップ10集中度",
        "x_growth": "Xフォロワー増加",
        "gtrend_growth": "Google Trends増加",
        "vwap_resilience": "VWAP回復",
        "score": "総合スコア",
        "risk_score": "リスクスコア",
        "momentum_score": "勢いスコア",
    }

    df_display = df_display.rename(columns=column_mapping)

    # 数値のフォーマット
    if "1時間出来高(SOL)" in df_display.columns:
        df_display["1時間出来高(SOL)"] = df_display["1時間出来高(SOL)"].apply(
            lambda x: f"{x:,.0f}"
        )

    if "1分間買い注文数" in df_display.columns:
        df_display["1分間買い注文数"] = df_display["1分間買い注文数"].apply(
            lambda x: f"{x:,}"
        )

    if "総合スコア" in df_display.columns:
        df_display["総合スコア"] = df_display["総合スコア"].apply(lambda x: f"{x:.2f}")

    if "リスクスコア" in df_display.columns:
        df_display["リスクスコア"] = df_display["リスクスコア"].apply(
            lambda x: f"{x:.2f}"
        )

    if "勢いスコア" in df_display.columns:
        df_display["勢いスコア"] = df_display["勢いスコア"].apply(lambda x: f"{x:.2f}")

    if "VWAP回復" in df_display.columns:
        df_display["VWAP回復"] = df_display["VWAP回復"].apply(
            lambda x: "✅" if x else "❌"
        )

    return df_display


async def run_screening():
    """スクリーニング実行"""
    try:
        # 銘柄リスト取得
        candidates = await get_pump_fun_tokens()

        if not candidates:
            st.warning("銘柄リストが取得できませんでした。")
            return pd.DataFrame()

        # スクリーニング実行
        with st.spinner("銘柄をスクリーニング中..."):
            df = await st.session_state.screener.screen_once(candidates)

        return df

    except Exception as e:
        st.error(f"スクリーニング中にエラーが発生しました: {e}")
        return pd.DataFrame()


def main():
    # ヘッダー
    st.markdown(
        '<h1 class="main-header">🚀 Pump.fun 爆上げ銘柄スクリーナー</h1>',
        unsafe_allow_html=True,
    )

    # 初期化
    initialize_screener()

    # サイドバー
    with st.sidebar:
        st.header("⚙️ 設定")

        # 更新間隔
        refresh_interval = st.slider(
            "更新間隔（秒）", min_value=10, max_value=300, value=30, step=10
        )

        # フィルタ設定
        st.subheader("🔍 フィルタ設定")
        min_score = st.slider(
            "最小スコア", min_value=0.0, max_value=10.0, value=3.0, step=0.5
        )

        min_volume = st.number_input(
            "最小出来高（SOL）", min_value=0, value=1000, step=100
        )

        max_risk = st.slider(
            "最大リスクスコア", min_value=0.0, max_value=1.0, value=0.7, step=0.1
        )

        # 手動更新ボタン
        if st.button("🔄 手動更新", type="primary"):
            st.session_state.last_update = None

    # メインコンテンツ
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="監視銘柄数",
            value=(
                len(st.session_state.candidates_df)
                if not st.session_state.candidates_df.empty
                else 0
            ),
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        if not st.session_state.candidates_df.empty:
            avg_score = st.session_state.candidates_df["score"].mean()
            st.metric(label="平均スコア", value=f"{avg_score:.2f}")
        else:
            st.metric(label="平均スコア", value="0.00")
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        if not st.session_state.candidates_df.empty:
            total_volume = st.session_state.candidates_df["volume_1h_sol"].sum()
            st.metric(label="総出来高", value=f"{total_volume:,.0f} SOL")
        else:
            st.metric(label="総出来高", value="0 SOL")
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        if st.session_state.last_update:
            st.metric(
                label="最終更新",
                value=st.session_state.last_update.strftime("%H:%M:%S"),
            )
        else:
            st.metric(label="最終更新", value="未更新")
        st.markdown("</div>", unsafe_allow_html=True)

    # 自動更新
    if (
        st.session_state.last_update is None
        or (dt.datetime.now() - st.session_state.last_update).seconds
        >= refresh_interval
    ):

        # スクリーニング実行
        df = asyncio.run(run_screening())

        if not df.empty:
            # フィルタ適用
            df_filtered = df[
                (df["score"] >= min_score)
                & (df["volume_1h_sol"] >= min_volume)
                & (df["risk_score"] <= max_risk)
            ].copy()

            st.session_state.candidates_df = df_filtered
            st.session_state.last_update = dt.datetime.now()

    # 結果表示
    st.subheader("📊 スクリーニング結果")

    if not st.session_state.candidates_df.empty:
        # フォーマット済みDataFrameを表示
        df_display = format_dataframe(st.session_state.candidates_df)

        # データテーブル表示
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # 詳細情報
        st.subheader("📈 詳細分析")

        # スコア分布
        col1, col2 = st.columns(2)

        with col1:
            st.write("**スコア分布**")
            score_counts = (
                st.session_state.candidates_df["score"]
                .apply(
                    lambda x: (
                        "高スコア(7-10)"
                        if x >= 7
                        else "中スコア(4-7)" if x >= 4 else "低スコア(0-4)"
                    )
                )
                .value_counts()
            )
            st.bar_chart(score_counts)

        with col2:
            st.write("**出来高分布**")
            volume_data = st.session_state.candidates_df["volume_1h_sol"]
            st.line_chart(volume_data)

        # リスク分析
        col1, col2 = st.columns(2)

        with col1:
            st.write("**リスクスコア分布**")
            risk_data = st.session_state.candidates_df["risk_score"]
            st.line_chart(risk_data)

        with col2:
            st.write("**勢いスコア分布**")
            momentum_data = st.session_state.candidates_df["momentum_score"]
            st.line_chart(momentum_data)

        # トップ銘柄の詳細
        if len(st.session_state.candidates_df) > 0:
            st.subheader("🏆 トップ銘柄")
            top_token = st.session_state.candidates_df.iloc[0]

            # トークン情報カード
            st.markdown(
                f"""
            <div class="token-info">
                <h3>{top_token['name']} ({top_token['symbol']})</h3>
                <p><strong>銘柄アドレス:</strong> {top_token['mint'][:8]}...{top_token['mint'][-8:]}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("総合スコア", f"{top_token['score']:.2f}")

            with col2:
                st.metric("1分間買い注文数", f"{top_token['buys_per_minute']:,}")

            with col3:
                st.metric("1時間出来高", f"{top_token['volume_1h_sol']:,.0f} SOL")

            with col4:
                st.metric("VWAP回復", "✅" if top_token["vwap_resilience"] else "❌")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("リスクスコア", f"{top_token['risk_score']:.2f}")

            with col2:
                st.metric("勢いスコア", f"{top_token['momentum_score']:.2f}")

            with col3:
                st.metric("Xフォロワー増加", f"{top_token['x_growth']}")

            with col4:
                st.metric("Google Trends増加", f"{top_token['gtrend_growth']}")

            # Pump.funリンク
            pump_fun_url = f"https://pump.fun/coin/{top_token['mint']}"
            if st.button("🔗 Pump.funで詳細を見る", key="top_token_link"):
                webbrowser.open(pump_fun_url)

    else:
        st.info("スクリーニング条件に合う銘柄が見つかりませんでした。")

    # フッター
    st.markdown("---")
    st.markdown(
        """
    <div style="text-align: center; color: #666; font-size: 0.8rem;">
        <p>⚠️ 投資は自己責任で行ってください。このアプリは投資助言ではありません。</p>
        <p>Powered by Bitquery GraphQL API + Streamlit</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
