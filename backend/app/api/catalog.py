
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import PriceRequest
from ..services.catalog.loader import get_shoe, load_components, load_shoes, shoe_with_options
from ..services.catalog.pricing import price_configuration

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/shoes")
def list_shoes() -> dict:
    return {"shoes": load_shoes()}


@router.get("/shoes/{slug}")
def get_shoe_detail(slug: str) -> dict:
    shoe = get_shoe(slug)
    if shoe is None:
        raise HTTPException(404, "shoe model not found")
    return shoe_with_options(shoe)


@router.get("/components")
def list_components() -> dict:
    return load_components()


@router.post("/price")
def price(payload: PriceRequest) -> dict:
    shoe = get_shoe(payload.shoe_slug)
    if shoe is None:
        raise HTTPException(404, "shoe model not found")
    return price_configuration(shoe, payload.selections).to_dict()
