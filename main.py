from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from pydantic import BaseModel
import mysql.connector
import os

# ✅ ローカル開発時のみ .env を読み込む（AzureではApp Serviceの環境変数を使う）
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

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

# 共通：MySQL接続関数（SSLの有無を切り替え）
def get_connection():
    ssl_ca_path = os.getenv("SSL_CA_PATH")
    conn_args = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "use_pure": True,           # ← 追加
        "unix_socket": None         # ← 追加（パイプ接続を防ぐ）
    }
    if ssl_ca_path:
        conn_args["ssl_ca"] = ssl_ca_path

    return mysql.connector.connect(**conn_args)

# 商品取得API
@app.get("/product")
def get_product_by_code(code: str):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT name, price FROM product_master WHERE code = %s", (code,))
        row = cursor.fetchone()

        cursor.close()
        conn.close()

        if row:
            return row
        else:
            return JSONResponse(status_code=404, content={"message": "商品が見つかりません"})

    except Exception as e:
        print("❌ 商品取得エラー:", e)
        return JSONResponse(status_code=500, content={"message": str(e)})

# 注文登録API
@app.post("/order")
def register_order(order: OrderRequest):
    try:
        print("Connecting to DB with:", os.getenv("DB_HOST"))

        conn = get_connection()
        cursor = conn.cursor()

        # 注文登録
        cursor.execute(
            "INSERT INTO 取引 (DATETIME, EMP_CD, STORE_CD, POS_NO, TOTAL_AMT) VALUES (NOW(), %s, %s, %s, %s)",
            (order.empCd, order.storeCd, order.posNo, order.totalAmount)
        )
        trd_id = cursor.lastrowid

        for item in order.items:
            cursor.execute(
                "INSERT INTO 取引明細 (TRD_ID, DTL_ID, PRD_CODE, PRD_NAME, PRD_PRICE) VALUES (%s, %s, %s, %s, %s)",
                (trd_id, item.detailId, item.code, item.name, item.price)
            )

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "注文を登録しました", "orderId": trd_id}

    except Exception as e:
        print("❌ 注文登録エラー:", e)
        return {"error": str(e)}


