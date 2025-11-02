# 📋 Planning Documents

このディレクトリには、プロジェクトの実装計画ドキュメントが含まれています。

## ディレクトリ構造

```
plans/
├── README.md                           # このファイル
├── yyyy-mm-dd-plan-name.md             # 進行中の計画
└── completed/                          # 完了した計画
    └── yyyy-mm-dd-plan-name.md
```

## ディレクトリの目的

- 実装前の計画・提案を保存
- 過去の意思決定の記録
- 実装済み項目の参照資料

## ファイル命名規則

```
yyyy-mm-dd-<plan-name>.md
```

**例:**
- `2025-11-01-improvement-plan.md`
- `2025-12-01-frontend-proposal.md`

## 計画一覧

### 2025-11-02: API Refactoring Plan
**[2025-11-02-api-refactoring-plan.md](2025-11-02-api-refactoring-plan.md)**

chat_api.py (1109行) をRouter分割し、Clean Architectureに近づける3段階リファクタリング計画。

**ステータス:** 📝 提案中

**フェーズ:**
- Phase 1: Router分割 (即効性★★★) - 4-8時間
- Phase 2: Service層抽出 (設計改善★★★) - 8-16時間
- Phase 3: Domain層整備 (Clean Architecture★★★★★) - 16-24時間

**期待効果:**
- 1ファイル最大行数: 1109 → ~250行 (Phase 1)
- 可読性: +50%, 保守性: +70%
- テスト容易性: 低 → 高
- 新規参画障壁: -60%

**優先度:** High (Phase 1即時着手推奨)

---

## 計画のライフサイクル

1. **📝 計画中** - `plans/` 直下に配置
2. **🚧 実装中** - `plans/` 直下に配置（計画ドキュメントを参照しながら実装）
3. **✅ 完了** - `plans/completed/` へ移動
4. **📚 ガイド作成** - 必要に応じて `guide/` にユーザー向けドキュメントを作成

## ワークフロー

### 計画作成時
```bash
# plans/ 直下に新規計画を作成
plans/2025-11-01-improvement-plan.md
```

### 実装完了時
```bash
# completed/ へ移動
mv plans/2025-11-01-improvement-plan.md plans/completed/
```

## 注意事項

- 完了した計画も削除せず、`completed/` ディレクトリで保持
- 計画の変更履歴はGit履歴で管理
- 実装後のユーザー向けドキュメントは `guide/` ディレクトリへ
- `completed/` 内の計画は参照資料として活用
