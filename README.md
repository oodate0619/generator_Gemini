# ブログ記事ジェネレーター（Streamlit × Gemini版）

社内・学習用サンプル。**Google Gemini API（無料枠あり）**で動作。
キーワードを入れると、タイトル候補 → 記事 → 図解 → WordPress用エクスポートまでを一通り体験できる。

## なぜ Gemini 版？

- Anthropic（Claude）API は2026年4月時点で**断続的な障害**が発生中
- Gemini は**無料枠あり、クレカ登録不要**で API キーが即発行できる
- 学習・実験用途なら **Gemini 2.5 Flash** で十分な品質

## デプロイ手順（Streamlit Community Cloud で URL 公開）

### 必要なもの

- Google アカウント
- GitHub アカウント（無料）
- Streamlit Community Cloud アカウント（無料、GitHub連携で作成可能）

### 手順

#### 1. Gemini API キーを発行（5分）

1. [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) を開く
2. Google アカウントでログイン
3. 「**Create API key**」を押す
4. 「Create API key in new project」を選ぶのがクリーン
5. 表示されたキー（`AIza...` で始まる文字列）を**すぐコピー**して安全な場所に保管

**注意**：このキーが漏れると不正利用されるリスクがあります。GitHub・チャット・スクショに含めないこと。

#### 2. このフォルダの中身を GitHub にプッシュ

新規リポジトリ（例：`blog-generator-gemini`）を作って、以下のファイルを入れる：

```
blog-generator-gemini/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── secrets.toml.example
```

**重要**：`.streamlit/secrets.toml` は **絶対に push しない**こと（`.gitignore` で除外済み）。

#### 3. Streamlit Community Cloud でデプロイ

1. [share.streamlit.io](https://share.streamlit.io/) にアクセス
2. GitHub でログイン
3. 「New app」 → 上で作ったリポジトリを選択
4. Branch は `main`、Main file path は `app.py`
5. App URL は好きな名前（例：`my-blog-generator`）

#### 4. APIキーを Secrets に設定

デプロイ後、アプリ画面の右下「Manage app」 → 「Settings」 → 「Secrets」 を開いて、以下を貼り付け：

```toml
GEMINI_API_KEY = "AIza...（コピーしたキー）"
```

「Save」を押すと自動で再起動して反映される。

#### 5. URL ができる

`https://my-blog-generator.streamlit.app` のような URL で公開される。

## ローカルで動かす場合

```bash
# 1. 依存をインストール
pip install -r requirements.txt

# 2. APIキーを設定
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# secrets.toml を開いて <YOUR_KEY> を実キーに書き換え

# 3. 起動
streamlit run app.py
```

ブラウザで `http://localhost:8501` が開く。

## API コストの目安（Gemini 2.5 Flash）

**無料枠の範囲内**で十分動かせます。

- 無料枠：1日250リクエスト程度（プロジェクト単位）、Flash モデルは無料利用可
- 有料に切り替えても、Gemini 2.5 Flash は **入力 $0.30 / 出力 $2.50 per 1M tokens**（参考：claude-sonnet-4 と比較して数倍安い）
- 1記事フルフローで概算 **5〜15円程度**（無料枠を使い切らなければ実質0円）

学習・実験用途なら気にせず使える。

## 注意点

- **本番のWP連携は未実装**。送信内容のプレビューのみ表示するモック動作
- **画像生成は Gemini が SVG を生成**。写真風カバーが欲しい場合は Imagen API（有料、`imagen-4.0-generate-001` など）への差し替えが必要
- **データ保存なし**。ブラウザを閉じると生成内容は消える（学習用なのでこれで十分）
- **Streamlit Community Cloud は使わないとスリープ**するので、社内デモで使う直前にアクセスして起動させておくとよい
- **Gemini 無料枠のデータは Google の改善に使われる**可能性がある（プライバシー重視なら有料プラン）

## 戦略上の前提

このサンプルは「社内・学習用」が出発点。**売り物（SaaS）に格上げする場合は、Googleの2025-2026年AI生成コンテンツ取り締まり強化を踏まえた差別化戦略が別途必要**。

また、今回 Anthropic 障害 → Gemini に切り替えという経験そのものが、本番運用では**複数 LLM プロバイダーへのフェイルオーバー設計が必要**という重要な学習になります。

## Anthropic（Claude）に戻したい場合

Anthropic API が安定したら、`app.py` を以下のように書き換えれば戻せます：

1. `requirements.txt` の `google-genai` を `anthropic>=0.39.0` に
2. `app.py` の冒頭の import を `from anthropic import Anthropic` に
3. `get_client()` を Anthropic クライアントに
4. `call_gemini()` 関数を Claude API 呼び出しに（前バージョンの `call_claude()` を参照）
5. Secrets を `ANTHROPIC_API_KEY` に

主要なロジック（プロンプト、UI、状態管理）は変更不要。
