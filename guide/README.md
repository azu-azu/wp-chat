# 📚 Documentation Guide

このフォルダには、WordPress RAG Chatbotの詳細なドキュメントが含まれています。

## 📋 ドキュメント一覧

### 🖥️ CLI実行ガイド
**[CLI_GUIDE.md](CLI_GUIDE.md)**

CLIツールの詳細な使用方法を説明します。

**内容:**
- 環境設定とセットアップ
- RAG生成テストの使用方法
- 全オプションの詳細説明
- トラブルシューティング
- パフォーマンス最適化
- 自動化スクリプト例

**対象者:**
- 開発者
- テスト担当者
- 運用担当者

### 🌐 APIエンドポイントガイド
**[API_GUIDE.md](API_GUIDE.md)**

APIエンドポイントの詳細な仕様と使用例を説明します。

**内容:**
- 全エンドポイントの仕様
- リクエスト/レスポンス例
- エラーハンドリング
- セキュリティ設定
- パフォーマンス最適化
- テスト例

**対象者:**
- API開発者
- フロントエンド開発者
- インテグレーション担当者

### 💾 バックアップ・復元ガイド
**[BACKUP_GUIDE.md](BACKUP_GUIDE.md)**

バックアップシステムの使用方法と復元手順を説明します。

**内容:**
- バックアップの種類と設定
- 自動バックアップのスケジュール
- 復元手順とベリフィケーション
- トラブルシューティング
- セキュリティ考慮事項

**対象者:**
- 運用担当者
- システム管理者
- 災害復旧担当者

### 🚨 インシデント対応ガイド
**[INCIDENT_RUNBOOK.md](INCIDENT_RUNBOOK.md)**

インシデント発生時の緊急対応手順を説明します。

**内容:**
- 緊急事態の種類別対応手順
- エスカレーション手順
- 監視とアラート設定
- 事後対応プロセス
- コミュニケーション手順

**対象者:**
- オンコールエンジニア
- 運用担当者
- インシデント対応チーム

### 🎯 MVP4実装サマリー
**[MVP4_SUMMARY.md](MVP4_SUMMARY.md)**

MVP4 RAG生成機能の実装内容と次のステップを説明します。

**内容:**
- 実装完了機能一覧
- アーキテクチャ概要
- 設定手順
- テスト方法
- 監視指標

**対象者:**
- 開発者
- プロジェクトマネージャー
- 技術リーダー

## 🚀 クイックスタート

### 1. CLI実行
```bash
# ヘルスチェック
python3 -m src.cli.generate_cli --health

# インタラクティブモード
python3 -m src.cli.generate_cli --interactive
```

### 2. API使用
```bash
# サーバー起動
uvicorn src.api.chat_api:app --reload --port 8080

# 生成テスト
curl -X POST http://localhost:8080/generate \
  -H 'Content-Type: application/json' \
  -d '{"question": "テスト質問", "stream": false}'
```

## 📖 ドキュメントの読み方

### 初心者の方
1. まず [MVP4_SUMMARY.md](MVP4_SUMMARY.md) で全体像を把握
2. [CLI_GUIDE.md](CLI_GUIDE.md) の「環境設定」セクションを読む
3. 「基本的な使用方法」で実際に試す
4. 問題があれば「トラブルシューティング」を参照

### 開発者の方
1. [MVP4_SUMMARY.md](MVP4_SUMMARY.md) で実装内容を確認
2. [API_GUIDE.md](API_GUIDE.md) でエンドポイント仕様を確認
3. 「レスポンス形式」でデータ構造を理解
4. 「テスト例」で実装を参考にする

### 運用担当者の方
1. [BACKUP_GUIDE.md](BACKUP_GUIDE.md) でバックアップ手順を確認
2. [INCIDENT_RUNBOOK.md](INCIDENT_RUNBOOK.md) で緊急対応手順を確認
3. [CLI_GUIDE.md](CLI_GUIDE.md) の「その他のCLIツール」を確認
4. 「パフォーマンス最適化」で設定を調整

### インシデント対応担当者の方
1. [INCIDENT_RUNBOOK.md](INCIDENT_RUNBOOK.md) の「緊急手順」を確認
2. 「エスカレーション手順」を理解
3. 「監視とアラート設定」で監視体制を整備
4. 「事後対応プロセス」で改善点を把握

## 🔧 設定ファイル

### 主要設定ファイル
- **[config.yml](../config.yml)** - アプリケーション設定
- **[pricing.json](../pricing.json)** - LLMモデル価格
- **[.env.example](../.env.example)** - 環境変数テンプレート

### 設定の優先順位
1. 環境変数
2. `.env` ファイル
3. `config.yml` ファイル
4. デフォルト値

## 🚨 トラブルシューティング

### よくある問題

#### インポートエラー
```bash
# 解決方法
cd /path/to/wp-chat
source .venv/bin/activate
```

#### API接続エラー
```bash
# 解決方法
export OPENAI_API_KEY="your-key-here"
python3 -m src.cli.generate_cli --health
```

#### インデックスエラー
```bash
# 解決方法
python -m src.data.build_index
```

### ログ確認
```bash
# アプリケーションログ
tail -f logs/app.log

# エラーログ
tail -f logs/error.log
```

## 📊 パフォーマンス指標

### SLO目標
- **TTFT**: ≤ 1.2秒
- **P95 Latency**: ≤ 6秒
- **Success Rate**: ≥ 98%
- **Citation Rate**: ≥ 90%

### 監視方法
```bash
# SLO確認
curl http://localhost:8080/stats/slo

# ダッシュボード
curl http://localhost:8080/dashboard
```

## 🔄 更新履歴

### v1.0.0 (2024-10-24)
- 初回ドキュメント作成
- CLI実行ガイド追加
- APIエンドポイントガイド追加
- トラブルシューティング情報追加

## 📞 サポート

### 問題報告
1. GitHub Issueを作成
2. ログファイルを添付
3. 再現手順を記載

### 改善提案
1. GitHub Issueで提案
2. Pull Requestで実装
3. ドキュメント更新

---

**Happy coding! 🚀**
