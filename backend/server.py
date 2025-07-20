from fastapi import FastAPI, APIRouter, HTTPException, Query
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
from services.mexc_service_optimized import optimized_mexc_service
from services.price_tracker_optimized import optimized_price_tracker
from config.tickers import SUPPORTED_TICKERS


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="MEXC Crypto Screener API - Optimized", version="2.0.0")

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
    total_available: int

class TickersListResponse(BaseModel):
    tickers: List[str]
    count: int
    timestamp: str

# Фоновая задача для сбора данных
background_task_running = False

async def background_price_collection():
    """Оптимизированная фоновая задача для сбора ценовых данных"""
    global background_task_running
    background_task_running = True
    
    logger.info(f"Starting optimized background price collection for {len(SUPPORTED_TICKERS)} tickers...")
    
    while background_task_running:
        try:
            # Получаем все данные одним запросом (намного эффективнее!)
            raw_data = await optimized_mexc_service.get_filtered_tickers(SUPPORTED_TICKERS)
            
            # Обновляем трекер цен
            valid_updates = 0
            for symbol, ticker_data in raw_data.items():
                if 'error' not in ticker_data:
                    try:
                        price = float(ticker_data.get("lastPrice", 0))
                        volume = float(ticker_data.get("volume", 0))
                        if price > 0:  # Только валидные цены
                            optimized_price_tracker.add_price_point(symbol, price, volume)
                            valid_updates += 1
                    except (ValueError, TypeError):
                        continue
            
            logger.debug(f"Updated {valid_updates}/{len(raw_data)} tickers successfully")
            
        except Exception as e:
            logger.error(f"Error in background price collection: {str(e)}")
        
        # Ждем 2 секунды перед следующим обновлением
        await asyncio.sleep(2)

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {
        "message": "MEXC Crypto Screener API - Optimized v2.0",
        "features": [
            "250+ tickers support",
            "Batch API optimization", 
            "Real-time candle charts",
            "Short-term price tracking",
            "Configurable display settings"
        ]
    }

@api_router.get("/health")
async def health_check():
    """Проверка работоспособности оптимизированного API"""
    active_symbols = optimized_price_tracker.get_active_symbols_count()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "total_supported_tickers": len(SUPPORTED_TICKERS),
        "active_symbols": active_symbols,
        "background_task_running": background_task_running,
        "optimization": "enabled"
    }

@api_router.get("/tickers", response_model=TickersListResponse)
async def get_supported_tickers():
    """Получить список всех поддерживаемых тикеров"""
    return TickersListResponse(
        tickers=SUPPORTED_TICKERS,
        count=len(SUPPORTED_TICKERS),
        timestamp=datetime.utcnow().isoformat()
    )

@api_router.get("/crypto/prices", response_model=CryptoPricesResponse)
async def get_crypto_prices(
    limit: Optional[int] = Query(default=30, ge=1, le=50, description="Number of tickers to return"),
    offset: Optional[int] = Query(default=0, ge=0, description="Offset for pagination"),
    sort_by: Optional[str] = Query(default="symbol", description="Sort by: symbol, price, change24h, changePercent24h, volume"),
    sort_order: Optional[str] = Query(default="asc", description="Sort order: asc, desc"),
    search: Optional[str] = Query(default=None, description="Search filter for symbol names")
):
    """
    Получить актуальные цены криптовалют с поддержкой пагинации, сортировки и поиска
    """
    try:
        # Получаем данные от MEXC API
        raw_data = await optimized_mexc_service.get_filtered_tickers(SUPPORTED_TICKERS)
        
        # Получаем данные из трекера цен
        tracked_data = optimized_price_tracker.get_symbols_batch_data(list(raw_data.keys()))
        
        # Форматируем данные
        formatted_data = []
        for symbol, ticker_data in raw_data.items():
            # Базовые данные от MEXC
            formatted_ticker = optimized_mexc_service.format_ticker_data(ticker_data)
            
            # Дополняем данными из трекера
            if symbol in tracked_data:
                track_data = tracked_data[symbol]
                formatted_ticker.update({
                    "change_15s": track_data.get("change_15s"),
                    "change_30s": track_data.get("change_30s"),
                    "candles": track_data.get("candles", [])
                })
            
            formatted_data.append((symbol, CryptoPrice(**formatted_ticker)))
        
        # Применяем поиск
        if search:
            search_upper = search.upper()
            formatted_data = [
                (symbol, data) for symbol, data in formatted_data 
                if search_upper in symbol or search_upper in symbol.replace('USDT', '')
            ]
        
        # Сортировка
        sort_key_map = {
            "symbol": lambda x: x[1].symbol,
            "price": lambda x: x[1].price,
            "change24h": lambda x: x[1].change24h,
            "changePercent24h": lambda x: x[1].changePercent24h,
            "volume": lambda x: x[1].volume,
        }
        
        if sort_by in sort_key_map:
            formatted_data.sort(
                key=sort_key_map[sort_by], 
                reverse=(sort_order.lower() == "desc")
            )
        
        # Пагинация
        total_available = len(formatted_data)
        paginated_data = formatted_data[offset:offset + limit]
        
        # Формируем финальный ответ
        result_data = {symbol: data for symbol, data in paginated_data}
        
        response = CryptoPricesResponse(
            data=result_data,
            timestamp=datetime.utcnow().isoformat(),
            count=len(result_data),
            total_available=total_available
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
        symbol_upper = symbol.upper()
        if not symbol_upper.endswith('USDT'):
            symbol_upper += 'USDT'
            
        if symbol_upper not in SUPPORTED_TICKERS:
            raise HTTPException(
                status_code=400, 
                detail=f"Symbol {symbol} not supported. Use /tickers endpoint to see all supported symbols."
            )
        
        # Получаем данные от MEXC API
        all_data = await optimized_mexc_service.get_filtered_tickers([symbol_upper])
        raw_data = all_data.get(symbol_upper, {})
        
        # Получаем данные из трекера цен
        tracked_data = optimized_price_tracker.get_symbols_batch_data([symbol_upper])
        
        # Форматируем данные
        formatted_data = optimized_mexc_service.format_ticker_data(raw_data)
        
        # Дополняем данными из трекера
        if symbol_upper in tracked_data:
            track_data = tracked_data[symbol_upper]
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
    logger.info("MEXC Crypto Screener API v2.0 starting up...")
    logger.info(f"Configured {len(SUPPORTED_TICKERS)} tickers for tracking")
    
    # Запускаем фоновую задачу сбора данных
    asyncio.create_task(background_price_collection())
    
    # Планируем очистку старых данных каждые 10 минут
    async def cleanup_task():
        while True:
            await asyncio.sleep(600)  # 10 минут
            try:
                optimized_price_tracker.cleanup_old_data()
                logger.info("Old data cleanup completed")
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
    
    asyncio.create_task(cleanup_task())

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка ресурсов при завершении работы"""
    global background_task_running
    background_task_running = False
    
    logger.info("MEXC Crypto Screener API v2.0 shutting down...")
    await optimized_mexc_service.close_session()
    client.close()