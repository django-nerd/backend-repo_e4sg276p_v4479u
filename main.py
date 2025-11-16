import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import Product as ProductSchema, Order as OrderSchema

app = FastAPI(title="Victus MC Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Victus MC Store Backend Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# ---------- Store Models for Requests ----------
class CreateOrderRequest(BaseModel):
    items: List[dict]
    buyer_email: Optional[str] = None
    buyer_username: Optional[str] = None
    note: Optional[str] = None

# ---------- Helper: Seed products if collection empty ----------
DEFAULT_PRODUCTS = [
    {
        "title": "VIP Rank",
        "description": "Purple tag, daily crate, /fly, and more perks.",
        "price": 9.99,
        "category": "ranks",
        "in_stock": True,
        "sku": "RANK_VIP",
        "image": "https://i.imgur.com/7gW5a8W.png",
        "badge": "Popular"
    },
    {
        "title": "MVP Rank",
        "description": "All VIP perks plus extra kits and boosters.",
        "price": 19.99,
        "category": "ranks",
        "in_stock": True,
        "sku": "RANK_MVP",
        "image": "https://i.imgur.com/3wM3q6B.png",
        "badge": "Best Value"
    },
    {
        "title": "Legend Rank",
        "description": "Ultimate status, cosmetics, and exclusive features.",
        "price": 39.99,
        "category": "ranks",
        "in_stock": True,
        "sku": "RANK_LEGEND",
        "image": "https://i.imgur.com/8F9mTnE.png",
        "badge": "Premium"
    },
    {
        "title": "Keys Bundle",
        "description": "10x Galaxy Crate Keys.",
        "price": 7.99,
        "category": "keys",
        "in_stock": True,
        "sku": "KEYS_GALAXY_10",
        "image": "https://i.imgur.com/0kCqf3L.png",
        "badge": None
    }
]

COLLECTION_PRODUCTS = "product"  # based on schema class name
COLLECTION_ORDERS = "order"

@app.get("/api/products")
def get_products():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    count = db[COLLECTION_PRODUCTS].count_documents({})
    if count == 0:
        # Seed defaults
        for p in DEFAULT_PRODUCTS:
            try:
                _ = create_document(COLLECTION_PRODUCTS, p)
            except Exception:
                pass
    products = get_documents(COLLECTION_PRODUCTS, {}, None)
    # Convert ObjectId and datetimes to strings
    for p in products:
        if "_id" in p:
            p["id"] = str(p.pop("_id"))
        if "created_at" in p:
            p["created_at"] = str(p["created_at"]) 
        if "updated_at" in p:
            p["updated_at"] = str(p["updated_at"]) 
    return {"items": products}

@app.post("/api/orders")
def create_order(payload: CreateOrderRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    items = []
    subtotal = 0.0
    if not payload.items:
        raise HTTPException(status_code=400, detail="No items in order")

    for item in payload.items:
        try:
            qty = int(item.get("quantity", 1))
            price = float(item.get("price"))
            title = item.get("title") or "Item"
            product_id = str(item.get("product_id") or "")
            if qty <= 0 or price < 0:
                continue
            subtotal += qty * price
            items.append({
                "product_id": product_id,
                "quantity": qty,
                "price": price,
                "title": title,
            })
        except Exception:
            continue

    if len(items) == 0:
        raise HTTPException(status_code=400, detail="Invalid items")

    order_doc = OrderSchema(
        items=items, 
        subtotal=round(subtotal, 2), 
        buyer_email=payload.buyer_email, 
        buyer_username=payload.buyer_username,
        note=payload.note
    )

    order_id = create_document(COLLECTION_ORDERS, order_doc)
    return {"ok": True, "order_id": order_id}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
