import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class HistoricalDataService:
    """Сервис для загрузки исторических данных с MEXC API"""
    
    def __init__(self):
        self.base_url = "https://api.mexc.com"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Маппинг наших таймфреймов к MEXC интервалам
        self.timeframe_mapping = {
            '15s': None,  # MEXC не поддерживает 15s
            '30s': None,  # MEXC не поддерживает 30s  
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Получить или создать HTTP сессию"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self.session
    
    async def close_session(self):
        """Закрыть HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def fetch_historical_klines(self, symbol: str, interval: str, limit: int = 100) -> List[Dict]:
        """
        Получить исторические данные klines для символа и интервала
        
        Args:
            symbol: Торговый символ (например, BTCUSDT)
            interval: Интервал MEXC (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Количество свечей (макс 1000)
        
        Returns:
            Список словарей с данными свечей
        """
        try:
            session = await self.get_session()
            url = f"{self.base_url}/api/v3/klines"
            
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': min(limit, 1000)  # MEXC лимит
            }
            
            logger.debug(f"Fetching historical data for {symbol} {interval} (limit: {limit})")
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    raw_data = await response.json()
                    
                    # Конвертируем данные MEXC в наш формат
                    candles = []
                    for kline in raw_data:
                        if len(kline) >= 11:
                            candle = {
                                'open': float(kline[1]),
                                'high': float(kline[2]), 
                                'low': float(kline[3]),
                                'close': float(kline[4]),
                                'volume': float(kline[5]),
                                'open_time': int(kline[0]),
                                'close_time': int(kline[6]),
                                'start_time': datetime.fromtimestamp(int(kline[0]) / 1000).isoformat(),
                                'end_time': datetime.fromtimestamp(int(kline[6]) / 1000).isoformat(),
                                'timestamp': int(kline[0]),
                                'timeframe': self._mexc_interval_to_timeframe(interval)
                            }
                            candles.append(candle)
                    
                    logger.info(f"Fetched {len(candles)} historical candles for {symbol} {interval}")
                    return candles
                
                else:
                    error_text = await response.text()
                    logger.error(f"Error fetching historical data for {symbol} {interval}: {response.status} - {error_text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error in fetch_historical_klines for {symbol} {interval}: {str(e)}")
            return []
    
    def _mexc_interval_to_timeframe(self, mexc_interval: str) -> str:
        """Конвертировать MEXC интервал в наш таймфрейм"""
        mapping = {
            '1m': '1m',
            '5m': '5m', 
            '15m': '15m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        return mapping.get(mexc_interval, mexc_interval)
    
    async def load_historical_data_for_symbols(self, symbols: List[str], timeframes: List[str] = None) -> Dict[str, Dict[str, List[Dict]]]:
        """
        Загрузить исторические данные для списка символов и таймфреймов
        
        Args:
            symbols: Список символов для загрузки
            timeframes: Список наших таймфреймов (если None, используем стандартные)
            
        Returns:
            Dict в формате {symbol: {timeframe: [candles]}}
        """
        if timeframes is None:
            timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        # Фильтруем только поддерживаемые MEXC таймфреймы
        supported_timeframes = [tf for tf in timeframes if self.timeframe_mapping.get(tf)]
        
        logger.info(f"Loading historical data for {len(symbols)} symbols and {len(supported_timeframes)} timeframes")
        
        result = {}
        tasks = []
        
        # Создаем задачи для параллельной загрузки
        for symbol in symbols:
            for timeframe in supported_timeframes:
                mexc_interval = self.timeframe_mapping[timeframe]
                if mexc_interval:
                    task = self._load_symbol_timeframe(symbol, timeframe, mexc_interval)
                    tasks.append(task)
        
        # Выполняем все задачи параллельно батчами
        batch_size = 20  # Ограничиваем количество одновременных запросов
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            # Обрабатываем результаты батча
            for task_result in batch_results:
                if isinstance(task_result, Exception):
                    logger.error(f"Batch task failed: {str(task_result)}")
                elif task_result:
                    symbol, timeframe, candles = task_result
                    if symbol not in result:
                        result[symbol] = {}
                    result[symbol][timeframe] = candles
            
            # Небольшая задержка между батчами
            if i + batch_size < len(tasks):
                await asyncio.sleep(0.1)
        
        logger.info(f"Historical data loading completed. Loaded data for {len(result)} symbols")
        return result
    
    async def _load_symbol_timeframe(self, symbol: str, timeframe: str, mexc_interval: str) -> tuple:
        """Загрузить данные для одного символа и таймфрейма"""
        try:
            candles = await self.fetch_historical_klines(symbol, mexc_interval, 50)
            return (symbol, timeframe, candles)
        except Exception as e:
            logger.error(f"Error loading {symbol} {timeframe}: {str(e)}")
            return (symbol, timeframe, [])

# Глобальный экземпляр сервиса
historical_data_service = HistoricalDataService()