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
  reasoning/    ルールベース推論（none / rdfs / rl-lite）＋導出根拠
  validation/   SHACL シェイプ生成と pySHACL 検証
  vocab/        同梱語彙（schema.org / SKOS / FOAF / DCTERMS / PROV-O / OWL / RDFS）
  mcp/          MCP 読み取り専用サーバー
  api/          FastAPI（REST・SPARQL・SSE・/mcp）
frontend/       React 18 + TypeScript + Vite + Tailwind CSS
docs/           設計書
```

## 起動

### Docker（推奨）

```bash
docker run -d --name ontoforge -p 8080:8080 -v "$(pwd)/data:/data" ghcr.io/sotanengel/knowledge-grap-editor:latest
```

- UI: `http://localhost:8080`
- MCP エンドポイント: `http://localhost:8080/mcp`

コンテナは**非 root** で動作し、書き込み可能なのは `/data` のみです。
読み取り専用ルートファイルシステムで動かす場合:

```bash
docker run -d --name ontoforge -p 127.0.0.1:8080:8080 --read-only --tmpfs /tmp -v "$(pwd)/data:/data" ghcr.io/sotanengel/knowledge-grap-editor:latest
```

### ソースから

```bash
uv run ontoforge serve
```

既定で `127.0.0.1:8080` にのみバインドします。LAN へ公開する場合は
`--host` を明示し、あわせて `ONTOFORGE_AUTH_TOKEN` を設定してください。

同梱語彙の読み込み:

```bash
uv run ontoforge load-vocab
```

## MCP（AI からの参照）

**MCP は完全な読み取り専用です。** 更新系ツールは存在せず、ストアは書き込みを
拒否し、SPARQL は実行前にパースして更新句を弾きます（三重防御、P4）。

### Streamable HTTP

```json
{
  "mcpServers": {
    "ontoforge": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

`/mcp` は**読み取り専用のハンドル**で開いたストアを見ます。stdio は別プロセス
なので pyoxigraph の `Store.read_only` をそのまま使い、同一プロセスの HTTP
マウントは（生きた DB に 2 本目のハンドルを開くのが未定義動作のため）同じ
ハンドルを読み取り専用ラッパー越しに共有します。どちらも書き込みは届きません。

### stdio

```json
{
  "mcpServers": {
    "ontoforge": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-v", "./data:/data", "ghcr.io/sotanengel/knowledge-grap-editor:latest", "mcp-stdio"]
    }
  }
}
```

| ツール | 内容 |
|---|---|
| `search_entities` | ラベル全文検索 |
| `get_entity` | CBD を Turtle で（IRI にラベル併記） |
| `list_classes` | クラス階層とインスタンス数 |
| `list_properties` | プロパティ一覧（定義域・値域つき） |
| `describe_ontology` | オントロジー全体の自然言語サマリ |
| `get_neighbors` | 近傍サブグラフ |
| `find_path` | ノード間の最短経路 |
| `sparql_select` | SELECT / ASK / CONSTRUCT / DESCRIBE のみ |
| `validate_graph` | SHACL 検証結果 |
| `explain_inference` | 導出トリプルの根拠（適用ルールと前提） |

Resources は `ontoforge://ontology/schema.ttl` / `summary.md` / `graphs` /
`examples/queries.md`、Prompts は `explore_entity` / `build_sparql` /
`extract_to_kg` を公開します。

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
| `POST` | `/api/v1/reason` | 推論を実行し `inferred` グラフを再構築 |
| `GET` | `/api/v1/reason/profiles` | `none` / `rdfs` / `rl-lite` と適用ルール |
| `POST` | `/api/v1/reason/explain` | 導出トリプルの根拠 |
| `POST` | `/api/v1/validate` | SHACL 検証。違反ごとに修正候補を返す |
| `GET/PUT/DELETE` | `/api/v1/shapes/{name}` | SHACL シェイプの管理 |
| `GET/POST` | `/api/v1/vocabularies` | 同梱語彙の一覧と読み込み |
| `POST` | `/mcp` | MCP Streamable HTTP（**読み取り専用**） |
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

## 推論と検証

推論は**前向き連鎖で有限回停止する範囲**に限ります（§10.1）。記述論理の
充足可能性判定は行わず、外部推論器も別コンテナも不要です。

| プロファイル | 適用ルール |
|---|---|
| `none` | 推論なし |
| `rdfs`（既定） | `subClassOf` / `subPropertyOf` の推移閉包、`domain` / `range` からの型付与 |
| `rl-lite` | 上記 ＋ `inverseOf` / `TransitiveProperty` / `SymmetricProperty` / `equivalentClass` / `equivalentProperty` / `sameAs` |

導出トリプルは `urn:ontoforge:inferred` に書き出され、**適用ルール名と前提
トリプル**を併せて記録します。UI と MCP の `explain_inference` から参照できます。

クラス式からの分類、カーディナリティ矛盾検出、`disjointWith` の充足可能性判定は
**行いません**。それらが必要な検証は SHACL で代替してください（§10.2）。

## Phase 1 受け入れ確認

```bash
./scripts/e2e_phase1.sh
```

空の状態から 50 ノードの KG を作り、Turtle で出力し、MCP から `search_entities`
と `sparql_select` で参照でき、`INSERT` が拒否されることを確認します。

## バックアップ

`/data` をコピーすれば完結します。`snapshots/*.trig` は単体で可搬な完全ダンプ
なので、Git リポジトリに置いて差分管理する運用を推奨します。

## ライセンス

[Apache License 2.0](LICENSE)
