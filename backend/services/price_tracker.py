import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import time

logger = logging.getLogger(__name__)

@dataclass
class PricePoint:
    """Точка данных цены"""
    price: float
    timestamp: datetime
    volume: float = 0

@dataclass
class Candle:
    """Свечные данные OHLC"""
    open: float
    high: float
    low: float
    close: float
    volume: float
    start_time: datetime
    end_time: datetime
    
    def to_dict(self):
        return {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "timestamp": int(self.start_time.timestamp() * 1000)
        }

@dataclass
class SymbolData:
    """Данные по символу"""
    symbol: str
    price_history: List[PricePoint] = field(default_factory=list)
    candles: List[Candle] = field(default_factory=list)
    current_candle: Optional[Candle] = None
    current_candle_start: Optional[datetime] = None
    
class PriceTracker:
    """Трекер цен для отслеживания коротких интервалов и формирования свечей"""
    
    def __init__(self, candle_duration_seconds: int = 30):
        self.candle_duration = candle_duration_seconds
        self.symbols_data: Dict[str, SymbolData] = {}
        self.max_history_points = 100  # Максимум точек в истории
        self.max_candles = 50  # Максимум свечей для хранения
        
    def add_price_point(self, symbol: str, price: float, volume: float = 0):
        """Добавить новую точку цены"""
        now = datetime.utcnow()
        
        if symbol not in self.symbols_data:
            self.symbols_data[symbol] = SymbolData(symbol=symbol)
        
        symbol_data = self.symbols_data[symbol]
        
        # Добавляем точку в историю
        price_point = PricePoint(price=price, timestamp=now, volume=volume)
        symbol_data.price_history.append(price_point)
        
        # Ограничиваем размер истории
        if len(symbol_data.price_history) > self.max_history_points:
            symbol_data.price_history = symbol_data.price_history[-self.max_history_points:]
        
        # Обновляем/создаем свечу
        self._update_candle(symbol_data, price_point)
        
        logger.debug(f"Added price point for {symbol}: ${price} at {now}")
    
    def _update_candle(self, symbol_data: SymbolData, price_point: PricePoint):
        """Обновить текущую свечу или создать новую"""
        now = price_point.timestamp
        
        # Определяем начало текущего интервала свечи
        candle_start = self._get_candle_start_time(now)
        candle_end = candle_start + timedelta(seconds=self.candle_duration)
        
        # Если это новый интервал или первая свеча
        if (symbol_data.current_candle is None or 
            symbol_data.current_candle_start != candle_start):
            
            # Завершаем предыдущую свечу
            if symbol_data.current_candle is not None:
                symbol_data.candles.append(symbol_data.current_candle)
                
                # Ограничиваем количество свечей
                if len(symbol_data.candles) > self.max_candles:
                    symbol_data.candles = symbol_data.candles[-self.max_candles:]
            
            # Создаем новую свечу
            symbol_data.current_candle = Candle(
                open=price_point.price,
                high=price_point.price,
                low=price_point.price,
                close=price_point.price,
                volume=price_point.volume,
                start_time=candle_start,
                end_time=candle_end
            )
            symbol_data.current_candle_start = candle_start
            
        else:
            # Обновляем текущую свечу
            candle = symbol_data.current_candle
            candle.high = max(candle.high, price_point.price)
            candle.low = min(candle.low, price_point.price)
            candle.close = price_point.price
            candle.volume += price_point.volume
            candle.end_time = candle_end
    
    def _get_candle_start_time(self, timestamp: datetime) -> datetime:
        """Получить время начала свечи для данного timestamp"""
        # Округляем до ближайшего интервала
        seconds_since_epoch = int(timestamp.timestamp())
        interval_start = (seconds_since_epoch // self.candle_duration) * self.candle_duration
        return datetime.utcfromtimestamp(interval_start)
    
    def get_price_change(self, symbol: str, seconds_ago: int) -> Optional[Dict]:
        """Получить изменение цены за указанное количество секунд"""
        if symbol not in self.symbols_data:
            return None
        
        symbol_data = self.symbols_data[symbol]
        if not symbol_data.price_history:
            return None
        
        now = datetime.utcnow()
        target_time = now - timedelta(seconds=seconds_ago)
        
        # Находим ближайшую точку по времени
        target_price = None
        min_time_diff = float('inf')
        
        for point in symbol_data.price_history:
            time_diff = abs((point.timestamp - target_time).total_seconds())
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                target_price = point.price
        
        if target_price is None:
            return None
        
        current_price = symbol_data.price_history[-1].price
        price_change = current_price - target_price
        percent_change = (price_change / target_price) * 100 if target_price > 0 else 0
        
        return {
            "price_change": price_change,
            "percent_change": percent_change,
            "seconds_ago": seconds_ago,
            "old_price": target_price,
            "current_price": current_price
        }
    
    def get_candles(self, symbol: str, limit: int = 20) -> List[Dict]:
        """Получить свечные данные для символа"""
        if symbol not in self.symbols_data:
            return []
        
        symbol_data = self.symbols_data[symbol]
        candles = symbol_data.candles.copy()
        
        # Добавляем текущую свечу, если она существует
        if symbol_data.current_candle:
            candles.append(symbol_data.current_candle)
        
        # Возвращаем последние N свечей
        return [candle.to_dict() for candle in candles[-limit:]]
    
    def get_all_symbols_data(self) -> Dict[str, Dict]:
        """Получить данные по всем символам"""
        result = {}
        
        for symbol, symbol_data in self.symbols_data.items():
            if not symbol_data.price_history:
                continue
                
            result[symbol] = {
                "current_price": symbol_data.price_history[-1].price,
                "change_15s": self.get_price_change(symbol, 15),
                "change_30s": self.get_price_change(symbol, 30),
                "candles": self.get_candles(symbol, 20),
                "last_updated": symbol_data.price_history[-1].timestamp.isoformat()
            }
        
        return result
    
    def cleanup_old_data(self):
        """Очистить старые данные"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=30)
        
        for symbol_data in self.symbols_data.values():
            # Очищаем старые точки истории
            symbol_data.price_history = [
                point for point in symbol_data.price_history 
                if point.timestamp > cutoff_time
            ]
            
            # Очищаем старые свечи
            symbol_data.candles = [
                candle for candle in symbol_data.candles 
                if candle.start_time > cutoff_time
            ]

# Глобальный экземпляр трекера
price_tracker = PriceTracker(candle_duration_seconds=30)