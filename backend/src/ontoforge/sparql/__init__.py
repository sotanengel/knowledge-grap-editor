"""SPARQL endpoint support: the read-only guard (§9.2, §13)."""

from ontoforge.sparql.guard import QueryForm, SparqlRejectedError, ensure_read_only, is_read_only

__all__ = ["QueryForm", "SparqlRejectedError", "ensure_read_only", "is_read_only"]
