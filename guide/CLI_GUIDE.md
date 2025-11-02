# CLI実行ガイド

このドキュメントでは、WordPress RAG ChatbotのCLIツールの使用方法を詳しく説明します。

## 📋 目次

- [環境設定](#環境設定)
- [RAG生成テスト](#rag生成テスト)
- [その他のCLIツール](#その他のcliツール)
- [トラブルシューティング](#トラブルシューティング)

## 🔧 環境設定

### 1. 仮想環境の有効化
```bash
source .venv/bin/activate
```

### 2. 環境変数の設定
```bash
export OPENAI_API_KEY="sk-proj-your-openai-api-key-here"
```

または `.env` ファイルに設定：
```bash
# .env
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
WP_BASE_URL=https://your-blog.example.com
```

## 🚀 RAG生成テスト

### 基本的な使用方法

#### ヘルスチェック
```bash
python3 -m src.cli.generate_cli --health
```
**出力例:**
```
🏥 Checking OpenAI API health...
Status: healthy
✅ Model: gpt-4o-mini
✅ Latency: 3289ms
```

#### 単発質問
```bash
python3 -m src.cli.generate_cli "VBAで文字列の処理方法を教えて"
```

#### インタラクティブモード（推奨）
```bash
python3 -m src.cli.generate_cli --interactive
```
**使用例:**
```
Entering interactive mode. Type 'exit' or 'quit' to end.
Q: VBAで文字列の処理方法を教えて
A: [ストリーミング応答が表示される]
Q: exit
```

### オプション一覧

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--topk TOPK` | 取得する文書数 | 5 |
| `--no-stream` | ストリーミングを無効化 | false |
| `--mode {dense,bm25,hybrid}` | 検索モード | hybrid |
| `--rerank` | リランキングを有効化 | false |
| `--health` | API接続確認 | - |
| `--interactive` | インタラクティブモード | - |

### 使用例

#### 1. 基本的な質問
```bash
python3 -m src.cli.generate_cli "プライバシーポリシーについて教えて"
```

#### 2. 検索モード指定
```bash
# Dense検索のみ
python3 -m src.cli.generate_cli "質問" --mode dense

# BM25検索のみ
python3 -m src.cli.generate_cli "質問" --mode bm25

# ハイブリッド検索（デフォルト）
python3 -m src.cli.generate_cli "質問" --mode hybrid
```

#### 3. リランキング有効
```bash
python3 -m src.cli.generate_cli "質問" --rerank
```

#### 4. 取得文書数指定
```bash
python3 -m src.cli.generate_cli "質問" --topk 10
```

#### 5. ストリーミング無効
```bash
python3 -m src.cli.generate_cli "質問" --no-stream
```

#### 6. 複数オプション組み合わせ
```bash
python3 -m src.cli.generate_cli "質問" --topk 8 --mode hybrid --rerank
```

### 出力の見方

#### ストリーミング出力
```
🔍 Testing generation for: 'VBAで文字列の処理方法を教えて'
📊 Parameters: topk=3, stream=True, mode=hybrid, rerank=False
------------------------------------------------------------
📝 Context processed: 2 chunks, 53 tokens
💬 Prompt built: 279 tokens

🌊 Streaming response:
----------------------------------------

⚡ TTFT: 1994ms, Model: gpt-4o-mini
根拠資料が不足しています。VBAでの文字列処理に関する具体的な情報は提供されていません。

📊 Final metrics:
   Total latency: 2319ms
   Tokens: 0
   Success: True

📚 References:
   [1] Sample Document 1
        https://example.com/doc1
   [2] Sample Document 2
        https://example.com/doc2

✅ Citations found: 0
✅ Response valid: True
```

#### 各項目の説明
- **TTFT**: Time to First Token（初回応答時間）
- **Total latency**: 全体の処理時間
- **Tokens**: 使用トークン数
- **Success**: 成功/失敗
- **Citations found**: 引用数
- **Response valid**: 応答の妥当性

## 🛠️ その他のCLIツール

### バックアップ管理
```bash
python3 -m src.cli.backup_cli --help
```

**主要コマンド:**
```bash
# バックアップ作成
python3 -m src.cli.backup_cli create

# バックアップ一覧
python3 -m src.cli.backup_cli list

# バックアップ復元
python3 -m src.cli.backup_cli restore <backup_id>

# バックアップ削除
python3 -m src.cli.backup_cli delete <backup_id>
```

### カナリーデプロイ管理
```bash
python3 -m src.cli.canary_cli --help
```

**主要コマンド:**
```bash
# カナリー状態確認
python3 -m src.cli.canary_cli status

# カナリー有効化
python3 -m src.cli.canary_cli enable

# カナリー無効化
python3 -m src.cli.canary_cli disable

# ロールアウト率設定
python3 -m src.cli.canary_cli rollout 25
```

### インシデント管理
```bash
python3 -m src.cli.incident_cli --help
```

**主要コマンド:**
```bash
# インシデント状態確認
python3 -m src.cli.incident_cli status

# インシデント検出
python3 -m src.cli.incident_cli detect

# 緊急手順実行
python3 -m src.cli.incident_cli execute <incident_id>

# インシデント解決
python3 -m src.cli.incident_cli resolve <incident_id>
```

## 🚨 トラブルシューティング

### よくある問題と解決方法

#### 1. インポートエラー
**エラー:**
```
ModuleNotFoundError: No module named 'src'
```

**解決方法:**
```bash
# プロジェクトルートにいることを確認
pwd
# /Users/mypc/AI_develop/wp-chat であることを確認

# 仮想環境を有効化
source .venv/bin/activate
```

#### 2. OpenAI API エラー
**エラー:**
```
ValueError: OPENAI_API_KEY environment variable is required
```

**解決方法:**
```bash
# APIキーを設定
export OPENAI_API_KEY="sk-proj-your-key-here"

# または .env ファイルに設定
echo "OPENAI_API_KEY=sk-proj-your-key-here" >> .env
```

#### 3. インデックスが見つからない
**エラー:**
```
FileNotFoundError: data/index/wp.faiss
```

**解決方法:**
```bash
# インデックスを再構築
python -m wp_chat.data.build_index
```

#### 4. ポート競合
**エラー:**
```
OSError: [Errno 48] Address already in use
```

**解決方法:**
```bash
# 既存のプロセスを終了
pkill -f uvicorn

# 新しいサーバーを起動
uvicorn wp_chat.api.main:app --reload --port 8080
```

#### 5. 依存関係エラー
**エラー:**
```
ImportError: No module named 'openai'
```

**解決方法:**
```bash
# 依存関係を再インストール
pip install -r requirements.txt
```

### デバッグ方法

#### 1. 詳細ログ出力
```bash
# 環境変数でログレベルを設定
export LOG_LEVEL=DEBUG
python3 -m src.cli.generate_cli --health
```

#### 2. 設定確認
```bash
# 設定ファイルの内容確認
python3 -c "from wp_chat.core.config import load_config; import json; print(json.dumps(load_config(), indent=2))"
```

#### 3. インデックス状態確認
```bash
# インデックスファイルの存在確認
ls -la data/index/
```

## 📊 パフォーマンス最適化

### 推奨設定

#### 開発環境
```bash
# 軽量設定
python3 -m src.cli.generate_cli "質問" --topk 3 --mode dense
```

#### 本番環境
```bash
# 高品質設定
python3 -m src.cli.generate_cli "質問" --topk 8 --mode hybrid --rerank
```

### メモリ使用量の最適化

#### 1. チャンクサイズ調整
`config.yml`で調整：
```yaml
generation:
  chunk_max_tokens: 800  # デフォルト: 1000
  max_chunks: 3          # デフォルト: 5
```

#### 2. 検索モード選択
- **dense**: 高速、低メモリ
- **bm25**: 中速、中メモリ
- **hybrid**: 低速、高メモリ

## 🔄 自動化

### スクリプト例

#### バッチ処理スクリプト
```bash
#!/bin/bash
# batch_test.sh

questions=(
    "VBAで文字列の処理方法を教えて"
    "プライバシーポリシーについて"
    "お問い合わせ方法"
)

for question in "${questions[@]}"; do
    echo "Testing: $question"
    python3 -m src.cli.generate_cli "$question" --topk 5
    echo "---"
done
```

#### ヘルスチェックスクリプト
```bash
#!/bin/bash
# health_check.sh

echo "Checking API health..."
python3 -m src.cli.generate_cli --health

if [ $? -eq 0 ]; then
    echo "✅ API is healthy"
else
    echo "❌ API is unhealthy"
    exit 1
fi
```

## 📞 サポート

問題が解決しない場合：

1. **ログ確認**: `logs/` ディレクトリのログファイルを確認
2. **GitHub Issue**: 問題を報告
3. **設定確認**: `config.yml` と `.env` の設定を確認
4. **依存関係確認**: `pip list` でパッケージ一覧を確認

---

**Happy coding! 🚀**
