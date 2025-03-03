# 確定申告用TTMレート換算アプリケーション

このアプリケーションは、みずほ銀行のTTM（Telegraphic Transfer Middle）レートを使用して、USD取引を自動的にJPYに換算し、確定申告をサポートするツールです。

## 主な機能

- **TTMデータの自動取得**: みずほ銀行の為替レートを自動的に取得・保存
- **CSVアップロード・処理**: 取引履歴のCSVファイルをアップロードして自動換算
- **分析・レポート**: 月次・年次の収入サマリーを表示
- **エクスポート機能**: 結果をCSVまたはHTML/PDFで出力
- **ダークモード対応**: ライト/ダークテーマの切り替えが可能

## 技術スタック

### フロントエンド
- React
- TypeScript
- Tailwind CSS
- Chart.js（データの可視化）
- Lucide React（アイコン）

### バックエンド
- Python with FastAPI
- Pandas（データ処理）
- SQLite（データストレージ）
- APScheduler（バックグラウンドタスク）

## 始め方

### 必要条件
- Node.js
- Python 3.8以上
- npmまたはyarn

### インストール手順

1. リポジトリをクローン
2. フロントエンドの依存関係をインストール：
   ```
   npm install
   ```
3. バックエンドの依存関係をインストール：
   ```
   cd api
   pip install -r requirements.txt
   ```

### アプリケーションの実行

1. バックエンドサーバーの起動：
   ```
   cd api
   python main.py
   ```

2. フロントエンド開発サーバーの起動：
   ```
   npm run dev
   ```

3. ブラウザで`http://localhost:5173`にアクセス

## CSVファイルの要件

アプリケーションは以下のカラムを含むCSVファイルを想定しています：
- `Transaction Date`: 取引日（pandasで解析可能な形式）
- `Credit amount`: 取引金額（USD）

## ライセンス

このプロジェクトは個人利用を目的としています。 