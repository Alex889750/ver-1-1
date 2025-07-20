import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { getMockPriceData } from '../data/mock';

const CryptoScreener = () => {
  const [priceData, setPriceData] = useState({});
  const [lastUpdate, setLastUpdate] = useState(new Date());
  
  const tickers = [
    'LTCUSDT', 'SHIBUSDT', 'AVAXUSDT', 'LINKUSDT', 'BCHUSDT',
    'ATOMUSDT', 'XMRUSDT', 'APTUSDT', 'FILUSDT', 'NEARUSDT'
  ];

  const formatPrice = (price) => {
    if (price >= 1) {
      return price.toFixed(2);
    } else if (price >= 0.01) {
      return price.toFixed(4);
    } else {
      return price.toFixed(8);
    }
  };

  const formatCurrency = (symbol) => {
    return symbol.replace('USDT', '');
  };

  const getPriceChangeColor = (change) => {
    if (change > 0) return 'text-green-500';
    if (change < 0) return 'text-red-500';
    return 'text-gray-500';
  };

  const updatePrices = () => {
    const newData = getMockPriceData();
    setPriceData(newData);
    setLastUpdate(new Date());
  };

  useEffect(() => {
    // Инициализация данных
    updatePrices();
    
    // Обновление каждую секунду
    const interval = setInterval(updatePrices, 1000);
    
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-800 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-5xl font-bold text-white mb-4 tracking-tight">
            MEXC Криптовалютный Скринер
          </h1>
          <div className="flex justify-center items-center space-x-4">
            <Badge variant="secondary" className="px-4 py-2 text-sm">
              Реальное время
            </Badge>
            <span className="text-gray-400 text-sm">
              Последнее обновление: {lastUpdate.toLocaleTimeString()}
            </span>
          </div>
        </div>

        {/* Price Table */}
        <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-white text-2xl">Цены криптовалют</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-4 px-6 text-gray-300 font-semibold">Символ</th>
                    <th className="text-right py-4 px-6 text-gray-300 font-semibold">Цена (USDT)</th>
                    <th className="text-right py-4 px-6 text-gray-300 font-semibold">Изменение 24ч</th>
                    <th className="text-right py-4 px-6 text-gray-300 font-semibold">Изменение %</th>
                  </tr>
                </thead>
                <tbody>
                  {tickers.map((ticker) => {
                    const data = priceData[ticker];
                    if (!data) return null;
                    
                    return (
                      <tr key={ticker} className="border-b border-gray-700/50 hover:bg-gray-700/20 transition-colors">
                        <td className="py-4 px-6">
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center">
                              <span className="text-white text-xs font-bold">
                                {formatCurrency(ticker).substring(0, 2)}
                              </span>
                            </div>
                            <div>
                              <div className="text-white font-semibold">{formatCurrency(ticker)}</div>
                              <div className="text-gray-400 text-sm">{ticker}</div>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-right">
                          <span className="text-white text-lg font-mono">
                            ${formatPrice(data.price)}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-right">
                          <span className={`font-mono ${getPriceChangeColor(data.change24h)}`}>
                            {data.change24h > 0 ? '+' : ''}{formatPrice(data.change24h)}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-right">
                          <Badge 
                            variant={data.changePercent24h >= 0 ? "default" : "destructive"}
                            className={`font-mono ${
                              data.changePercent24h >= 0 
                                ? 'bg-green-600 hover:bg-green-700' 
                                : 'bg-red-600 hover:bg-red-700'
                            }`}
                          >
                            {data.changePercent24h > 0 ? '+' : ''}{data.changePercent24h.toFixed(2)}%
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Status Indicator */}
        <div className="mt-6 text-center">
          <div className="inline-flex items-center space-x-2 bg-green-600/20 border border-green-600 rounded-full px-4 py-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-green-400 text-sm font-medium">
              Подключение активно • Обновление каждую секунду
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CryptoScreener;