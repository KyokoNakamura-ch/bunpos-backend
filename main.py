from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from pydantic import BaseModel
import mysql.connector
import os
from dotenv import load_dotenv

# .env 読み込み
load_dotenv()

# ✅ FastAPIのインスタンスをまず作る！
app = FastAPI()

# ✅ CORS設定をそのあとに追加！
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# .env 読み込み
load_dotenv()

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

@app.get("/product")
def get_product_by_code(code: str):
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            ssl_ca=os.getenv("SSL_CA_PATH")
        )
        cursor = conn.cursor(dictionary=True)

        # ✅ カラム名・テーブル名を実際に合わせたよ！
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

@app.post("/order")
def register_order(order: OrderRequest):
    try:
        # ✅ 接続前にログ出して確認
        print("Connecting to DB with:")
        print("HOST:", os.getenv("DB_HOST"))
        print("USER:", os.getenv("DB_USER"))
        print("DB  :", os.getenv("DB_NAME"))
        print("SSL :", os.getenv("SSL_CA_PATH"))

        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            ssl_ca=os.getenv("SSL_CA_PATH")
        )
        print("✅ 接続成功")

        cursor = conn.cursor()

        # 注文テーブルに追加
        cursor.execute(
            "INSERT INTO 取引 (DATETIME, EMP_CD, STORE_CD, POS_NO, TOTAL_AMT) VALUES (NOW(), %s, %s, %s, %s)",
            (order.empCd, order.storeCd, order.posNo, order.totalAmount)
        )
        trd_id = cursor.lastrowid

        # 注文明細を追加
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
        print("❌ エラー発生：", e)
        return {"error": str(e)}

