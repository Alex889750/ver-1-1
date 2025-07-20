import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MEXCService:
    def __init__(self):
        self.base_url = "https://api.mexc.com"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Получить или создать HTTP сессию"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close_session(self):
        """Закрыть HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_24hr_ticker(self, symbol: Optional[str] = None) -> Dict:
        """
        Получить 24-часовую статистику тикера
        
        Args:
            symbol: Символ торговой пары (опционально). Если не указан, возвращает все символы
            
        Returns:
            Dict с данными о цене и изменениях за 24 часа
        """
        try:
            session = await self.get_session()
            url = f"{self.base_url}/api/v3/ticker/24hr"
            
            params = {}
            if symbol:
                params['symbol'] = symbol
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched 24hr ticker data for {'all symbols' if not symbol else symbol}")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"Error fetching 24hr ticker: {response.status} - {error_text}")
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error in get_24hr_ticker: {str(e)}")
            raise
    
    async def get_current_price(self, symbol: Optional[str] = None) -> Dict:
        """
        Получить текущую цену
        
        Args:
            symbol: Символ торговой пары (опционально)
            
        Returns:
            Dict с текущими ценами
        """
        try:
            session = await self.get_session()
            url = f"{self.base_url}/api/v3/ticker/price"
            
            params = {}
            if symbol:
                params['symbol'] = symbol
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched price data for {'all symbols' if not symbol else symbol}")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"Error fetching price: {response.status} - {error_text}")
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error in get_current_price: {str(e)}")
            raise
    
    async def get_multiple_tickers(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Получить данные для нескольких тикеров одновременно
        
        Args:
            symbols: Список символов торговых пар
            
        Returns:
            Dict где ключи - символы, значения - данные о ценах
        """
        try:
            # Создаем задачи для параллельного выполнения запросов
            tasks = []
            for symbol in symbols:
                task = self.get_24hr_ticker(symbol)
                tasks.append(task)
            
            # Выполняем все запросы параллельно
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            tickers_data = {}
            for i, result in enumerate(results):
                symbol = symbols[i]
                if isinstance(result, Exception):
                    logger.error(f"Error fetching data for {symbol}: {str(result)}")
                    # Используем заглушку для ошибочных символов
                    tickers_data[symbol] = {
                        "symbol": symbol,
                        "lastPrice": "0",
                        "priceChange": "0", 
                        "priceChangePercent": "0",
                        "error": str(result)
                    }
                else:
                    tickers_data[symbol] = result
            
            return tickers_data
            
        except Exception as e:
            logger.error(f"Error in get_multiple_tickers: {str(e)}")
            raise
    
    def format_ticker_data(self, raw_data: Dict) -> Dict:
        """
        Форматировать данные тикера для frontend
        
        Args:
            raw_data: Сырые данные от MEXC API
            
        Returns:
            Отформатированные данные
        """
        try:
            return {
                "symbol": raw_data.get("symbol", ""),
                "price": float(raw_data.get("lastPrice", 0)),
                "change24h": float(raw_data.get("priceChange", 0)),
                "changePercent24h": float(raw_data.get("priceChangePercent", 0)),
                "volume": float(raw_data.get("volume", 0)),
                "high24h": float(raw_data.get("highPrice", 0)),
                "low24h": float(raw_data.get("lowPrice", 0)),
                "timestamp": datetime.utcnow().isoformat(),
                "source": "mexc"
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Error formatting ticker data: {str(e)}")
            return {
                "symbol": raw_data.get("symbol", ""),
                "price": 0,
                "change24h": 0,
                "changePercent24h": 0,
                "volume": 0,
                "high24h": 0,
                "low24h": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "mexc",
                "error": "formatting_error"
            }

# Глобальный экземпляр сервиса
mexc_service = MEXCService()