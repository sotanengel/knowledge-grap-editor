from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import edges, export, graph, nodes, ontology
from app.config import settings

app = FastAPI(title="Knowledge Graph API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nodes.router)
app.include_router(edges.router)
app.include_router(ontology.router)
app.include_router(graph.router)
app.include_router(export.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "validation_mode": settings.validation_mode}
