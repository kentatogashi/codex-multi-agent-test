# Kanagawa Weekly Weather Viewer

神奈川県の一週間の天気予報を Web 表示する小さな Python アプリです。気象庁の公開 JSON を取得し、概況、県東部 / 県西部の近い予報、週間予報を 1 画面にまとめて表示します。

## Features

- Python 標準ライブラリのみで動作
- 気象庁の公式公開データを利用
- 神奈川県の週間予報と東部 / 西部の短期差分を同時表示
- 外部データの HTML エスケープ、リクエストタイムアウト、CSP などの基本対策を適用
- Render Blueprint と GitHub Actions によるデプロイ導線を同梱

## Local Setup

1. Python 3.13 前後を用意します
2. 仮想環境を作成します: `python -m venv .venv`
3. 有効化します: `source .venv/bin/activate`
4. 依存を入れます: `pip install -r requirements.txt`
5. サーバーを起動します: `python src/main.py`

起動後、`http://127.0.0.1:8000` を開いてください。

### Environment Variables

- `HOST`: リッスンアドレス。既定値は `0.0.0.0`
- `PORT`: リッスンポート。既定値は `8000`
- `WEATHER_CACHE_TTL_SECONDS`: 気象庁レスポンスのキャッシュ秒数。既定値は `900`
- `WEATHER_REQUEST_TIMEOUT_SECONDS`: 気象庁へのタイムアウト秒数。既定値は `10`

## Health Check

```bash
curl http://127.0.0.1:8000/healthz
```

## Tests

```bash
python -m compileall src tests
python -m unittest discover -s tests -v
```

## Render Deployment

`render.yaml` で Web Service を Blueprint 管理します。

1. Render でこのリポジトリから Blueprint を作成します
2. `render.yaml` のサービス名、ブランチ、プランを確認します
3. サービス作成後、Render の Deploy Hook URL を取得します
4. Render 側に個別の Git auto-deploy 設定が見える場合は無効化します

アプリの起動コマンドは次です。

```bash
python src/main.py
```

## GitHub Actions Deployment

含まれる workflow:

- `.github/workflows/ci.yml`: Pull Request と `master` push 用の compile + unit test
- `.github/workflows/deploy.yml`: CI 成功後、検証済みの commit SHA を指定して Render へデプロイ

GitHub 側の事前設定:

1. `production` environment を作成する
2. environment secret `RENDER_DEPLOY_HOOK_URL` を設定する
3. environment variable `RENDER_SERVICE_URL` を設定する
4. `production` environment に required reviewers を設定する
5. 必要なら `master` の branch protection も有効化する

`deploy.yml` は Render Deploy Hook に `?ref=<CIで検証済みSHA>` を付けて呼ぶため、CI 後に `master` が進んでも未検証コミットを誤って本番に出しにくくしています。

## Data Sources

- `https://www.jma.go.jp/bosai/forecast/data/forecast/140000.json`
- `https://www.jma.go.jp/bosai/forecast/data/overview_forecast/140000.json`
