FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY kg_mcp ./kg_mcp

RUN pip install --no-cache-dir ".[dev]"

EXPOSE 8080

CMD ["python", "-m", "kg_mcp.server"]
