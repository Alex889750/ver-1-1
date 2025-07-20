import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class OptimizedMEXCService:
    def __init__(self):
        self.base_url = "https://api.mexc.com"
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_delay = 0.1  # 100ms между запросами
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Получить или создать HTTP сессию с оптимизированными настройками"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                limit=100,  # Максимум одновременных подключений
                limit_per_host=20,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    'User-Agent': 'MEXC-Crypto-Screener/1.0'
                }
            )
        return self.session
    
    async def close_session(self):
        """Закрыть HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_all_24hr_tickers(self) -> Dict[str, Dict]:
        """
        Получить все 24-часовые данные одним запросом (наиболее эффективно)
        """
        try:
            session = await self.get_session()
            url = f"{self.base_url}/api/v3/ticker/24hr"
            
            logger.info("Fetching all 24hr ticker data in single request...")
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Преобразуем список в словарь для быстрого доступа
                    tickers_dict = {}
                    if isinstance(data, list):
                        for ticker_data in data:
                            symbol = ticker_data.get('symbol', '')
                            if symbol:
                                tickers_dict[symbol] = ticker_data
                    
                    logger.info(f"Successfully fetched {len(tickers_dict)} tickers from MEXC")
                    return tickers_dict
                    
                else:
                    error_text = await response.text()
                    logger.error(f"Error fetching all tickers: {response.status} - {error_text}")
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error in get_all_24hr_tickers: {str(e)}")
            raise
    
    async def get_filtered_tickers(self, target_symbols: List[str]) -> Dict[str, Dict]:
        """
        Получить данные только для указанных символов из всех доступных
        """
        try:
            # Получаем все данные одним запросом
            all_data = await self.get_all_24hr_tickers()
            
            # Фильтруем только нужные символы
            filtered_data = {}
            not_found = []
            
            for symbol in target_symbols:
                if symbol in all_data:
                    filtered_data[symbol] = all_data[symbol]
                else:
                    not_found.append(symbol)
                    # Создаем заглушку для отсутствующих символов
                    filtered_data[symbol] = {
                        "symbol": symbol,
                        "lastPrice": "0",
                        "priceChange": "0",
                        "priceChangePercent": "0",
                        "volume": "0",
                        "highPrice": "0",
                        "lowPrice": "0",
                        "error": "not_found"
                    }
            
            if not_found:
                logger.warning(f"Symbols not found on MEXC: {', '.join(not_found[:10])}{'...' if len(not_found) > 10 else ''}")
            
            logger.info(f"Filtered {len(filtered_data)} symbols from MEXC data")
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error in get_filtered_tickers: {str(e)}")
            # Возвращаем заглушки для всех символов в случае ошибки
            return {
                symbol: {
                    "symbol": symbol,
                    "lastPrice": "0",
                    "priceChange": "0",
                    "priceChangePercent": "0",
                    "volume": "0",
                    "highPrice": "0",
                    "lowPrice": "0",
                    "error": "api_error"
                }
                for symbol in target_symbols
            }
    
    def format_ticker_data(self, raw_data: Dict) -> Dict:
        """
        Форматировать данные тикера для frontend (оптимизированная версия)
        """
        try:
            if "error" in raw_data:
                return {
                    "symbol": raw_data.get("symbol", ""),
                    "price": 0.0,
                    "change24h": 0.0,
                    "changePercent24h": 0.0,
                    "volume": 0.0,
                    "high24h": 0.0,
                    "low24h": 0.0,
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "mexc",
                    "error": raw_data.get("error", "unknown")
                }
            
            # Быстрое преобразование с обработкой ошибок
            def safe_float(value, default=0.0):
                try:
                    return float(value) if value and value != "0" else default
                except (ValueError, TypeError):
                    return default
            
            return {
                "symbol": raw_data.get("symbol", ""),
                "price": safe_float(raw_data.get("lastPrice")),
                "change24h": safe_float(raw_data.get("priceChange")),
                "changePercent24h": safe_float(raw_data.get("priceChangePercent")),
                "volume": safe_float(raw_data.get("volume")),
                "high24h": safe_float(raw_data.get("highPrice")),
                "low24h": safe_float(raw_data.get("lowPrice")),
                "timestamp": datetime.utcnow().isoformat(),
                "source": "mexc"
            }
            
        except Exception as e:
            logger.error(f"Error formatting ticker data: {str(e)}")
            return {
                "symbol": raw_data.get("symbol", "unknown"),
                "price": 0.0,
                "change24h": 0.0,
                "changePercent24h": 0.0,
                "volume": 0.0,
                "high24h": 0.0,
                "low24h": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "mexc",
                "error": "formatting_error"
            }

# Глобальный экземпляр оптимизированного сервиса
optimized_mexc_service = OptimizedMEXCService()