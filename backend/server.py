from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import asyncio
from services.mexc_service import mexc_service
from services.price_tracker import price_tracker


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

class PriceChange(BaseModel):
    price_change: float
    percent_change: float
    seconds_ago: int
    old_price: float
    current_price: float

class CandleData(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: float
    start_time: str
    end_time: str
    timestamp: int

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
    change_15s: Optional[PriceChange] = None
    change_30s: Optional[PriceChange] = None
    candles: List[CandleData] = Field(default_factory=list)

class CryptoPricesResponse(BaseModel):
    data: Dict[str, CryptoPrice]
    timestamp: str
    count: int

# Список поддерживаемых тикеров
SUPPORTED_TICKERS = [
    "LTCUSDT", "SHIBUSDT", "AVAXUSDT", "LINKUSDT", "BCHUSDT",
    "ATOMUSDT", "XMRUSDT", "APTUSDT", "FILUSDT", "NEARUSDT"
]

# Фоновая задача для сбора данных
background_task_running = False

async def background_price_collection():
    """Фоновая задача для сбора ценовых данных"""
    global background_task_running
    background_task_running = True
    
    logger.info("Starting background price collection...")
    
    while background_task_running:
        try:
            # Получаем данные от MEXC
            raw_data = await mexc_service.get_multiple_tickers(SUPPORTED_TICKERS)
            
            # Обновляем трекер цен
            for symbol, ticker_data in raw_data.items():
                if 'error' not in ticker_data:
                    try:
                        price = float(ticker_data.get("lastPrice", 0))
                        volume = float(ticker_data.get("volume", 0))
                        price_tracker.add_price_point(symbol, price, volume)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid price data for {symbol}")
            
            logger.debug("Background price collection completed")
            
        except Exception as e:
            logger.error(f"Error in background price collection: {str(e)}")
        
        # Ждем 2 секунды перед следующим обновлением
        await asyncio.sleep(2)

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
        "supported_tickers": SUPPORTED_TICKERS,
        "background_task_running": background_task_running
    }

@api_router.get("/crypto/prices", response_model=CryptoPricesResponse)
async def get_crypto_prices():
    """
    Получить актуальные цены всех поддерживаемых криптовалют с короткими интервалами
    """
    try:
        # Получаем данные от MEXC API
        raw_data = await mexc_service.get_multiple_tickers(SUPPORTED_TICKERS)
        
        # Получаем данные из трекера цен
        tracked_data = price_tracker.get_all_symbols_data()
        
        # Форматируем данные
        formatted_data = {}
        for symbol, ticker_data in raw_data.items():
            # Базовые данные от MEXC
            formatted_ticker = mexc_service.format_ticker_data(ticker_data)
            
            # Дополняем данными из трекера
            if symbol in tracked_data:
                track_data = tracked_data[symbol]
                formatted_ticker.update({
                    "change_15s": track_data.get("change_15s"),
                    "change_30s": track_data.get("change_30s"),
                    "candles": track_data.get("candles", [])
                })
            
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
        
        # Получаем данные из трекера цен
        tracked_data = price_tracker.get_all_symbols_data()
        
        # Форматируем данные
        formatted_data = mexc_service.format_ticker_data(raw_data)
        
        # Дополняем данными из трекера
        if symbol.upper() in tracked_data:
            track_data = tracked_data[symbol.upper()]
            formatted_data.update({
                "change_15s": track_data.get("change_15s"),
                "change_30s": track_data.get("change_30s"),
                "candles": track_data.get("candles", [])
            })
        
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

@api_router.get("/crypto/candles/{symbol}")
async def get_candles(symbol: str, limit: int = 20):
    """
    Получить свечные данные для символа
    """
    try:
        if symbol.upper() not in SUPPORTED_TICKERS:
            raise HTTPException(
                status_code=400, 
                detail=f"Symbol {symbol} not supported"
            )
        
        candles = price_tracker.get_candles(symbol.upper(), limit)
        
        return {
            "symbol": symbol.upper(),
            "candles": candles,
            "count": len(candles),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching candles for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch candles for {symbol}: {str(e)}"
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
    
    # Запускаем фоновую задачу сбора данных
    asyncio.create_task(background_price_collection())
    
    # Планируем очистку старых данных каждые 10 минут
    async def cleanup_task():
        while True:
            await asyncio.sleep(600)  # 10 минут
            try:
                price_tracker.cleanup_old_data()
                logger.info("Old data cleanup completed")
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
    
    asyncio.create_task(cleanup_task())

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка ресурсов при завершении работы"""
    global background_task_running
    background_task_running = False
    
    logger.info("MEXC Crypto Screener API shutting down...")
    await mexc_service.close_session()
    client.close()