# API Refactoring Plan: chat_api.py分割

**作成日**: 2025-11-02
**ステータス**: 提案中
**優先度**: High
**推定工数**: Phase 1: 4-8時間, Phase 2: 8-16時間, Phase 3: 16-24時間

---

## 📊 現状分析

### chat_api.pyの実態

```bash
総行数: 1,109行
関数/デコレータ数: 80個
APIエンドポイント数: 37+個
```

### エンドポイント内訳

| カテゴリ | エンドポイント数 | 例 |
|---------|----------------|-----|
| コアAPI | 3個 | `/search`, `/ask`, `/generate` |
| 統計 | 13個 | `/stats/*`, `/dashboard` |
| カナリー管理 | 6個 | `/admin/canary/*` |
| インシデント管理 | 7個 | `/admin/incidents/*` |
| バックアップ管理 | 7個 | `/admin/backup/*` |
| キャッシュ管理 | 1個 | `/admin/cache/*` |

### 問題点

1. **God Object化**: 1ファイルに6層の責務が集中
   - ① APIルーティング層
   - ② 業務ロジック層
   - ③ モデル管理層
   - ④ キャッシュ・レート制御層
   - ⑤ モニタリング・A/Bテスト層
   - ⑥ 管理・運用層

2. **可読性の低下**: 1000行超えで変更の影響範囲が不明確

3. **テスト困難**: 関数が`@app`デコレータに直接紐付き、単体テスト困難

4. **保守性の低下**: 同様の処理が複数箇所に散在（search/ask/generate）

---

## 🎯 3段階リファクタリング計画

### Phase 1: Router分割 ⭐ 即効性★★★

**目的**: 責務ごとにファイル分割し、可読性を向上

#### ターゲット構成

```
wp_chat/api/
├── __init__.py
├── main.py                 # FastAPIアプリ本体 (~50行)
├── dependencies.py         # 共通Depends/認証 (~100行)
├── errors.py              # 例外ハンドラ (~50行)
├── middleware.py          # CORS/logging (~50行)
└── routers/
    ├── __init__.py
    ├── chat.py            # /search, /ask, /generate (~200行)
    ├── stats.py           # /stats/*, /dashboard (~250行)
    ├── admin_canary.py    # /admin/canary/* (~150行)
    ├── admin_incidents.py # /admin/incidents/* (~200行)
    ├── admin_backup.py    # /admin/backup/* (~200行)
    └── admin_cache.py     # /admin/cache/* (~50行)
```

#### main.py の構造

```python
from fastapi import FastAPI
from .routers import chat, stats, admin_canary, admin_incidents, admin_backup, admin_cache
from .middleware import setup_middleware
from .errors import setup_error_handlers

def create_app() -> FastAPI:
    app = FastAPI(title="WordPress RAG Chatbot")

    # Setup middleware
    setup_middleware(app)

    # Setup error handlers
    setup_error_handlers(app)

    # Include routers
    app.include_router(chat.router, tags=["Chat"])
    app.include_router(stats.router, prefix="/stats", tags=["Stats"])
    app.include_router(admin_canary.router, prefix="/admin/canary", tags=["Admin-Canary"])
    app.include_router(admin_incidents.router, prefix="/admin/incidents", tags=["Admin-Incidents"])
    app.include_router(admin_backup.router, prefix="/admin/backup", tags=["Admin-Backup"])
    app.include_router(admin_cache.router, prefix="/admin/cache", tags=["Admin-Cache"])

    return app

app = create_app()
```

#### 移行優先順位

| 優先度 | Router | 理由 | 推定工数 |
|--------|--------|------|----------|
| 🔥 High | `chat.py` | コアビジネスロジック、使用頻度最高 | 2-3h |
| 🔥 High | `admin_backup.py` | 運用安全性に直結 | 1-2h |
| 🟡 Medium | `stats.py` | 独立性高い、影響範囲小 | 1-2h |
| 🟢 Low | `admin_*` その他 | 使用頻度低い、後回しOK | 各1h |

#### 実装手順

1. **routers/chat.py 作成** (最優先)
   ```python
   from fastapi import APIRouter, Request
   from ..models import SearchRequest, SearchResponse

   router = APIRouter()

   @router.post("/search", response_model=SearchResponse)
   async def search_endpoint(req: SearchRequest, request: Request):
       # 既存のsearch処理を移動
       ...
   ```

