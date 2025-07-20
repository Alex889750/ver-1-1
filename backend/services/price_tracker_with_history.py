import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import threading
from .price_tracker_advanced import AdvancedCandle, AdvancedSymbolData

logger = logging.getLogger(__name__)

class PriceTrackerWithHistory:
    """Продвинутый трекер цен с предварительной загрузкой исторических данных"""
    
    def __init__(self):
        self.symbols_data: Dict[str, AdvancedSymbolData] = {}
        self.active_symbols: Set[str] = set()
        self.lock = threading.RLock()
        self.historical_data_loaded = False
        
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
    
    def populate_historical_data(self, historical_data: Dict[str, Dict[str, List[Dict]]]):
        """
        Заполнить трекер историческими данными
        
        Args:
            historical_data: Данные в формате {symbol: {timeframe: [candles]}}
        """
        logger.info("Populating price tracker with historical data...")
        
        with self.lock:
            for symbol, symbol_timeframes in historical_data.items():
                if symbol not in self.symbols_data:
                    self.symbols_data[symbol] = AdvancedSymbolData(symbol=symbol)
                    self.active_symbols.add(symbol)
                
                symbol_data = self.symbols_data[symbol]
                
                # Заполняем исторические свечи для каждого таймфрейма
                for timeframe, candles in symbol_timeframes.items():
                    if not candles:
                        continue
                    
                    # Конвертируем словари обратно в AdvancedCandle объекты
                    candle_objects = []
                    for candle_dict in candles:
                        try:
                            candle = AdvancedCandle(
                                open=candle_dict['open'],
                                high=candle_dict['high'],
                                low=candle_dict['low'],
                                close=candle_dict['close'],
                                volume=candle_dict['volume'],
                                start_time=candle_dict['timestamp'] / 1000,  # Конвертируем мс в секунды
                                end_time=(candle_dict['timestamp'] + self.timeframes.get(timeframe, 60) * 1000) / 1000,
                                timeframe=timeframe
                            )
                            candle_objects.append(candle)
                        except Exception as e:
                            logger.warning(f"Error converting candle for {symbol} {timeframe}: {str(e)}")
                            continue
                    
                    # Заполняем соответствующую deque
                    candles_attr = f'candles_{timeframe}'
                    if hasattr(symbol_data, candles_attr):
                        candles_deque = getattr(symbol_data, candles_attr)
                        candles_deque.extend(candle_objects)
                        
                        # Устанавливаем последнюю цену из последней свечи
                        if candle_objects:
                            last_candle = candle_objects[-1]
                            symbol_data.last_price = last_candle.close
                            symbol_data.last_update = last_candle.end_time
                
                logger.debug(f"Populated historical data for {symbol}: {len(symbol_timeframes)} timeframes")
        
        self.historical_data_loaded = True
        logger.info(f"Historical data population completed for {len(historical_data)} symbols")
    
    def add_price_point(self, symbol: str, price: float, volume: float = 0):
        """Добавить новую точку цены (использует логику из AdvancedPriceTracker)"""
        if price <= 0:
            return
            
        now = datetime.utcnow().timestamp()
        
        with self.lock:
            if symbol not in self.symbols_data:
                self.symbols_data[symbol] = AdvancedSymbolData(symbol=symbol)
                self.active_symbols.add(symbol)
            
            symbol_data = self.symbols_data[symbol]
            
            # Добавляем точку в историю
            from .price_tracker_advanced import PricePoint
            price_point = PricePoint(price=price, timestamp=now, volume=volume)
            symbol_data.price_history.append(price_point)
            symbol_data.last_price = price
            symbol_data.last_update = now
            
            # Обновляем свечи для всех таймфреймов
            self._update_all_candles(symbol_data, price_point)
    
    def _update_all_candles(self, symbol_data: AdvancedSymbolData, price_point):
        """Обновить свечи для всех таймфреймов"""
        for tf_name, tf_seconds in self.timeframes.items():
            self._update_candle_for_timeframe(symbol_data, price_point, tf_name, tf_seconds)
    
    def _update_candle_for_timeframe(self, symbol_data: AdvancedSymbolData, price_point, 
                                   timeframe: str, duration_seconds: int):
        """Обновить свечу для конкретного таймфрейма"""
        now = price_point.timestamp
        
        # Получаем атрибуты для данного таймфрейма
        candles_attr = f'candles_{timeframe}'
        current_candle_attr = f'current_candle_{timeframe}'
        current_start_attr = f'current_candle_start_{timeframe}'
        
        if not hasattr(symbol_data, candles_attr):
            return
        
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
    
    def get_symbols_batch_data(self, symbols: List[str], timeframes: List[str] = ['15s', '30s', '1m']) -> Dict[str, Dict]:
        """Получить данные для batch символов с множественными таймфреймами"""
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
                        
                        # Добавляем данные по таймфреймам
                        for tf in timeframes:
                            result[symbol][f'candles_{tf}'] = self.get_candles(symbol, tf, 50)
        
        return result
    
    def get_active_symbols_count(self) -> int:
        """Получить количество активных символов"""
        with self.lock:
            return len(self.active_symbols)
    
    def is_historical_data_loaded(self) -> bool:
        """Проверить, загружены ли исторические данные"""
        return self.historical_data_loaded
    
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

# Глобальный экземпляр трекера с историей
price_tracker_with_history = PriceTrackerWithHistory()