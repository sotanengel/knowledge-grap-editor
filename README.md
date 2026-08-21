# OntoForge

ローカル環境のブラウザ上でオントロジー（TBox）とナレッジグラフ（ABox）を直感的に作成・編集し、
その成果物を **MCP（Model Context Protocol）経由で AI エージェントが読み取り専用で参照**できる
オーサリングツールです。

設計書は [docs/system-definition.md](docs/system-definition.md) を参照してください。

## 設計原則

| # | 原則 |
|---|---|
| P1 | 標準準拠（RDF / OWL / SHACL / SPARQL）、UI で隠蔽 |
| P2 | 単一コンテナ・単一コマンド起動 |
| P3 | ファイルが正（Portable）。ロックインしない |
| P4 | AI は読み取り専用 |
| P5 | 小さく作る |

## 構成

```
backend/src/ontoforge/
  config.py     設定（ONTOFORGE_* 環境変数 / config.yaml）
  cli.py        `ontoforge serve` / `ontoforge info`
  store/        pyoxigraph ラッパ・名前付きグラフ・IRI 採番・read-only ハンドル
  changelog/    RDF Patch 追記ログ・スナップショット・復元
  entities.py   インスタンス CRUD（TBox に従う事実）
  ontology.py   クラス／プロパティ定義とリネーム
  search/       SQLite FTS5 全文検索
  sparql/       読み取り専用ガード
  io/           インポート／エクスポート（RDF・CSV・GraphML・Mermaid）
  rdfstar.py    RDF 1.2 三重項によるエッジ属性
  api/          FastAPI（REST・SPARQL・SSE）
frontend/       React 18 + TypeScript + Vite + Tailwind CSS
docs/           設計書
```

## 起動

```bash
uv run ontoforge serve
```

既定で `127.0.0.1:8080` にのみバインドします。LAN へ公開する場合は
`--host` を明示し、あわせて `ONTOFORGE_AUTH_TOKEN` を設定してください。

## API

すべて `/api/v1` 配下。SPARQL のみプロトコル準拠のため `/sparql` に置きます。

| Method | パス | 説明 |
|---|---|---|
| `GET` | `/api/v1/health` | 稼働確認とストア統計 |
| `GET` | `/api/v1/entities?q=&type=&limit=&offset=` | ラベル全文検索 |
| `POST` | `/api/v1/entities` | インスタンス作成（IRI は ULID で自動採番） |
| `GET` | `/api/v1/entities/{iri}?depth=` | CBD を JSON-LD で返す |
| `PATCH` | `/api/v1/entities/{iri}` | 差分更新。IRI は動かない |
| `DELETE` | `/api/v1/entities/{iri}` | ノードと関連トリプルを削除 |
| `GET` | `/api/v1/ontology` | クラス階層とプロパティ一覧 |
| `POST` | `/api/v1/ontology/classes` / `/properties` | 語彙定義の追加 |
| `GET` | `/api/v1/ontology/properties?domain=` | 定義域に合う候補プロパティ |
| `POST` | `/api/v1/ontology/rename` | 用語のリネーム（参照を一括更新） |
| `GET/POST` | `/sparql` | SPARQL 1.1 Query。更新句はパース段階で拒否 |
| `POST` | `/sparql/update` | SPARQL Update（UI セッション用） |
| `POST` | `/api/v1/import` | Turtle / TriG / N-Triples / N-Quads / RDF-XML / JSON-LD / CSV |
| `GET` | `/api/v1/export?format=&graphs=` | 上記 RDF 各形式 + GraphML / CSV / Mermaid |
| `GET/PUT/DELETE` | `/api/v1/mappings/{name}` | CSV マッピングの保存と再利用 |
| `GET` | `/api/v1/history` / `POST /history/undo` / `redo` | 変更履歴と取り消し |
| `GET` | `/api/v1/events` | SSE。変更を他クライアントへプッシュ |

対話的なドキュメントは起動後 `http://127.0.0.1:8080/docs` にあります。

データはすべて `ONTOFORGE_DATA_DIR`（既定 `/data`）配下に置かれます。

```
/data
  store/       RDF ストア実体
  snapshots/   *.trig 定期スナップショット
  changelog/   追記型パッチログ (RDF Patch)
  index/       全文検索インデックス
  config.yaml  設定
```

## 開発

### 前提

- Python 3.12（`uv` が自動で用意します）
- Node.js 22 以上 / pnpm 10 以上

### セットアップ

```bash
uv sync --extra dev
```

```bash
pnpm -C frontend install
```

### チェック

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```

```bash
pnpm -C frontend lint && pnpm -C frontend test && pnpm -C frontend build
```

### pre-commit

```bash
uv run pre-commit install
```

## Takumi Guard（Shisho）

パッケージ取得はサプライチェーン保護のため Takumi Guard のプロキシ経由に固定しています。
**トークンはリポジトリに含めません。** 各開発者・各 CI で環境変数として与えてください。

npm 側（`.npmrc` はレジストリのみを指定）:

```bash
pnpm config set //npm.flatt.tech/:_authToken "$TAKUMI_GUARD_TOKEN"
```

PyPI 側（`pyproject.toml` の `[[tool.uv.index]]` はインデックス URL のみを指定）:

```bash
export UV_INDEX_TAKUMI_GUARD_USERNAME=token
```

```bash
export UV_INDEX_TAKUMI_GUARD_PASSWORD="$TAKUMI_GUARD_TOKEN"
```

トークン未設定でも匿名モードで動作し、ブロック対象パッケージは 403 で拒否されます。

### 設定の確認

```bash
pnpm -C frontend add @panda-guard/test-malicious
```

`403 Forbidden` で失敗すれば設定は正しく効いています。

## 環境変数

| 変数 | 既定値 | 説明 |
|---|---|---|
| `ONTOFORGE_BASE_IRI` | `https://example.org/kg/` | 生成 IRI のベース |
| `ONTOFORGE_DATA_DIR` | `/data` | 永続化ディレクトリ |
| `ONTOFORGE_AUTH_TOKEN` | （空＝認証なし） | LAN へ露出させる場合のみ設定 |
| `ONTOFORGE_REASONER` | `rdfs` | `none` / `rdfs` / `rl-lite` |
| `ONTOFORGE_REASONER_MAX_ITER` | `20` | 前向き連鎖の最大反復回数 |
| `ONTOFORGE_QUERY_TIMEOUT_MS` | `10000` | SPARQL タイムアウト |

## ライセンス

[Apache License 2.0](LICENSE)