2. **テスト実行**
   ```bash
   pytest tests/integration/test_api_endpoints.py -v
   ```

3. **段階的移行**: 他のrouterも同様に移行

4. **旧chat_api.py削除**: 全移行完了後

---

### Phase 2: Service層抽出 ⭐ 設計改善★★★

**目的**: 業務ロジックをAPI層から分離し、テスタビリティ向上

#### ターゲット構成

```
wp_chat/
├── api/
│   └── routers/
│       └── chat.py        # 薄いAPI層（validation + call service）
└── services/              # 新規作成
    ├── __init__.py
    ├── search_service.py  # 検索ロジック集約
    ├── generation_service.py  # 生成ロジック
    └── cache_service.py      # キャッシュ制御
```

#### Before / After 比較

**Before (chat_api.py内):**
```python
@app.post("/search")
async def search_endpoint(req: SearchRequest):
    # 100行の検索ロジック...
    qv = model.encode(q, normalize_embeddings=True).astype("float32")
    D, I = index.search(np.expand_dims(qv, 0), topk)
    # スコア計算...
    # レート制限...
    # キャッシュ処理...
    return results
```

**After (router + service):**
```python
# api/routers/chat.py
@router.post("/search")
async def search_endpoint(
    req: SearchRequest,
    search_service: SearchService = Depends(get_search_service)
):
    results = await search_service.execute_search(req)
    return results

# services/search_service.py
class SearchService:
    def __init__(self, cache_manager, rate_limiter):
        self.cache_manager = cache_manager
        self.rate_limiter = rate_limiter

    async def execute_search(self, req: SearchRequest) -> SearchResponse:
        # キャッシュチェック
        cached = self.cache_manager.get(req.query)
        if cached:
            return cached

        # 検索実行
        results = self._perform_search(req)

        # キャッシュ保存
        self.cache_manager.set(req.query, results)

        return results

    def _perform_search(self, req):
        # 検索ロジック（テスト可能）
        ...
```

#### メリット

- ✅ 単体テストが容易（mockを使った検証）
- ✅ 責務の明確化（API層 vs ビジネスロジック）
- ✅ 再利用性向上（CLIからも同じserviceを使用可能）

---

### Phase 3: Domain層整備 ⭐ Clean Architecture完成★★★★★

**目的**: ドメインモデルを明確化し、完全なClean Architecture実現

#### ターゲット構成

```
wp_chat/
├── api/              # Presentation Layer
│   └── routers/
├── services/         # Application Layer
│   └── search_service.py
├── domain/           # Domain Layer (新規)
│   ├── models/
│   │   ├── search_result.py
│   │   ├── generation_result.py
│   │   └── document.py
│   ├── repositories/
│   │   ├── search_repository.py
│   │   └── cache_repository.py
│   └── value_objects/
│       ├── query.py
│       └── score.py
├── core/             # Infrastructure Layer
└── retrieval/        # Infrastructure Layer
```

#### Domain Model例

```python
# domain/models/search_result.py
from dataclasses import dataclass
from typing import List

@dataclass
class SearchResult:
    """検索結果のドメインモデル"""
    query: str
    documents: List['Document']
    total_results: int
    took_ms: int

    def get_top_n(self, n: int) -> List['Document']:
        """上位N件を取得"""
        return self.documents[:n]

    def filter_by_score(self, min_score: float) -> 'SearchResult':
        """スコアでフィルタリング"""
        filtered = [d for d in self.documents if d.score >= min_score]
        return SearchResult(
            query=self.query,
            documents=filtered,
            total_results=len(filtered),
            took_ms=self.took_ms
        )

@dataclass
class Document:
    """ドキュメントのドメインモデル"""
    id: int
    title: str
    content: str
    url: str
    score: float

    def is_relevant(self, threshold: float = 0.7) -> bool:
        """関連性判定"""
        return self.score >= threshold
```

#### Repository Pattern例

