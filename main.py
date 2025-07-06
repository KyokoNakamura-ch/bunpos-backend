from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from pydantic import BaseModel
import os
from datetime import datetime

# .env 読み込み（ローカル用）
from dotenv import load_dotenv
load_dotenv()

# Supabaseクライアント
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("SUPABASE_URL または SUPABASE_ANON_KEY が環境変数に見つかりません")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# FastAPIインスタンス作成
app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# モデル定義
class OrderItem(BaseModel):
    detailId: int
    code: str
    name: str
    price: int

class OrderRequest(BaseModel):
    items: List[OrderItem]
    totalAmount: int
    empCd: str = "999999999"
    storeCd: str = "30"
    posNo: str = "90"

# 商品取得API
@app.get("/product")
def get_product_by_code(code: str):
    try:
        code = code.strip()
        print(f"🔍 検索コード: [{code}]")
        response = (
            supabase.table("product_master")
            .select("name, price")
            .ilike("code", code)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]  # limit(1)なので1件のみ
        else:
            return JSONResponse(status_code=404, content={"message": "商品が見つかりません"})
    except Exception as e:
        print("❌ 商品取得エラー:", e)
        return JSONResponse(status_code=500, content={"message": str(e)})

# 注文登録API
@app.post("/order")
def register_order(order: OrderRequest):
    try:
        now = datetime.utcnow().isoformat()

        # 取引登録
        trd_result = supabase.table("transactions").insert({
            "datetime": now,
            "emp_cd": order.empCd,
            "store_cd": order.storeCd,
            "pos_no": order.posNo,
            "total_amt": order.totalAmount
        }).execute()

        trd_id = trd_result.data[0]["id"]

        # 明細登録
        for item in order.items:
            supabase.table("transaction_details").insert({
                "transaction_id": trd_id,
                "detail_id": item.detailId,
                "product_code": item.code,
                "product_name": item.name,
                "product_price": item.price
            }).execute()

        return {"message": "注文を登録しました", "orderId": trd_id}

    except Exception as e:
        print("❌ 注文登録エラー:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
