import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import threading
import math

logger = logging.getLogger(__name__)

@dataclass
class PricePoint:
    """Компактная точка данных цены"""
    price: float
    timestamp: float  # Unix timestamp для экономии памяти
    volume: float = 0

@dataclass
class AdvancedCandle:
    """Продвинутые свечные данные с поддержкой разных таймфреймов"""
    open: float
    high: float
    low: float
    close: float
    volume: float
    start_time: float
    end_time: float
    timeframe: str  # '15s', '30s', '1m', '5m', '15m', '1h', '4h', '1d'
    
    def to_dict(self):
        return {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat(),
            "timestamp": int(self.start_time * 1000),
            "timeframe": self.timeframe
        }

@dataclass
class AdvancedSymbolData:
    """Продвинутые данные по символу с поддержкой множественных таймфреймов"""
    symbol: str
    price_history: deque = field(default_factory=lambda: deque(maxlen=500))  # Больше истории для разных таймфреймов
    
    # Свечи для разных таймфреймов
    candles_15s: deque = field(default_factory=lambda: deque(maxlen=100))
    candles_30s: deque = field(default_factory=lambda: deque(maxlen=100))  
    candles_1m: deque = field(default_factory=lambda: deque(maxlen=100))
    candles_5m: deque = field(default_factory=lambda: deque(maxlen=50))
    candles_15m: deque = field(default_factory=lambda: deque(maxlen=50))
    candles_1h: deque = field(default_factory=lambda: deque(maxlen=30))
    candles_4h: deque = field(default_factory=lambda: deque(maxlen=30))
    candles_1d: deque = field(default_factory=lambda: deque(maxlen=30))
    
    # Текущие свечи для каждого таймфрейма
    current_candle_15s: Optional[AdvancedCandle] = None
    current_candle_30s: Optional[AdvancedCandle] = None
    current_candle_1m: Optional[AdvancedCandle] = None
    current_candle_5m: Optional[AdvancedCandle] = None
    current_candle_15m: Optional[AdvancedCandle] = None
    current_candle_1h: Optional[AdvancedCandle] = None
    current_candle_4h: Optional[AdvancedCandle] = None
    current_candle_1d: Optional[AdvancedCandle] = None
    
    # Стартовое время для каждого таймфрейма
    current_candle_start_15s: Optional[float] = None
    current_candle_start_30s: Optional[float] = None
    current_candle_start_1m: Optional[float] = None
    current_candle_start_5m: Optional[float] = None
    current_candle_start_15m: Optional[float] = None
    current_candle_start_1h: Optional[float] = None
    current_candle_start_4h: Optional[float] = None
    current_candle_start_1d: Optional[float] = None
    
    last_price: float = 0.0
    last_update: float = 0.0

