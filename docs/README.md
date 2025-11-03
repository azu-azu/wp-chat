🗓️ 2025/11/04 [Tuesday] (JST)

---

# **📘 WordPress RAG Chatbot — Development Report (Retrieval Phase Complete)**

---

## 🎯 要約（Summary）

**結局、どういうことか：**

WordPressのブログ記事を読み込んで、ユーザーの質問に対して「記事を根拠にした回答」をAIが生成するシステムを作っている。現在は、**「どの記事のどの部分が質問に関連しているか」を正確に検索する仕組み**（Retrievalフェーズ）を実装中。

**現在の状況：**
- ✅ 検索エンジン（BM25キーワード検索 + FAISS意味検索 + 再ランキング）完成
- ✅ 包括的なテスト体制確立（251テスト、93%カバレッジ達成）
- ✅ Retrievalフェーズ完了、次フェーズ準備完了
- ⏳ AI回答生成は未実装（次のフェーズ）

**設計思想：**
> *"AIに話す力を与える前に、正しく探す力を育てる。"*

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

**RAG = 検索（Retrieval）→ 文脈整形（Augmentation）→ 回答生成（Generation）**

| フェーズ               | 何をするか                 | 目的             | 状況         |
| ------------------ | ------------------ | -------------- | ---------- |
| **R：Retrieval**    | 質問に関連する記事を検索して抽出 | 「どの情報を使うか」を決める | ✅ 完了（テスト含む） |
| **A：Augmentation** | 検索結果をAIに渡す文脈として整形       | 「どう文脈を作るか」を決める | 🟡 準備完了     |
| **G：Generation**   | OpenAIで最終回答を生成     | 「どう答えるか」を作る    | ⏳ 次フェーズ      |

**現在の重点：** Rフェーズを丁寧に作り込むことで、後の品質を確保する設計方針。

---

## 🔍 現在の進捗（Retrievalフェーズ）

**やっていること：** 「AIが正確に情報を探し出せる基盤」を作る。

### ✅ 完了済み項目

| 項目                     | 状況 | 補足                              |
| ---------------------- | -- | ------------------------------- |
| **WordPressデータ取得**     | ✅  | API経由で記事データを取得、自動保存             |
| **テキスト整形・チャンク化**       | ✅  | HTML除去・分割・正規化を実装                |
| **BM25／FAISSインデックス構築** | ✅  | 検索の両軸（キーワード＋意味）対応               |
| **Hybrid Search統合**    | ✅  | dense＋sparse＋Cross-Encoder統合完了  |
| **Domain層設計**          | ✅  | Query／Document／SearchResult定義完了 |
| **Clean Architectureテスト** | ✅  | **251テスト、93%カバレッジ達成**（Domain 100%, Services 94-100%） |
| **OpenAI連携**           | ⏳  | Augmentation以降で統合予定             |

**検索の仕組み：**
- **BM25**：キーワードマッチング（「Python」で検索 → 「Python」を含む記事を探す）
- **FAISS**：意味検索（「プログラミング言語」で検索 → 「Python」や「Ruby」の記事も見つかる）
- **Cross-Encoder**：検索結果を再ランキングして精度向上

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

## 📈 成果と課題

### ✅ 主な成果

* 検索パイプライン（BM25＋FAISS＋Reranker）を統合
* Domain層によりクリーンな依存関係を確立
* **包括的なテスト体制確立**
  * 251単体テスト実装（Domain層 163テスト、Service層 88テスト）
  * **93%テストカバレッジ達成**（目標80%を超過）
  * Domain Models/Value Objects: 100%カバレッジ
  * Services: 94-100%カバレッジ
* FAISSとBM25のスコア統合精度の調整完了
* 検索クエリの異常値対策（XSS・空文字等）実装

### 🎯 達成した品質基準

* ✅ テストカバレッジ 93%（目標80%超過達成）
* ✅ Domain層 100%カバレッジ（Value Objects + Models）
* ✅ Service層 94-100%カバレッジ（mocking完備）
* ✅ エッジケース網羅（Unicode、空値、境界条件）
* ✅ CI/CD準備完了（pre-commit hooks統合）

---

## 🔭 今後の開発方針（Next Steps）

### **Step 1：Retrievalフェーズ完了** ✅ 完了
* ✅ 検索精度・異常値テストを強化完了
* ✅ pytest＋pre-commit hooksで自動化完了
* ✅ 251テスト、93%カバレッジ達成
* ✅ Clean Architecture基盤確立

### **Step 2：Augmentationフェーズ** 🟢 次のフェーズ
* 検索結果の要約・統合（context trimming）
* Promptテンプレート構築
* Context window制御（トークン管理）
* 検索結果 → AI入力形式への変換

### **Step 3：Generationフェーズ** 🟡 準備中
* OpenAI GPT-4o統合
* 引用付き回答（`[[1]]`）生成
* Streaming出力対応
* SLO監視・メトリクス収集

---

## 💬 設計思想（Philosophy）

**「R → A → G」の正しい順序**でRAG構築を進める。特にRetrieval層を丁寧に作り込むことで、後のA/Gフェーズの品質を高める。

> *"AIに話す力を与える前に、正しく探す力を育てる。"*

---

## 🪶 現在地のまとめ（Current Status）

| フェーズ                | 状況          | 備考                       |
| ------------------- | ----------- | ------------------------ |
| **R（Retrieval）**    | ✅ 完了       | 検索基盤構築完了、93%テストカバレッジ達成  |
| **A（Augmentation）** | 🟢 次フェーズ    | 文脈整形とprompt構築へ移行準備完了    |
| **G（Generation）**   | 🟡 準備中      | OpenAI API統合予定（基盤整備完了） |

### 📊 テスト品質メトリクス

| メトリクス          | 達成値        | 目標値   | 状態 |
| -------------- | ---------- | ----- | -- |
| テストカバレッジ（全体）   | **93%**    | 80%   | ✅  |
| Domain層カバレッジ   | **100%**   | 80%   | ✅  |
| Service層カバレッジ  | **94-100%** | 80%   | ✅  |
| 単体テスト総数        | **251**    | 200+  | ✅  |
| Value Objectsテスト | 55         | -     | ✅  |
| Domain Modelsテスト | 108        | -     | ✅  |
| Servicesテスト     | 88         | -     | ✅  |

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
