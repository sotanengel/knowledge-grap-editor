from fastapi import HTTPException

from app.models.schemas import ValidationWarning


def raise_if_blocked(warnings: list[ValidationWarning], should_block: bool) -> None:
    if should_block and warnings:
        payload = {"warnings": [w.model_dump() for w in warnings]}
        raise HTTPException(status_code=422, detail=payload)
