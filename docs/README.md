🗓️ 2025/11/03 [Monday] 18:00

---

# **📘 WordPress RAG Chatbot — Development Report (Retrieval Phase)**

---

## 🧭 プロジェクト概要（Overview）

**プロジェクト名**：WordPress RAG Chatbot（wp-chat）
**目的**：WordPress上のブログ記事をAIが自ら検索・理解し、ユーザーに根拠付きで回答する
**RAG（Retrieval-Augmented Generation）構造**を実装する。

本レポートは2025年11月時点の開発進捗をまとめたものであり、
RAGの第1フェーズ「Retrieval（検索）」の設計・実装・検証内容を中心に記録する。

---

## 🌐 完成イメージ（最終目標）

```
┌─────────────────────────────┐
│        User (質問する)        │
└────────────┬────────────────┘
             │
             ▼
┌───────────API───────────┐
│ FastAPIエンドポイント (/search, /generate) │
└───────────┬───────────┘
             │
             ▼
┌─────────Service──────────┐
│ 検索ロジック＋再ランキング処理           │
└─────────┬──────────┘
             │
             ▼
┌─────────Retrieval─────────┐
│ BM25（キーワード検索）＋FAISS（意味検索） │
│ Cross-Encoderによる再スコアリング          │
└─────────┬──────────┘
             │
             ▼
┌───────────Domain───────────┐
│ Query・Document・SearchResult モデル      │
└────────────────────────────┘
             │
             ▼
┌───────────Generation───────────┐
│ OpenAI GPT-4o（生成・引用付き応答）      │
└───────────────────────────────┘
```

---

## 🧩 開発の全体構成（RAG構造の3フェーズ）

| フェーズ               | 内容                 | 目的             | 状況         |
| ------------------ | ------------------ | -------------- | ---------- |
| **R：Retrieval**    | WordPressデータを検索・抽出 | 「どの情報を使うか」を決める | 🟢 実装＋テスト中 |
| **A：Augmentation** | 検索結果を文脈として整形       | 「どう文脈を作るか」を決める | 🟡 準備中     |
| **G：Generation**   | OpenAIで最終回答を生成     | 「どう答えるか」を作る    | ⚪️ 今後      |

---

## 🔍 現在の進捗（Retrievalフェーズ）

Retrievalフェーズでは、「AIが正確に情報を探し出せる基盤」を作ることに集中している。
主な作業内容は以下の通り。

### ✅ 完了済み項目

| 項目                     | 状況 | 補足                              |
| ---------------------- | -- | ------------------------------- |
| **WordPressデータ取得**     | ✅  | API経由で記事データを取得、自動保存             |
| **テキスト整形・チャンク化**       | ✅  | HTML除去・分割・正規化を実装                |
| **BM25／FAISSインデックス構築** | ✅  | 検索の両軸（キーワード＋意味）対応               |
| **Hybrid Search統合**    | ✅  | dense＋sparse＋Cross-Encoder統合完了  |
| **Domain層設計**          | ✅  | Query／Document／SearchResult定義完了 |
| **pytestテスト設計**        | 🚧 | 検索精度と再現性のテストを構築中                |
| **OpenAI連携**           | ⏳  | Augmentation以降で統合予定             |

---

## 🧠 アーキテクチャ構造（Architecture Overview）

```
User
  │
  ▼
FastAPI (/search, /ask, /generate)
  │
  ▼
Service層（search_service）
  │
  ▼
Domain層（Query, Document, SearchResult）
  │
  ▼
Retrieval層（BM25 / FAISS / Cross-Encoder）
  │
  ▼
Data層（WordPressデータ）
```

| 層             | 役割                   |
| ------------- | -------------------- |
| **API**       | 外部リクエストの受付・レスポンス処理   |
| **Service**   | ビジネスロジック・検索操作        |
| **Domain**    | モデル定義とロジック整合性の保持     |
| **Retrieval** | 実際の検索・再ランキング処理       |
| **Data**      | WordPressからの情報取得・前処理 |

---

## 📈 成果と評価

### 主な成果

* 検索パイプライン（BM25＋FAISS＋Reranker）を統合
* Domain層によりクリーンな依存関係を確立
* Router分割・Service抽出・Domain整備の3フェーズを全完了
* pytestによる自動テスト体制を開始

### 検証課題

* FAISSとBM25のスコア統合精度
* 検索クエリの異常値対策（XSS・空文字等）
* テストカバレッジ80%以上の達成

---

## 🔭 今後の開発方針（Next Steps）

### **Step 1：Retrievalフェーズ完了**

* 検索精度・異常値テストを強化
* pytest＋GitHub Actionsで自動化

### **Step 2：Augmentationフェーズ**

* 検索結果の要約・統合（context trimming）
* Promptテンプレート（`prompts.py`）構築
* Context window制御（トークン管理）

### **Step 3：Generationフェーズ**

* OpenAI GPT-4o統合
* 引用付き回答（`[[1]]`）生成
* Streaming出力対応

---

## 💬 考察（Discussion）

Kazumiは、**「R → A → G」の正しい順序**でRAG構築を進めており、
特にRetrieval層を丁寧に作り込むことで、後のA/Gフェーズの品質を高めている。

> *“AIに話す力を与える前に、
> 正しく探す力を育てる。”*
> — この設計思想が、プロジェクトの核。

---

## 🪶 現在地のまとめ（Summary）

| フェーズ                | 状況          | 備考             |
| ------------------- | ----------- | -------------- |
| **R（Retrieval）**    | 🟢 実装＋テスト中  | 検索基盤構築の最重要フェーズ |
| **A（Augmentation）** | 🟡 次フェーズ準備中 | 文脈整形とprompt構築へ |
| **G（Generation）**   | ⚪️ 今後       | OpenAI API統合予定 |

---

## 📚 Vocabulary List（英日）

| English                              | Japanese         |
| ------------------------------------ | ---------------- |
| RAG (Retrieval-Augmented Generation) | 検索拡張生成           |
| Retrieval                            | 検索（情報取得）         |
| Augmentation                         | 文脈補強・情報統合        |
| Generation                           | 回答生成             |
| Hybrid Search                        | ハイブリッド検索         |
| Cross-Encoder                        | 再ランキングモデル        |
| Context trimming                     | 文脈抽出／要約          |
| Prompt engineering                   | プロンプト設計          |
| Clean Architecture                   | クリーンアーキテクチャ      |
| pytest                               | Pythonテストフレームワーク |
