import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import CandleChart from './CandleChart';
import SettingsPanel from './SettingsPanel';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const OptimizedCryptoScreener = () => {
  const [priceData, setPriceData] = useState({});
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [totalTickers, setTotalTickers] = useState(0);
  const [activeTickers, setActiveTickers] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  
  // Настройки
  const [settings, setSettings] = useState({
    displayCount: 20,
    search: '',
    sortBy: 'symbol',
    sortOrder: 'asc',
  });

  // Колонки таблицы с возможностью сортировки
  const columns = [
    { key: 'symbol', label: 'Символ', sortable: true },
    { key: 'price', label: 'Цена (USDT)', sortable: true, align: 'right' },
    { key: 'change_15s', label: '15с', sortable: false, align: 'right' },
    { key: 'change_30s', label: '30с', sortable: false, align: 'right' },
    { key: 'change24h', label: '24ч', sortable: true, align: 'right' },
    { key: 'changePercent24h', label: '24ч %', sortable: true, align: 'right' },
    { key: 'volume', label: 'Объем', sortable: true, align: 'right' },
    { key: 'chart', label: 'График', sortable: false, align: 'center' },
  ];

  const formatPrice = useCallback((price) => {
    if (price >= 1) {
      return price.toFixed(2);
    } else if (price >= 0.01) {
      return price.toFixed(4);
    } else {
      return price.toFixed(8);
    }
  }, []);

  const formatCurrency = useCallback((symbol) => {
    return symbol.replace('USDT', '');
  }, []);

  const formatVolume = useCallback((volume) => {
    if (volume >= 1000000) {
      return `${(volume / 1000000).toFixed(1)}M`;
    } else if (volume >= 1000) {
      return `${(volume / 1000).toFixed(1)}K`;
    }
    return volume.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }, []);

  const getPriceChangeColor = useCallback((change) => {
    if (change > 0) return 'text-green-500';
    if (change < 0) return 'text-red-500';
    return 'text-gray-500';
  }, []);

  const formatShortTermChange = useCallback((changeData) => {
    if (!changeData) {
      return { text: 'N/A', color: 'text-gray-500', absolute: '' };
    }
    
    const { price_change, percent_change } = changeData;
    const color = getPriceChangeColor(price_change);
    const sign = price_change > 0 ? '+' : '';
    
    return {
      text: `${sign}${percent_change.toFixed(2)}%`,
      color,
      absolute: `${sign}${formatPrice(price_change)}`
    };
  }, [formatPrice, getPriceChangeColor]);

  const fetchPrices = useCallback(async () => {
    try {
      setError(null);
      
      // Строим параметры запроса
      const params = new URLSearchParams({
        limit: settings.displayCount.toString(),
        sort_by: settings.sortBy,
        sort_order: settings.sortOrder,
      });
      
      if (settings.search) {
        params.append('search', settings.search);
      }

      const response = await axios.get(`${API}/crypto/prices?${params}`);
      
      if (response.data && response.data.data) {
        setPriceData(response.data.data);
        setLastUpdate(new Date());
        setTotalTickers(response.data.total_available);
        setActiveTickers(response.data.count);
        setConnectionStatus('connected');
        setIsLoading(false);
      }
    } catch (err) {
      console.error('Error fetching prices:', err);
      setError('Ошибка получения данных с MEXC');
      setConnectionStatus('error');
      setIsLoading(false);
    }
  }, [settings]);

  useEffect(() => {
    fetchPrices();
  }, [fetchPrices]);

  useEffect(() => {
    const interval = setInterval(fetchPrices, 2000);
    return () => clearInterval(interval);
  }, [fetchPrices]);

  const handleSort = (columnKey) => {
    if (columns.find(col => col.key === columnKey)?.sortable) {
      setSettings(prev => ({
        ...prev,
        sortBy: columnKey,
        sortOrder: prev.sortBy === columnKey && prev.sortOrder === 'asc' ? 'desc' : 'asc'
      }));
    }
  };

  const getSortIcon = (columnKey) => {
    if (settings.sortBy !== columnKey) return '↕️';
    return settings.sortOrder === 'asc' ? '↑' : '↓';
  };

  const getConnectionStatusInfo = () => {
    switch (connectionStatus) {
      case 'connected':
        return {
          color: 'bg-green-600/20 border-green-600',
          textColor: 'text-green-400',
          icon: 'w-2 h-2 bg-green-500 rounded-full animate-pulse',
          text: `Подключение к MEXC активно • ${activeTickers}/${totalTickers} тикеров • Обновление каждые 2с`
        };
      case 'error':
        return {
          color: 'bg-red-600/20 border-red-600',
          textColor: 'text-red-400',
          icon: 'w-2 h-2 bg-red-500 rounded-full',
          text: 'Ошибка подключения к MEXC'
        };
      default:
        return {
          color: 'bg-yellow-600/20 border-yellow-600',
          textColor: 'text-yellow-400',
          icon: 'w-2 h-2 bg-yellow-500 rounded-full animate-pulse',
          text: 'Подключение к MEXC...'
        };
    }
  };

  const statusInfo = getConnectionStatusInfo();
  const dataArray = Object.entries(priceData);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-800 p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <h2 className="text-white text-2xl font-semibold mb-2">Загрузка MEXC Screener v2.0</h2>
          <p className="text-gray-400">Подключение к оптимизированному API и получение данных по 250+ тикерам...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-800 p-6 relative">
      {/* Settings Panel */}
      <SettingsPanel
        settings={settings}
        onSettingsChange={setSettings}
        isOpen={settingsOpen}
        onToggle={() => setSettingsOpen(!settingsOpen)}
        totalTickers={totalTickers}
        activeTickers={activeTickers}
      />

      <div className="max-w-full mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-5xl font-bold text-white mb-4 tracking-tight">
            MEXC Криптовалютный Скринер
            <span className="text-blue-400 text-2xl ml-3">v2.0</span>
          </h1>
          <div className="flex justify-center items-center space-x-4">
            <Badge variant="secondary" className="px-4 py-2 text-sm">
              250+ Тикеров
            </Badge>
            <Badge variant="outline" className="px-4 py-2 text-sm border-blue-500 text-blue-400">
              Оптимизировано
            </Badge>
            <span className="text-gray-400 text-sm">
              Обновлено: {lastUpdate.toLocaleTimeString()}
            </span>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6">
            <div className="bg-red-600/20 border border-red-600 rounded-lg p-4 text-center">
              <p className="text-red-400">{error}</p>
            </div>
          </div>
        )}

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800/50 rounded-lg p-3 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Отображается</div>
            <div className="text-white text-lg font-bold">{activeTickers}</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Всего доступно</div>
            <div className="text-blue-400 text-lg font-bold">{totalTickers}</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Сортировка</div>
            <div className="text-green-400 text-sm">{settings.sortBy} {getSortIcon(settings.sortBy)}</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Поиск</div>
            <div className="text-yellow-400 text-sm">{settings.search || 'Все'}</div>
          </div>
        </div>

        {/* Price Table */}
        <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="text-white text-2xl">
                Цены криптовалют (MEXC) - {activeTickers} тикеров
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSettingsOpen(true)}
                className="text-blue-400 border-blue-500 hover:bg-blue-600/20"
              >
                ⚙️ Настройки
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700">
                    {columns.map((column) => (
                      <th
                        key={column.key}
                        className={`py-4 px-3 text-gray-300 font-semibold cursor-pointer hover:text-white transition-colors ${
                          column.align === 'right' ? 'text-right' : 
                          column.align === 'center' ? 'text-center' : 'text-left'
                        } ${column.sortable ? 'select-none' : ''}`}
                        onClick={() => column.sortable && handleSort(column.key)}
                      >
                        <div className="flex items-center justify-between">
                          <span>{column.label}</span>
                          {column.sortable && (
                            <span className="ml-1 text-xs opacity-60">
                              {getSortIcon(column.key)}
                            </span>
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dataArray.length === 0 ? (
                    <tr>
                      <td colSpan={columns.length} className="py-8 text-center text-gray-500">
                        {settings.search ? `Не найдено тикеров по запросу "${settings.search}"` : 'Загрузка данных...'}
                      </td>
                    </tr>
                  ) : (
                    dataArray.map(([ticker, data]) => {
                      const change15s = formatShortTermChange(data.change_15s);
                      const change30s = formatShortTermChange(data.change_30s);
                      
                      return (
                        <tr key={ticker} className="border-b border-gray-700/50 hover:bg-gray-700/20 transition-colors">
                          <td className="py-4 px-3">
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
                          
                          <td className="py-4 px-3 text-right">
                            <span className="text-white text-lg font-mono">
                              ${formatPrice(data.price)}
                            </span>
                          </td>
                          
                          <td className="py-4 px-3 text-right">
                            <div className="flex flex-col items-end">
                              <span className={`font-mono text-sm ${change15s.color}`}>
                                {change15s.text}
                              </span>
                              {change15s.absolute && (
                                <span className={`font-mono text-xs ${change15s.color} opacity-70`}>
                                  {change15s.absolute}
                                </span>
                              )}
                            </div>
                          </td>
                          
                          <td className="py-4 px-3 text-right">
                            <div className="flex flex-col items-end">
                              <span className={`font-mono text-sm ${change30s.color}`}>
                                {change30s.text}
                              </span>
                              {change30s.absolute && (
                                <span className={`font-mono text-xs ${change30s.color} opacity-70`}>
                                  {change30s.absolute}
                                </span>
                              )}
                            </div>
                          </td>
                          
                          <td className="py-4 px-3 text-right">
                            <span className={`font-mono ${getPriceChangeColor(data.change24h)}`}>
                              {data.change24h > 0 ? '+' : ''}{formatPrice(data.change24h)}
                            </span>
                          </td>
                          
                          <td className="py-4 px-3 text-right">
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
                          
                          <td className="py-4 px-3 text-right">
                            <span className="text-gray-300 font-mono text-sm">
                              {formatVolume(data.volume)}
                            </span>
                          </td>
                          
                          <td className="py-4 px-3 text-center">
                            <CandleChart
                              candles={data.candles || []}
                              symbol={ticker}
                              width={180}
                              height={50}
                            />
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Status Indicator */}
        <div className="mt-6 text-center">
          <div className={`inline-flex items-center space-x-2 ${statusInfo.color} border rounded-full px-4 py-2`}>
            <div className={statusInfo.icon}></div>
            <span className={`${statusInfo.textColor} text-sm font-medium`}>
              {statusInfo.text}
            </span>
          </div>
          
          <div className="mt-2 text-xs text-gray-500">
            Оптимизированная архитектура • Batch API • 30-сек свечи • Быстрая сортировка и фильтрация
          </div>
        </div>
      </div>
    </div>
  );
};

export default OptimizedCryptoScreener;