"""Product catalog REST endpoints — list, photo, add, edit."""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response

from ..models import Product, ProductUpdate
from ..deps import verify_admin_token
from .. import db

router = APIRouter()


@router.get("/products")
def list_products():
    rows = db.list_products()
    products = []
    for p in rows:
        has_image = p.pop("has_image")
        p["image_url"] = f"/products/{p['id']}/photo" if has_image else None
        products.append(p)
    return products


@router.get("/products/{product_id}/photo")
def get_product_photo(product_id: int):
    result = db.get_product_image(product_id)
    if not result:
        raise HTTPException(status_code=404, detail="No photo for this product")
    data, mimetype = result
    return Response(content=data, media_type=mimetype)


@router.post("/products/", dependencies=[Depends(verify_admin_token)])
def add_product(product: Product):
    product_id = db.create_product(
        product.name, product.price, product.category, product.description
    )
    return {
        "product_id": product_id,
        "name": product.name,
        "price": product.price,
        "category": product.category,
        "description": product.description,
    }


@router.patch("/products/{product_id}", dependencies=[Depends(verify_admin_token)])
def edit_product(product_id: int, update: ProductUpdate):
    updated = db.update_product(
        product_id,
        name=update.name,
        price=update.price,
        category=update.category,
        description=update.description,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated