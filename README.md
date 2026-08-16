# オントロジー対応ナレッジグラフ Web アプリ

ローカル環境でナレッジグラフを作成・編集・検索できる Web アプリケーションです。オントロジー（型・Relationship）による意味の統一と、MCP 経由の AI 連携をサポートします。

## 機能（MVP）

- ナレッジグラフの可視化（Cytoscape.js）
- ノード / エッジ CRUD
- オントロジー（Class / Relationship / Property）管理
- 型サジェスト（label / description / alias ベース）
- Domain / Range バリデーション（警告モード）
- RDF Export（Turtle / N-Triples / JSON-LD / RDF/XML）
- MCP Server（search_nodes, get_node, get_neighbors, get_schema 等）

## 起動方法

```bash
docker compose up -d
```

- Web UI: http://127.0.0.1:3000
- Backend API: http://127.0.0.1:8000
- MCP Server: http://127.0.0.1:8080

## 開発

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
pytest -v
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
npm run test
```

### MCP

```bash
cd mcp
python3.12 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
pytest -v
```

## MCP 接続（Cursor / Claude Desktop）

`mcp.json` に以下を追加:

```json
{
  "mcpServers": {
    "knowledge-graph": {
      "url": "http://127.0.0.1:8080/sse"
    }
  }
}
```

### 利用可能な Tool

| Tool | 説明 |
|------|------|
| `search_nodes` | キーワードでノード検索 |
| `get_node` | ノード詳細取得 |
| `get_neighbors` | 周辺グラフ取得 |
| `search_by_type` | 型指定検索 |
| `get_schema` | オントロジー全体取得 |
| `find_relationship` | 2 ノード間の関係探索 |

## データ永続化

`./data` ディレクトリに Oxigraph データベースが保存されます。Docker 再起動後もデータは保持されます。

## テスト

```bash
./scripts/smoke-test.sh
```

## アーキテクチャ

```
Browser → Frontend (React) → Backend (FastAPI) → Oxigraph
                                    ↑
                              MCP Server
                                    ↑
                              Generative AI
```

オントロジーとナレッジグラフデータは Named Graph（`urn:kg:ontology` / `urn:kg:data`）で分離管理されます。