```python
# domain/repositories/search_repository.py
from abc import ABC, abstractmethod
from typing import List
from ..models.search_result import SearchResult

class SearchRepository(ABC):
    """検索リポジトリの抽象"""

    @abstractmethod
    async def search(self, query: str, topk: int) -> SearchResult:
        """検索実行"""
        pass

# retrieval/faiss_search_repository.py
from wp_chat.domain.repositories.search_repository import SearchRepository

class FAISSSearchRepository(SearchRepository):
    """FAISS実装"""

    async def search(self, query: str, topk: int) -> SearchResult:
        # FAISS検索ロジック
        ...
        return SearchResult(...)
```

#### メリット

- ✅ ビジネスルールがドメイン層に集約
- ✅ インフラ技術（FAISS, Redis等）の変更が容易
- ✅ テストカバレッジの向上
- ✅ 新規メンバーの理解速度向上

---

## 📈 効果試算

| 指標 | Before | Phase 1 | Phase 2 | Phase 3 |
|------|--------|---------|---------|---------|
| **1ファイル最大行数** | 1109 | ~250 | ~150 | ~100 |
| **責務の明確度** | 20% | 60% | 80% | 95% |
| **テスト容易性** | 低 | 中 | 高 | 最高 |
| **変更影響範囲** | 全体 | 局所 | 最小 | 最小 |
| **新規参画者の理解速度** | 3日 | 1日 | 0.5日 | 0.5日 |
| **保守コスト** | 100% | 60% | 40% | 30% |

---

## ⚠️ リスクとトレードオフ

### デメリット

1. **初期工数**:
   - Phase 1: 4-8時間
   - Phase 2: 8-16時間
   - Phase 3: 16-24時間

2. **循環参照リスク**: import地獄に陥る可能性

3. **過剰設計のリスク**: 小規模プロジェクトには不要

### 対策

- ✅ **段階的移行**: 一度に全部やらない
- ✅ **テスト駆動**: 移行前後でテストカバレッジ維持
- ✅ **ドキュメント更新**: アーキテクチャ図を同時更新
- ✅ **依存関係図**: importの方向性を明確化

---

## 🚀 実装ロードマップ

### Step 1: Phase 1実装 (即時着手推奨)

**Week 1-2**

```bash
□ Day 1-2: routers/chat.py 分離
  - /search, /ask, /generate の3エンドポイント移動
  - テスト実行・動作確認

□ Day 3: routers/stats.py 分離
  - 全statsエンドポイント移動

□ Day 4: admin系router分離
  - canary, incidents, backup, cache

□ Day 5: main.py 整備
  - 全routerの統合
  - middleware/errors分離

□ Day 6-7: テスト・ドキュメント更新
```

**マイルストーン**: 全エンドポイントがRouter化、テスト全pass

---

### Step 2: Phase 2実装 (Phase 1完了後)

**Week 3-4**

```bash
□ Week 3: Service層作成
  - SearchService
  - GenerationService
  - CacheService

□ Week 4: Router→Service移行
  - 各routerからサービス呼び出しに変更
  - 単体テスト作成
```

**マイルストーン**: ビジネスロジックがService層に集約

---

### Step 3: Phase 3実装 (任意・長期)

**Month 2-3**

```bash
□ Month 2: Domain層設計
  - モデル定義
  - Repository抽象化

□ Month 3: 段階的移行
  - Service→Domain移行
  - Infrastructure層整備
```

**マイルストーン**: Clean Architecture完成

---

## ✅ 成功基準

### Phase 1

- [ ] 全エンドポイントがrouter化
- [ ] chat_api.pyが削除可能
- [ ] 既存テストが全pass
- [ ] 新規router用テスト作成

### Phase 2

- [ ] 主要ビジネスロジックがService化
- [ ] Service層の単体テストカバレッジ80%以上
- [ ] API層が100行以下/ファイル

### Phase 3

- [ ] Domain層が確立
- [ ] Repository Patternで技術依存が抽象化
- [ ] アーキテクチャ図が更新

---

## 📚 参考資料

### FastAPI公式パターン

- [Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)

### Clean Architecture

- Robert C. Martin "Clean Architecture"
- [The Clean Architecture (blog)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

### Repository Pattern

- Martin Fowler "Patterns of Enterprise Application Architecture"

---

## 📞 次のアクション

1. **このPlanをレビュー**
2. **Phase 1着手の承認**
3. **担当者アサイン**
4. **実装開始 → PR → レビュー → マージ**

---

**最終更新**: 2025-11-02
**ドキュメントバージョン**: 1.0
