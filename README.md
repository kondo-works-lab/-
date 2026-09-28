# 経費精算・仕訳自動化ツール(ルールベース版)

CSV / Excel の取引明細を読み込み、摘要のキーワード部分一致で勘定科目を自動判定し、仕訳データ(CSV / Excel)として出力する Streamlit アプリ。外部 API は使用せず、完全オフラインで動作する。

## セキュリティ(データの取り扱い)

- **外部 API・外部通信は一切使用しない。** 判定はローカルの SQLite ルールテーブルとのキーワード照合のみ。
- **取引明細はローカル処理のみ。** アップロードしたファイルはこの PC 上の Streamlit プロセスのメモリ内で処理され、ディスクにも外部にも保存・送信されない。
- `.streamlit/config.toml` で以下を設定済み:
  - `browser.gatherUsageStats = false` … Streamlit の利用統計送信を無効化
  - `server.address = "localhost"` … 自端末以外からアクセス不可
  - `client.toolbarMode = "viewer"` … Deploy ボタン等を非表示
- 初回の `pip install` のみインターネット接続が必要。

## セットアップ・起動

### Windows(かんたん)

1. [python.org](https://www.python.org/downloads/) から Python をインストール(「Add python.exe to PATH」にチェック)
2. このフォルダの `start.bat` をダブルクリック(初回のみ数分かけて自動セットアップ)
3. ブラウザで http://localhost:8501 が開く。終了は黒い画面を閉じる

### コマンドで起動する場合

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

ブラウザで http://localhost:8501 を開く。`sample/sample_statement.csv` で動作確認できる。

## 使い方(3 ステップ)

1. **アップロード** … CSV(UTF-8 / Shift_JIS)または Excel(.xlsx)を選択し「勘定科目を自動判定」
2. **確認・編集** … 判定結果を表で確認。「勘定科目」列はプルダウンで修正可能。未一致は「雑費」
3. **ダウンロード** … 貸方勘定科目(既定: 未払金)を選び、仕訳データを CSV / Excel で出力

### 入力形式

| 列 | 必須 | 備考 |
|---|---|---|
| 日付 | ○ | `2026/09/01`、`2026-09-01` 等 |
| 摘要 | ○ | 判定対象 |
| 金額 | ○ | `1,200`、`¥1,200`、`1200円` 等も可 |
| 取引先 | – | あれば出力に引き継ぐ(判定には使わない) |

### 出力形式

`日付, 借方勘定科目, 借方金額, 貸方勘定科目, 貸方金額, 摘要[, 取引先]`(CSV は BOM 付き UTF-8)

## 判定ロジック

- `data/rules.db` の `rules` テーブル(`id, keyword, account, note`)を `id` 昇順で評価し、摘要にキーワードを含む**最初の**ルールの勘定科目を採用。
- マッチなしは「雑費」。
- 全角/半角・大文字/小文字は同一視(NFKC 正規化 + casefold)。
- DB が無ければ起動時に自動作成し、初期ルール(16 勘定科目)を投入する。初期データは `expense_journal/rules_db.py` の `SEED_RULES`。

ルールを変更する場合は、`data/rules.db` を SQLite クライアントで直接編集するか、`SEED_RULES` を編集して `data/rules.db` を削除し再起動する(UI 編集機能は将来拡張)。

## 構成

```
app.py                       Streamlit UI(3 ステップ)
expense_journal/
  rules_db.py                SQLite ルールテーブル・初期データ
  classifier.py              キーワード部分一致判定
  io.py                      明細読み込み・仕訳出力
sample/sample_statement.csv  サンプル明細
tests/                       pytest
```

## テスト

```bash
pip install -r requirements-dev.txt
pytest
```

## MVP スコープ外(将来拡張)

- 金額基準による会議費/交際費の自動振り分け
- ルールテーブルの UI 編集機能
- 複数キーワードマッチ時の優先度調整 UI