class AdvancedPriceTracker:
    """Продвинутый трекер цен с поддержкой множественных таймфреймов"""
    
    def __init__(self):
        self.symbols_data: Dict[str, AdvancedSymbolData] = {}
        self.active_symbols: Set[str] = set()
        self.lock = threading.RLock()
        
        # Таймфреймы в секундах
        self.timeframes = {
            '15s': 15,
            '30s': 30,
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }
    
    def add_price_point(self, symbol: str, price: float, volume: float = 0):
        """Добавить новую точку цены и обновить все таймфреймы"""
        if price <= 0:
            return
            
        now = datetime.utcnow().timestamp()
        
        with self.lock:
            if symbol not in self.symbols_data:
                self.symbols_data[symbol] = AdvancedSymbolData(symbol=symbol)
                self.active_symbols.add(symbol)
            
            symbol_data = self.symbols_data[symbol]
            
            # Добавляем точку в историю
            price_point = PricePoint(price=price, timestamp=now, volume=volume)
            symbol_data.price_history.append(price_point)
            symbol_data.last_price = price
            symbol_data.last_update = now
            
            # Обновляем свечи для всех таймфреймов
            self._update_all_candles(symbol_data, price_point)
    
    def _update_all_candles(self, symbol_data: AdvancedSymbolData, price_point: PricePoint):
        """Обновить свечи для всех таймфреймов"""
        for tf_name, tf_seconds in self.timeframes.items():
            self._update_candle_for_timeframe(symbol_data, price_point, tf_name, tf_seconds)
    
    def _update_candle_for_timeframe(self, symbol_data: AdvancedSymbolData, price_point: PricePoint, 
                                   timeframe: str, duration_seconds: int):
        """Обновить свечу для конкретного таймфрейма"""
        now = price_point.timestamp
        
        # Получаем атрибуты для данного таймфрейма
        candles_attr = f'candles_{timeframe}'
        current_candle_attr = f'current_candle_{timeframe}'
        current_start_attr = f'current_candle_start_{timeframe}'
        
        candles_deque = getattr(symbol_data, candles_attr)
        current_candle = getattr(symbol_data, current_candle_attr)
        current_start = getattr(symbol_data, current_start_attr)
        
        # Определяем начало текущего интервала
        candle_start = self._get_candle_start_time(now, duration_seconds)
        candle_end = candle_start + duration_seconds
        
        # Если это новый интервал или первая свеча
        if current_candle is None or current_start != candle_start:
            # Завершаем предыдущую свечу
            if current_candle is not None:
                candles_deque.append(current_candle)
            
            # Создаем новую свечу
            new_candle = AdvancedCandle(
                open=price_point.price,
                high=price_point.price,
                low=price_point.price,
                close=price_point.price,
                volume=price_point.volume,
                start_time=candle_start,
                end_time=candle_end,
                timeframe=timeframe
            )
            
            setattr(symbol_data, current_candle_attr, new_candle)
            setattr(symbol_data, current_start_attr, candle_start)
        else:
            # Обновляем текущую свечу
            current_candle.high = max(current_candle.high, price_point.price)
            current_candle.low = min(current_candle.low, price_point.price)
            current_candle.close = price_point.price
            current_candle.volume += price_point.volume
            current_candle.end_time = candle_end
    
    def _get_candle_start_time(self, timestamp: float, duration_seconds: int) -> float:
        """Получить время начала свечи для данного timestamp и таймфрейма"""
        return (int(timestamp) // duration_seconds) * duration_seconds
    
    def get_price_change(self, symbol: str, seconds_ago: int) -> Optional[Dict]:
        """Получить изменение цены за указанное количество секунд"""
        with self.lock:
            if symbol not in self.symbols_data:
                return None
            
            symbol_data = self.symbols_data[symbol]
            if not symbol_data.price_history:
                return None
            
            now = datetime.utcnow().timestamp()
            target_time = now - seconds_ago
            
            # Находим ближайшую точку по времени
            target_price = None
            min_time_diff = float('inf')
            
            for point in reversed(symbol_data.price_history):
                time_diff = abs(point.timestamp - target_time)
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    target_price = point.price
                    
                    if time_diff < 1.0:
                        break
            
            if target_price is None or target_price <= 0:
                return None
            
            current_price = symbol_data.last_price
            if current_price <= 0:
                return None
                
            price_change = current_price - target_price
            percent_change = (price_change / target_price) * 100
            
            return {
                "price_change": price_change,
                "percent_change": percent_change,
                "seconds_ago": seconds_ago,
                "old_price": target_price,
                "current_price": current_price
            }
    
    def get_multiple_price_changes(self, symbol: str, intervals_seconds: List[int]) -> Dict[str, Optional[Dict]]:
        """Получить изменения цены для нескольких интервалов"""
        result = {}
        for i, seconds in enumerate(intervals_seconds):
            result[f'change_interval_{i}'] = self.get_price_change(symbol, seconds)
        return result
    
    def get_candles(self, symbol: str, timeframe: str = '30s', limit: int = 50) -> List[Dict]:
        """Получить свечные данные для символа и таймфрейма"""
        with self.lock:
            if symbol not in self.symbols_data:
                return []
            
            symbol_data = self.symbols_data[symbol]
            
            # Получаем соответствующие атрибуты
            candles_attr = f'candles_{timeframe}'
            current_candle_attr = f'current_candle_{timeframe}'
            
            if not hasattr(symbol_data, candles_attr):
                return []
            
            candles_deque = getattr(symbol_data, candles_attr)
            current_candle = getattr(symbol_data, current_candle_attr)
            
            candles = list(candles_deque)
            
            # Добавляем текущую свечу, если она существует
            if current_candle:
                candles.append(current_candle)
            
            # Возвращаем последние N свечей
            return [candle.to_dict() for candle in candles[-limit:]]
    
    def get_symbols_batch_data(self, symbols: List[str], timeframes: List[str] = ['15s', '30s', '1m'], 
                             interval_configs: List[int] = [15, 30]) -> Dict[str, Dict]:
        """Получить данные для batch символов с множественными таймфреймами и настраиваемыми интервалами"""
        result = {}
        
        with self.lock:
            for symbol in symbols:
                if symbol in self.symbols_data:
                    symbol_data = self.symbols_data[symbol]
                    
                    if symbol_data.last_price > 0:
                        result[symbol] = {
                            "current_price": symbol_data.last_price,
                            "change_15s": self.get_price_change(symbol, 15),
                            "change_30s": self.get_price_change(symbol, 30),
                            "last_updated": datetime.fromtimestamp(symbol_data.last_update).isoformat()
                        }
                        
                        # Добавляем настраиваемые интервалы
                        interval_changes = self.get_multiple_price_changes(symbol, interval_configs)
                        result[symbol].update(interval_changes)
                        
                        # Добавляем данные по таймфреймам
                        for tf in timeframes:
                            result[symbol][f'candles_{tf}'] = self.get_candles(symbol, tf, 50)
        
        return result
    
    def get_active_symbols_count(self) -> int:
        """Получить количество активных символов"""
        with self.lock:
            return len(self.active_symbols)
    
    def cleanup_old_data(self):
        """Очистить старые данные"""
        cutoff_time = datetime.utcnow().timestamp() - 3600  # 1 час
        inactive_symbols = []
        
        with self.lock:
            for symbol, symbol_data in self.symbols_data.items():
                if symbol_data.last_update < cutoff_time:
                    inactive_symbols.append(symbol)
            
            for symbol in inactive_symbols:
                del self.symbols_data[symbol]
                self.active_symbols.discard(symbol)
        
        if inactive_symbols:
            logger.info(f"Cleaned up {len(inactive_symbols)} inactive symbols")

# Глобальный экземпляр продвинутого трекера
advanced_price_tracker = AdvancedPriceTracker()