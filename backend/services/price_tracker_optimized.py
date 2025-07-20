import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import threading

logger = logging.getLogger(__name__)

@dataclass
class PricePoint:
    """Компактная точка данных цены"""
    price: float
    timestamp: float  # Unix timestamp для экономии памяти
    volume: float = 0

@dataclass
class Candle:
    """Оптимизированные свечные данные"""
    open: float
    high: float
    low: float
    close: float
    volume: float
    start_time: float  # Unix timestamp
    end_time: float    # Unix timestamp
    
    def to_dict(self):
        return {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat(),
            "timestamp": int(self.start_time * 1000)
        }

@dataclass
class OptimizedSymbolData:
    """Оптимизированные данные по символу"""
    symbol: str
    price_history: deque = field(default_factory=lambda: deque(maxlen=180))  # 6 минут при обновлении каждые 2 сек
    candles: deque = field(default_factory=lambda: deque(maxlen=30))  # 15 минут при 30-сек свечах
    current_candle: Optional[Candle] = None
    current_candle_start: Optional[float] = None
    last_price: float = 0.0
    last_update: float = 0.0
    
class OptimizedPriceTracker:
    """Оптимизированный трекер цен для большого количества символов"""
    
    def __init__(self, candle_duration_seconds: int = 30):
        self.candle_duration = candle_duration_seconds
        self.symbols_data: Dict[str, OptimizedSymbolData] = {}
        self.active_symbols: Set[str] = set()
        self.lock = threading.RLock()
        
    def add_price_point(self, symbol: str, price: float, volume: float = 0):
        """Добавить новую точку цены (thread-safe)"""
        if price <= 0:  # Игнорируем невалидные цены
            return
            
        now = datetime.utcnow().timestamp()
        
        with self.lock:
            if symbol not in self.symbols_data:
                self.symbols_data[symbol] = OptimizedSymbolData(symbol=symbol)
                self.active_symbols.add(symbol)
            
            symbol_data = self.symbols_data[symbol]
            
            # Добавляем точку в историю
            price_point = PricePoint(price=price, timestamp=now, volume=volume)
            symbol_data.price_history.append(price_point)
            symbol_data.last_price = price
            symbol_data.last_update = now
            
            # Обновляем/создаем свечу
            self._update_candle(symbol_data, price_point)
    
    def _update_candle(self, symbol_data: OptimizedSymbolData, price_point: PricePoint):
        """Обновить текущую свечу (вызывается внутри lock)"""
        now = price_point.timestamp
        
        # Определяем начало текущего интервала свечи
        candle_start = self._get_candle_start_time(now)
        candle_end = candle_start + self.candle_duration
        
        # Если это новый интервал или первая свеча
        if (symbol_data.current_candle is None or 
            symbol_data.current_candle_start != candle_start):
            
            # Завершаем предыдущую свечу
            if symbol_data.current_candle is not None:
                symbol_data.candles.append(symbol_data.current_candle)
            
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
    
    def _get_candle_start_time(self, timestamp: float) -> float:
        """Получить время начала свечи для данного timestamp"""
        return (int(timestamp) // self.candle_duration) * self.candle_duration
    
    def get_price_change(self, symbol: str, seconds_ago: int) -> Optional[Dict]:
        """Получить изменение цены за указанное количество секунд (оптимизировано)"""
        with self.lock:
            if symbol not in self.symbols_data:
                return None
            
            symbol_data = self.symbols_data[symbol]
            if not symbol_data.price_history:
                return None
            
            now = datetime.utcnow().timestamp()
            target_time = now - seconds_ago
            
            # Находим ближайшую точку по времени (оптимизированный поиск)
            target_price = None
            min_time_diff = float('inf')
            
            # Ищем с конца (более свежие данные)
            for point in reversed(symbol_data.price_history):
                time_diff = abs(point.timestamp - target_time)
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    target_price = point.price
                    
                    # Если нашли очень близкую точку, прекращаем поиск
                    if time_diff < 1.0:  # Менее 1 секунды разницы
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
    
    def get_candles(self, symbol: str, limit: int = 20) -> List[Dict]:
        """Получить свечные данные для символа (оптимизировано)"""
        with self.lock:
            if symbol not in self.symbols_data:
                return []
            
            symbol_data = self.symbols_data[symbol]
            candles = list(symbol_data.candles)
            
            # Добавляем текущую свечу, если она существует
            if symbol_data.current_candle:
                candles.append(symbol_data.current_candle)
            
            # Возвращаем последние N свечей
            return [candle.to_dict() for candle in candles[-limit:]]
    
    def get_symbols_batch_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Получить данные для batch символов (очень быстро)"""
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
                            "candles": self.get_candles(symbol, 20),
                            "last_updated": datetime.fromtimestamp(symbol_data.last_update).isoformat()
                        }
        
        return result
    
    def get_active_symbols_count(self) -> int:
        """Получить количество активных символов"""
        with self.lock:
            return len(self.active_symbols)
    
    def cleanup_old_data(self):
        """Очистить старые данные (оптимизировано)"""
        cutoff_time = datetime.utcnow().timestamp() - 1800  # 30 минут
        inactive_symbols = []
        
        with self.lock:
            for symbol, symbol_data in self.symbols_data.items():
                # Удаляем неактивные символы
                if symbol_data.last_update < cutoff_time:
                    inactive_symbols.append(symbol)
            
            # Удаляем неактивные символы
            for symbol in inactive_symbols:
                del self.symbols_data[symbol]
                self.active_symbols.discard(symbol)
        
        if inactive_symbols:
            logger.info(f"Cleaned up {len(inactive_symbols)} inactive symbols")

# Глобальный экземпляр оптимизированного трекера
optimized_price_tracker = OptimizedPriceTracker(candle_duration_seconds=30)