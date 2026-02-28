import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Deal Aggregator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DealResponse(BaseModel):
    id: str
    created_at: str
    product_name: str
    deal_price: Optional[float]
    original_price: Optional[float]
    link: str
    card_offer: Optional[str]
    platform: Optional[str]
    category: Optional[str]

@app.get("/deals", response_model=List[DealResponse])
def get_deals():
    try:
        response = supabase.table('deals').select('*').order('created_at', desc=True).limit(50).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deals/category/{category_name}", response_model=List[DealResponse])
def get_deals_by_category(category_name: str):
    try:
        response = supabase.table('deals').select('*').eq('category', category_name).order('created_at', desc=True).limit(50).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
