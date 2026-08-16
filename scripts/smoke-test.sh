#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Backend tests"
cd backend && python3.12 -m venv .venv 2>/dev/null || true
.venv/bin/pip install -q ".[dev]"
.venv/bin/pytest -v

echo "==> MCP tests"
cd "$ROOT/mcp"
python3.12 -m venv .venv 2>/dev/null || true
.venv/bin/pip install -q ".[dev]"
.venv/bin/pytest -v

echo "==> Frontend tests"
cd "$ROOT/frontend"
npm install -q
npm run test
npm run build

echo "==> Docker build"
cd "$ROOT"
docker compose build

echo "==> All smoke tests passed"
