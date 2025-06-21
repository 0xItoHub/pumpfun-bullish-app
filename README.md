# 🚀 Pump.fun 爆上げ銘柄スクリーナー

Pump.funの爆上げ銘柄をリアルタイムでスクリーニングするWebアプリケーションです。

## ✨ 特徴

- **リアルタイム監視**: 10秒〜5分間隔で自動更新
- **8つの指標で総合評価**:
  1. 1分間買い注文数（勢い系）
  2. 1時間出来高（勢い系）
  3. クリエイター保有率（リスク系）
  4. LPロック率（リスク系）
  5. トップ10集中度（リスク系）
  6. Xフォロワー増加（SNS系）
  7. Google Trends増加（SNS系）
  8. VWAP回復判定（耐久系）
- **美しいUI**: Streamlitによるモダンなインターフェース
- **無料で運用可能**: Bitquery無料プラン + Streamlit Community Cloud

## 🛠️ 技術スタック

- **Python**: asyncio + aiohttp で並列処理
- **GraphQL**: Bitquery API でオンチェーンデータ取得
- **Web UI**: Streamlit
- **データ処理**: pandas
- **SNS分析**: pytrends, snscrape

## 📋 セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/YOUR_USERNAME/pumpfun-screener.git
cd pumpfun-screener
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. Bitquery API キーの取得

1. [Bitquery.io](https://bitquery.io/) にアクセス
2. アカウント作成
3. API キーを取得（無料プランで100kクエリ/月）

### 4. 環境設定

`.streamlit/secrets.toml` ファイルを編集：

```toml
BITQUERY_KEY = "your_actual_api_key_here"
```

### 5. ローカル実行

```bash
# 方法1: 起動スクリプトを使用
python run.py

# 方法2: 直接Streamlit実行
streamlit run app/app.py
```

### 6. Streamlit Cloud デプロイ（推奨）

1. GitHubにリポジトリをプッシュ
2. [Streamlit Community Cloud](https://share.streamlit.io/) にログイン
3. "New app" → リポジトリ選択 → `app/app.py` をエントリーポイントに設定
4. シークレット設定で `BITQUERY_KEY` を追加
5. デプロイ完了！

## 📊 使用方法

### 基本操作

1. **自動更新**: 設定した間隔で自動的に銘柄をスクリーニング
2. **フィルタ設定**: サイドバーで最小スコア・最小出来高・最大リスクスコアを調整
3. **手動更新**: "🔄 手動更新"ボタンで即座に更新
4. **詳細確認**: トップ銘柄の"🔗 Pump.funで詳細を見る"で詳細ページへ

### スコアリング基準

- **高スコア (7-10)**: 緑色 - 非常に有望
- **中スコア (4-7)**: オレンジ色 - 要監視
- **低スコア (0-4)**: 青色 - リスク高

## 🔧 カスタマイズ

### 銘柄リストの更新

`app/screen.py` の `get_pump_fun_tokens()` 関数を編集：

```python
async def get_pump_fun_tokens() -> List[str]:
    # Pump.fun APIから銘柄リストを取得
    # または手動で銘柄アドレスを追加
    return [
        "token_address_1",
        "token_address_2",
        # ...
    ]
```

### スクリーニング条件の調整

`app/screen.py` の `screen_once()` 関数内の一次フィルタ条件を編集：

```python
# 一次フィルタ条件
if bpm >= 25 and vol1h >= 2000:  # この値を調整
```

### スコア計算の調整

`calculate_score()` 関数で各指標の重みを調整：

```python
def calculate_score(self, row: Dict) -> float:
    score = 0.0
    
    # 勢い系（0-4点）
    score += min(row["buys_per_minute"] / 25, 2.0)  # 重み調整
    score += min(row["volume_1h_sol"] / 2000, 2.0)  # 重み調整
    
    # 他の指標も同様に調整
    return score
```

## 📈 アーキテクチャ

```
┌──────────────────────┐
│  Streamlit UI        │  ← GitHub ↔ Streamlit cloud（無料）
│  ├─ candidates df    │
│  └─ metrics charts   │
└───────▲─┬────────────┘
        │  │ websockets (st_autorefresh 10 s)
        │  ▼
┌──────────────────────┐
│  asyncio worker      │
│  ├─ fetch_board()    │  ← Bitquery subscription：新規/注目トークン
│  ├─ calc_fast_metrics()│ ← buysPerMinute・volume1h
│  └─ deep_scan_pool() │ ← creatorHoldings・top10・LP lock etc.
└──────────────────────┘
```

## 🚨 注意事項

- **投資は自己責任**: このアプリは投資助言ではありません
- **API制限**: Bitquery無料プランは100kクエリ/月
- **レート制限**: 同時接続数を10に制限してAPI負荷を軽減
- **データ精度**: オンチェーンデータに依存するため、リアルタイム性は保証されません

## 🔮 今後の拡張予定

- [ ] ワンクリック買い機能（QuickNode Metis API）
- [ ] Discord/Telegram アラート機能
- [ ] モバイル最適化
- [ ] 履歴データ保存・分析
- [ ] より詳細なテクニカル分析

## 📞 サポート

- バグ報告: [GitHub Issues](https://github.com/YOUR_USERNAME/pumpfun-screener/issues)
- 機能要望: [GitHub Discussions](https://github.com/YOUR_USERNAME/pumpfun-screener/discussions)
- 技術的な質問: [GitHub Discussions](https://github.com/YOUR_USERNAME/pumpfun-screener/discussions)

## 📄 ライセンス

MIT License

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します！

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

---

**⚠️ 投資は自己責任で行ってください。このアプリは投資助言ではありません。** 