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

### 2025-11-01: 改善実装計画
**[2025-11-01-improvement-plan.md](2025-11-01-improvement-plan.md)**

プロジェクトを「研究試作→安定運用」へ移行するためのTOP8改善項目。

**ステータス:** 📝 計画中

**内容:**
- テスト体系の整備
- CI/CDパイプライン
- 環境変数の完全化
- 型チェック導入
- 構造化ログ
- 例外クラス階層化
- 入力バリデーション
- API Key認証

**実装期間:** 4-5日

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
