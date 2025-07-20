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
from services.historical_data_service import historical_data_service
from services.price_tracker_with_history import price_tracker_with_history
from config.tickers import SUPPORTED_TICKERS


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="MEXC TradingView Screener API", version="3.1.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Utility functions
def convert_interval_to_seconds(interval: str) -> Optional[int]:
    """Конвертировать интервал в секунды"""
    interval_map = {
        '2s': 2, '5s': 5, '10s': 10, '15s': 15, '30s': 30,
        '1m': 60, '2m': 120, '3m': 180, '5m': 300, '10m': 600,
        '15m': 900, '20m': 1200, '30m': 1800, '1h': 3600,
        '4h': 14400, '24h': 86400
    }
    return interval_map.get(interval)

def get_price_change_for_interval(track_data: Dict, interval_seconds: int) -> Optional[Dict]:
    """Получить изменение цены для указанного интервала"""
    if interval_seconds == 15:
        return track_data.get("change_15s")
    elif interval_seconds == 30:
        return track_data.get("change_30s")
    elif interval_seconds == 86400:  # 24h
        # Для 24h возвращаем None, будем использовать данные MEXC
        return None
    else:
        # Для других интервалов пока возвращаем None
        # В будущем можно добавить более сложную логику
        return None

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
    changePercent24h: float  # Убрали change24h (в долларах)
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
    sort_by: Optional[str] = Query(default="symbol", description="Sort by: symbol, price, changePercent24h, volume, change_15s, change_30s"),
    sort_order: Optional[str] = Query(default="asc", description="Sort order: asc, desc"),
    search: Optional[str] = Query(default=None, description="Search filter for symbol names"),
    timeframes: Optional[str] = Query(default="15s,30s,1m", description="Comma-separated list of timeframes"),
    intervals: Optional[str] = Query(default="15s,30s,24h", description="Comma-separated list of price change intervals")
):
    """
    Получить актуальные цены криптовалют с продвинутыми графиками
    """
    try:
        # Парсим таймфреймы и интервалы
        tf_list = [tf.strip() for tf in timeframes.split(',') if tf.strip()]
        if not tf_list:
            tf_list = ['30s', '1m', '5m']  # По умолчанию
        
        interval_list = [int.strip() for int in intervals.split(',') if int.strip()]
        if not interval_list:
            interval_list = ['15s', '30s', '24h']  # По умолчанию
        
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
                
                # Добавляем данные для всех запрошенных интервалов
                for interval in interval_list:
                    # Конвертируем интервал в секунды
                    interval_seconds = convert_interval_to_seconds(interval)
                    if interval_seconds:
                        change_data = get_price_change_for_interval(track_data, interval_seconds)
                        if change_data:
                            formatted_ticker[f"change_{interval_seconds}s"] = change_data
                
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
        
        # Сортировка (обновленная для поддержки динамических интервалов)
        sort_key_map = {
            "symbol": lambda x: x[1].symbol,
            "price": lambda x: x[1].price,
            "changePercent24h": lambda x: x[1].changePercent24h,
            "volume": lambda x: x[1].volume,
            "change_15s": lambda x: x[1].change_15s.percent_change if x[1].change_15s else 0,
            "change_30s": lambda x: x[1].change_30s.percent_change if x[1].change_30s else 0,
        }
        
        # Добавляем динамические ключи для всех возможных интервалов
        interval_seconds_map = {
            2: "change_2s", 5: "change_5s", 10: "change_10s", 15: "change_15s", 30: "change_30s",
            60: "change_60s", 120: "change_120s", 180: "change_180s", 300: "change_300s", 
            600: "change_600s", 900: "change_900s", 1200: "change_1200s", 1800: "change_1800s",
            3600: "change_3600s", 14400: "change_14400s", 86400: "change_86400s"
        }
        
        for seconds, key in interval_seconds_map.items():
            sort_key_map[key] = lambda x, s=seconds: (
                getattr(x[1], f'change_{s}s', {}).get('percent_change', 0) 
                if hasattr(x[1], f'change_{s}s') and getattr(x[1], f'change_{s}s') 
                else (x[1].changePercent24h if s == 86400 else 0)
            )
        
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

@api_router.post("/crypto/load-history")
async def load_historical_data():
    """
    Загрузить исторические данные для всех поддерживаемых символов
    """
    try:
        logger.info("Starting historical data loading...")
        
        # Загружаем исторические данные
        historical_data = await historical_data_service.load_historical_data_for_symbols(
            symbols=SUPPORTED_TICKERS[:50],  # Ограничиваем для тестирования
            timeframes=['1m', '5m', '15m', '1h', '4h', '1d']
        )
        
        # Заполняем трекер историческими данными
        price_tracker_with_history.populate_historical_data(historical_data)
        
        # Переключаемся на трекер с историей
        global advanced_price_tracker
        advanced_price_tracker = price_tracker_with_history
        
        loaded_symbols = len(historical_data)
        total_candles = sum(
            len(tf_data) for symbol_data in historical_data.values() 
            for tf_data in symbol_data.values()
        )
        
        logger.info(f"Historical data loading completed: {loaded_symbols} symbols, {total_candles} candles")
        
        return {
            "success": True,
            "message": f"Загружены исторические данные для {loaded_symbols} символов",
            "symbols_loaded": loaded_symbols,
            "total_candles": total_candles,
            "timeframes": ['1m', '5m', '15m', '1h', '4h', '1d'],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error loading historical data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load historical data: {str(e)}"
        )

@api_router.get("/crypto/history-status")
async def get_history_status():
    """
    Получить статус загрузки исторических данных
    """
    try:
        is_loaded = advanced_price_tracker.is_historical_data_loaded() if hasattr(advanced_price_tracker, 'is_historical_data_loaded') else False
        active_symbols = advanced_price_tracker.get_active_symbols_count()
        
        return {
            "historical_data_loaded": is_loaded,
            "active_symbols": active_symbols,
            "supported_symbols": len(SUPPORTED_TICKERS),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting history status: {str(e)}")
        return {
            "historical_data_loaded": False,
            "active_symbols": 0,
            "supported_symbols": len(SUPPORTED_TICKERS),
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

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