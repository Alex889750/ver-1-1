from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict
import uuid
from datetime import datetime
from services.mexc_service import mexc_service


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class CryptoPrice(BaseModel):
    symbol: str
    price: float
    change24h: float
    changePercent24h: float
    volume: float = 0
    high24h: float = 0
    low24h: float = 0
    timestamp: str
    source: str = "mexc"

class CryptoPricesResponse(BaseModel):
    data: Dict[str, CryptoPrice]
    timestamp: str
    count: int

# Список поддерживаемых тикеров
SUPPORTED_TICKERS = [
    "LTCUSDT", "SHIBUSDT", "AVAXUSDT", "LINKUSDT", "BCHUSDT",
    "ATOMUSDT", "XMRUSDT", "APTUSDT", "FILUSDT", "NEARUSDT"
]

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "MEXC Crypto Screener API"}

@api_router.get("/health")
async def health_check():
    """Проверка работоспособности API"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "supported_tickers": SUPPORTED_TICKERS
    }

@api_router.get("/crypto/prices", response_model=CryptoPricesResponse)
async def get_crypto_prices():
    """
    Получить актуальные цены всех поддерживаемых криптовалют
    """
    try:
        # Получаем данные от MEXC API
        raw_data = await mexc_service.get_multiple_tickers(SUPPORTED_TICKERS)
        
        # Форматируем данные
        formatted_data = {}
        for symbol, ticker_data in raw_data.items():
            formatted_ticker = mexc_service.format_ticker_data(ticker_data)
            formatted_data[symbol] = CryptoPrice(**formatted_ticker)
        
        response = CryptoPricesResponse(
            data=formatted_data,
            timestamp=datetime.utcnow().isoformat(),
            count=len(formatted_data)
        )
        
        return response
        
    except Exception as e:
        logging.error(f"Error fetching crypto prices: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch crypto prices: {str(e)}"
        )

@api_router.get("/crypto/price/{symbol}")
async def get_single_crypto_price(symbol: str):
    """
    Получить актуальную цену конкретной криптовалюты
    """
    try:
        # Проверяем, что символ поддерживается
        if symbol.upper() not in SUPPORTED_TICKERS:
            raise HTTPException(
                status_code=400, 
                detail=f"Symbol {symbol} not supported. Supported symbols: {SUPPORTED_TICKERS}"
            )
        
        # Получаем данные от MEXC API
        raw_data = await mexc_service.get_24hr_ticker(symbol.upper())
        
        # Форматируем данные
        formatted_data = mexc_service.format_ticker_data(raw_data)
        crypto_price = CryptoPrice(**formatted_data)
        
        return {
            "data": crypto_price,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching price for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch price for {symbol}: {str(e)}"
        )

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    logger.info("MEXC Crypto Screener API starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка ресурсов при завершении работы"""
    logger.info("MEXC Crypto Screener API shutting down...")
    await mexc_service.close_session()
    client.close()