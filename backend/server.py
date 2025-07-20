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
from services.price_tracker_advanced import advanced_price_tracker
from config.tickers import SUPPORTED_TICKERS


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="MEXC TradingView Screener API", version="3.0.0")

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
    timeframe: str

class CryptoPrice(BaseModel):
    symbol: str
    price: float
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
    """Продвинутая фоновая задача для сбора ценовых данных с поддержкой множественных таймфреймов"""
    global background_task_running
    background_task_running = True
    
    logger.info(f"Starting advanced background price collection for {len(SUPPORTED_TICKERS)} tickers with multiple timeframes...")
    
    while background_task_running:
        try:
            # Получаем все данные одним запросом
            raw_data = await optimized_mexc_service.get_filtered_tickers(SUPPORTED_TICKERS)
            
            # Обновляем продвинутый трекер цен
            valid_updates = 0
            for symbol, ticker_data in raw_data.items():
                if 'error' not in ticker_data:
                    try:
                        price = float(ticker_data.get("lastPrice", 0))
                        volume = float(ticker_data.get("volume", 0))
                        if price > 0:
                            advanced_price_tracker.add_price_point(symbol, price, volume)
                            valid_updates += 1
                    except (ValueError, TypeError):
                        continue
            
            logger.debug(f"Updated {valid_updates}/{len(raw_data)} tickers with advanced tracking")
            
        except Exception as e:
            logger.error(f"Error in advanced background price collection: {str(e)}")
        
        # Ждем 2 секунды перед следующим обновлением
        await asyncio.sleep(2)

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {
        "message": "MEXC TradingView Screener API - v3.0",
        "features": [
            "TradingView style charts",
            "8 timeframes support", 
            "Multiple timeframe candles",
            "Compact responsive design",
            "Advanced price tracking"
        ]
    }

@api_router.get("/health")
async def health_check():
    """Проверка работоспособности продвинутого API"""
    active_symbols = advanced_price_tracker.get_active_symbols_count()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "total_supported_tickers": len(SUPPORTED_TICKERS),
        "active_symbols": active_symbols,
        "background_task_running": background_task_running,
        "features": "TradingView charts with 8 timeframes",
        "version": "3.0.0"
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
    limit: Optional[int] = Query(default=20, ge=1, le=50, description="Number of tickers to return"),
    offset: Optional[int] = Query(default=0, ge=0, description="Offset for pagination"),
    sort_by: Optional[str] = Query(default="symbol", description="Sort by: symbol, price, changePercent24h, volume, change_15s, change_30s, change_interval_0, change_interval_1, change_interval_2"),
    sort_order: Optional[str] = Query(default="asc", description="Sort order: asc, desc"),
    search: Optional[str] = Query(default=None, description="Search filter for symbol names"),
    timeframes: Optional[str] = Query(default="15s,30s,1m", description="Comma-separated list of timeframes"),
    interval_configs: Optional[str] = Query(default="15s,30s,24h", description="Comma-separated list of 3 intervals for table columns")
):
    """
    Получить актуальные цены криптовалют с продвинутыми графиками
    """
    try:
        # Парсим таймфреймы
        tf_list = [tf.strip() for tf in timeframes.split(',') if tf.strip()]
        if not tf_list:
            tf_list = ['30s', '1m', '5m']  # По умолчанию
        
        # Получаем данные от MEXC API
        raw_data = await optimized_mexc_service.get_filtered_tickers(SUPPORTED_TICKERS)
        
        # Получаем данные из продвинутого трекера цен
        tracked_data = advanced_price_tracker.get_symbols_batch_data(list(raw_data.keys()), tf_list)
        
        # Форматируем данные
        formatted_data = []
        for symbol, ticker_data in raw_data.items():
            # Базовые данные от MEXC (убираем change24h в долларах)
            formatted_ticker = {
                "symbol": ticker_data.get("symbol", symbol),
                "price": float(ticker_data.get("lastPrice", 0)) if ticker_data.get("lastPrice") else 0,
                "changePercent24h": float(ticker_data.get("priceChangePercent", 0)) if ticker_data.get("priceChangePercent") else 0,
                "volume": float(ticker_data.get("volume", 0)) if ticker_data.get("volume") else 0,
                "high24h": float(ticker_data.get("highPrice", 0)) if ticker_data.get("highPrice") else 0,
                "low24h": float(ticker_data.get("lowPrice", 0)) if ticker_data.get("lowPrice") else 0,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "mexc"
            }
            
            # Дополняем данными из трекера
            if symbol in tracked_data:
                track_data = tracked_data[symbol]
                formatted_ticker.update({
                    "change_15s": track_data.get("change_15s"),
                    "change_30s": track_data.get("change_30s"),
                })
                
                # Добавляем свечи для всех запрошенных таймфреймов
                candles = []
                for tf in tf_list:
                    tf_candles = track_data.get(f'candles_{tf}', [])
                    candles.extend(tf_candles)
                formatted_ticker["candles"] = candles
            
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
            "changePercent24h": lambda x: x[1].changePercent24h,
            "volume": lambda x: x[1].volume,
            "change_15s": lambda x: x[1].change_15s.percent_change if x[1].change_15s else 0,
            "change_30s": lambda x: x[1].change_30s.percent_change if x[1].change_30s else 0,
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
    logger.info("MEXC TradingView Screener API v3.0 starting up...")
    logger.info(f"Configured {len(SUPPORTED_TICKERS)} tickers with advanced tracking")
    
    # Запускаем фоновую задачу сбора данных
    asyncio.create_task(background_price_collection())
    
    # Планируем очистку старых данных каждые 15 минут
    async def cleanup_task():
        while True:
            await asyncio.sleep(900)  # 15 минут
            try:
                advanced_price_tracker.cleanup_old_data()
                logger.info("Advanced data cleanup completed")
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
    
    asyncio.create_task(cleanup_task())

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка ресурсов при завершении работы"""
    global background_task_running
    background_task_running = False
    
    logger.info("MEXC TradingView Screener API v3.0 shutting down...")
    await optimized_mexc_service.close_session()
    client.close()