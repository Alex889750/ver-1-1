import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import TradingViewChart from './TradingViewChart';
import SettingsPanel from './SettingsPanel';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CompactCryptoScreener = () => {
  const [priceData, setPriceData] = useState({});
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [totalTickers, setTotalTickers] = useState(0);
  const [activeTickers, setActiveTickers] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [expandedRows, setExpandedRows] = useState(new Set());
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [historyStatus, setHistoryStatus] = useState({
    status: 'idle',
    progress: 0,
    total: 0,
    current_symbol: ''
  });
  
  // Настройки с поддержкой настраиваемых интервалов колонок
  const [settings, setSettings] = useState({
    displayCount: 15,
    search: '',
    sortBy: 'symbol',
    sortOrder: 'asc',
    chartTimeframes: ['30s', '1m', '5m'],
    tableIntervals: ['15s', '30s', '24h'], // Настраиваемые интервалы для колонок
    // Настройки для таблицы сигналов
    signalThreshold: 3.0, // Порог превышения (3.0 = отношение 3:1)
    signalCandlesCount: 6, // Количество свечей для расчета среднего (6 минут)
    signalTimeframe: '1m', // Таймфрейм для анализа сигналов
    showSignalsTable: true // Показывать ли таблицу сигналов
  });

  // Состояние для таблицы сигналов
  const [signalsData, setSignalsData] = useState([]);

  // Доступные интервалы для таблицы
  const availableTableIntervals = [
    { value: '2s', label: '2 сек', seconds: 2 },
    { value: '5s', label: '5 сек', seconds: 5 },
    { value: '10s', label: '10 сек', seconds: 10 },
    { value: '15s', label: '15 сек', seconds: 15 },
    { value: '30s', label: '30 сек', seconds: 30 },
    { value: '1m', label: '1 мин', seconds: 60 },
    { value: '2m', label: '2 мин', seconds: 120 },
    { value: '3m', label: '3 мин', seconds: 180 },
    { value: '5m', label: '5 мин', seconds: 300 },
    { value: '10m', label: '10 мин', seconds: 600 },
    { value: '15m', label: '15 мин', seconds: 900 },
    { value: '20m', label: '20 мин', seconds: 1200 },
    { value: '30m', label: '30 мин', seconds: 1800 },
    { value: '1h', label: '60 мин', seconds: 3600 },
    { value: '4h', label: '240 мин', seconds: 14400 },
    { value: '24h', label: '1 день', seconds: 86400 }
  ];

  // Доступные таймфреймы для сигналов
  const availableSignalTimeframes = [
    { value: '1m', label: '1 мин' },
    { value: '2m', label: '2 мин' },
    { value: '3m', label: '3 мин' },
    { value: '5m', label: '5 мин' },
    { value: '15m', label: '15 мин' },
    { value: '20m', label: '20 мин' },
    { value: '30m', label: '30 мин' },
    { value: '1h', label: '60 мин' }
  ];

  // Доступные таймфреймы
  const availableTimeframes = [
    { value: '15s', label: '15 сек', color: '#3b82f6' },
    { value: '30s', label: '30 сек', color: '#10b981' },
    { value: '1m', label: '1 мин', color: '#f59e0b' },
    { value: '5m', label: '5 мин', color: '#8b5cf6' },
    { value: '15m', label: '15 мин', color: '#ec4899' },
    { value: '1h', label: '1 час', color: '#ef4444' },
    { value: '4h', label: '4 часа', color: '#06b6d4' },
    { value: '1d', label: '1 день', color: '#84cc16' },
  ];

  // Dynamic columns based on tableIntervals settings
  const getColumns = () => {
    const baseColumns = [
      { key: 'symbol', label: 'Символ', sortable: true, width: '200px' },
      { key: 'price', label: 'Цена (USDT)', sortable: true, align: 'right', width: '120px' },
    ];
    
    // Add configurable interval columns
    const intervalColumns = settings.tableIntervals.map((interval, index) => {
      const intervalObj = availableTableIntervals.find(i => i.value === interval);
      return {
        key: `change_interval_${index}`,
        label: intervalObj ? intervalObj.label : interval,
        sortable: true,
        align: 'center',
        width: '80px'
      };
    });
    
    const endColumns = [
      { key: 'changePercent24h', label: '24ч %', sortable: true, align: 'center', width: '90px' },
      { key: 'volume', label: 'Объем', sortable: true, align: 'right', width: '100px' },
      { key: 'actions', label: 'Действия', sortable: false, align: 'center', width: '100px' },
    ];
    
    return [...baseColumns, ...intervalColumns, ...endColumns];
  };

  const columns = getColumns();

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
      return { text: 'N/A', color: 'text-gray-500' };
    }
    
    const { percent_change } = changeData;
    const color = getPriceChangeColor(percent_change);
    const sign = percent_change > 0 ? '+' : '';
    
    return {
      text: `${sign}${percent_change.toFixed(2)}%`,
      color
    };
  }, [getPriceChangeColor]);

  const calculateSignals = useCallback((data) => {
    const newSignals = [];
    const currentTime = new Date().toLocaleTimeString('ru-RU', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
    
    Object.entries(data).forEach(([ticker, tickerData]) => {
      // Получаем свечи для расчета (используем выбранный таймфрейм)
      const candles = tickerData.candles?.filter(candle => candle.timeframe === settings.signalTimeframe) || [];
      
      if (candles.length >= settings.signalCandlesCount + 1) {
        // Сортируем свечи по времени (последние сначала)
        const sortedCandles = candles.sort((a, b) => b.timestamp - a.timestamp);
        
        // Последняя свеча (за последнюю минуту)
        const latestCandle = sortedCandles[0];
        const previousCandle = sortedCandles[1];
        
        // Изменение цены за последнюю минуту (с учетом знака)
        const lastMinutePriceChange = latestCandle.close - previousCandle.close;
        
        // Берем предыдущие N свечей для расчета среднего изменения
        const historicalCandles = sortedCandles.slice(1, settings.signalCandlesCount + 1);
        
        if (historicalCandles.length === settings.signalCandlesCount && Math.abs(lastMinutePriceChange) > 0.0001) {
          // Рассчитываем среднее изменение цены за предыдущие N минут
          let totalPriceChange = 0;
          let validChanges = 0;
          
          for (let i = 0; i < historicalCandles.length - 1; i++) {
            const current = historicalCandles[i];
            const previous = historicalCandles[i + 1];
            const priceChange = current.close - previous.close;
            totalPriceChange += priceChange;
            validChanges++;
          }
          
          const averagePriceChange = validChanges > 0 ? totalPriceChange / validChanges : 0;
          
          // Избегаем деления на ноль и очень маленькие значения
          if (Math.abs(averagePriceChange) > 0.0001) {
            
            // ВАЖНО: Проверяем совпадение направлений движения
            const lastMinutePositive = lastMinutePriceChange > 0;
            const averagePositive = averagePriceChange > 0;
            
            // Сигнал только если направления совпадают
            if (lastMinutePositive === averagePositive) {
              // Рассчитываем отношение изменений цен (оба значения с одинаковыми знаками)
              const ratio = Math.abs(lastMinutePriceChange) / Math.abs(averagePriceChange);
              
              // Проверяем превышение порога
              if (ratio >= settings.signalThreshold) {
                const isPositive = lastMinutePriceChange > 0;
                
                newSignals.push({
                  id: `${ticker}-${Date.now()}`,
                  time: currentTime,
                  ticker: ticker,
                  value: ratio.toFixed(2),
                  isPositive: isPositive,
                  lastMinuteChange: lastMinutePriceChange.toFixed(6),
                  averageChange: averagePriceChange.toFixed(6),
                  ratio: ratio,
                  trendDirection: isPositive ? 'рост' : 'падение'
                });
              }
            }
          }
        }
      }
    });
    
    if (newSignals.length > 0) {
      setSignalsData(prev => {
        // Добавляем новые сигналы и ограничиваем до 50 последних
        const updated = [...newSignals, ...prev].slice(0, 50);
        return updated;
      });
    }
  }, [settings.signalThreshold, settings.signalCandlesCount, settings.signalTimeframe]);

  const formatConfigurableChange = useCallback((data, intervalIndex) => {
    const changeKey = `change_interval_${intervalIndex}`;
    const changeData = data[changeKey];
    return formatShortTermChange(changeData);
  }, [formatShortTermChange]);

  const fetchPrices = useCallback(async () => {
    try {
      setError(null);
      
      const params = new URLSearchParams({
        limit: settings.displayCount.toString(),
        sort_by: settings.sortBy,
        sort_order: settings.sortOrder,
        timeframes: settings.chartTimeframes.join(','), // Передаем выбранные таймфреймы
        interval_configs: settings.tableIntervals.join(','), // Передаем настраиваемые интервалы
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
        
        // Рассчитываем сигналы если включена таблица сигналов
        if (settings.showSignalsTable) {
          calculateSignals(response.data.data);
        }
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
    const interval = setInterval(fetchPrices, 3000); // 3 секунды для менее частого обновления
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

  const loadHistory = async () => {
    try {
      setHistoryLoading(true);
      setHistoryStatus({ status: 'loading', progress: 0, total: 0, current_symbol: '' });
      
      // Запускаем загрузку истории
      const response = await axios.post(`${API}/crypto/load-history`);
      
      if (response.data.status === 'started') {
        // Начинаем опрос статуса
        pollHistoryStatus();
      } else {
        throw new Error('Failed to start history loading');
      }
    } catch (err) {
      console.error('Error loading history:', err);
      setError('Ошибка загрузки истории');
      setHistoryLoading(false);
    }
  };

  const pollHistoryStatus = async () => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get(`${API}/crypto/history-status`);
        const status = response.data;
        
        setHistoryStatus(status);
        
        if (status.status === 'completed') {
          setHistoryLoading(false);
          setHistoryLoaded(true);
          clearInterval(pollInterval);
        } else if (status.status === 'error') {
          setHistoryLoading(false);
          setError('Ошибка при загрузке исторических данных');
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error('Error polling history status:', err);
        clearInterval(pollInterval);
        setHistoryLoading(false);
      }
    }, 1000); // Опрос каждую секунду
    
    // Автоматически останавливаем опрос через 5 минут (таймаут)
    setTimeout(() => {
      clearInterval(pollInterval);
      if (historyLoading) {
        setHistoryLoading(false);
        setError('Таймаут загрузки истории');
      }
    }, 300000); // 5 минут
  };

  const toggleRowExpansion = (ticker) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(ticker)) {
      newExpanded.delete(ticker);
    } else {
      newExpanded.add(ticker);
    }
    setExpandedRows(newExpanded);
  };

  const getConnectionStatusInfo = () => {
    switch (connectionStatus) {
      case 'connected':
        return {
          color: 'bg-green-600/20 border-green-600',
          textColor: 'text-green-400',
          icon: 'w-2 h-2 bg-green-500 rounded-full animate-pulse',
          text: `MEXC подключен • ${activeTickers}/${totalTickers} тикеров • TradingView графики`
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
          <h2 className="text-white text-2xl font-semibold mb-2">Загрузка TradingView Screener</h2>
          <p className="text-gray-400">Инициализация продвинутых графиков и множественных таймфреймов...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-800 p-4 relative">
      {/* Settings Panel */}
      <SettingsPanel
        settings={settings}
        onSettingsChange={setSettings}
        isOpen={settingsOpen}
        onToggle={() => setSettingsOpen(!settingsOpen)}
        totalTickers={totalTickers}
        activeTickers={activeTickers}
        availableTimeframes={availableTimeframes}
        availableTableIntervals={availableTableIntervals}
        availableSignalTimeframes={availableSignalTimeframes}
      />

      <div className="max-w-full mx-auto">
        {/* Header */}
        <div className="mb-6 text-center">
          <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">
            MEXC TradingView Screener
            <span className="text-blue-400 text-xl ml-2">Pro</span>
          </h1>
          <div className="flex justify-center items-center space-x-3">
            <Badge variant="secondary" className="px-3 py-1 text-xs">
              📊 TradingView Charts
            </Badge>
            <Badge variant="outline" className="px-3 py-1 text-xs border-blue-500 text-blue-400">
              8 таймфреймов
            </Badge>
            <span className="text-gray-400 text-sm">
              {lastUpdate.toLocaleTimeString()}
            </span>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4">
            <div className="bg-red-600/20 border border-red-600 rounded-lg p-3 text-center">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
          <div className="bg-gray-800/50 rounded-lg p-2 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Показано</div>
            <div className="text-white text-sm font-bold">{activeTickers}</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Доступно</div>
            <div className="text-blue-400 text-sm font-bold">{totalTickers}</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Сортировка</div>
            <div className="text-green-400 text-sm">{settings.sortBy} {getSortIcon(settings.sortBy)}</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Графики</div>
            <div className="text-purple-400 text-sm">{settings.chartTimeframes.length} TF</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Поиск</div>
            <div className="text-yellow-400 text-sm">{settings.search || 'Все'}</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">История</div>
            {historyLoading ? (
              <div className="text-orange-400 text-sm">
                {historyStatus.total > 0 ? 
                  `${historyStatus.progress}/${historyStatus.total}` : 
                  'Загрузка...'
                }
              </div>
            ) : historyLoaded ? (
              <div className="text-green-400 text-sm">✓ Готово</div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                onClick={loadHistory}
                className="text-xs px-2 py-0.5 h-auto border-blue-500 text-blue-400 hover:bg-blue-600/20"
              >
                Загрузить
              </Button>
            )}
          </div>
        </div>

        {/* Compact Price Table */}
        <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
          <CardHeader className="pb-2">
            <div className="flex justify-between items-center">
              <CardTitle className="text-white text-xl">
                Компактная таблица • {activeTickers} тикеров
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
          <CardContent className="pt-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700">
                    {columns.map((column) => (
                      <th
                        key={column.key}
                        style={{ width: column.width }}
                        className={`py-2 text-gray-300 font-medium cursor-pointer hover:text-white transition-colors ${
                          column.align === 'right' ? 'text-right pl-2 pr-3' : 
                          column.align === 'center' ? 'text-center pl-4 pr-2' : 'text-left pl-3 pr-2'
                        } ${column.sortable ? 'select-none' : ''}`}
                        onClick={() => column.sortable && handleSort(column.key)}
                      >
                        <div className={`flex items-center text-xs ${
                          column.align === 'right' ? 'justify-end' : 
                          column.align === 'center' ? 'justify-center' : 'justify-between'
                        }`}>
                          <span>{column.label}</span>
                          {column.sortable && column.align !== 'center' && column.align !== 'right' && (
                            <span className="ml-1 opacity-60">
                              {getSortIcon(column.key)}
                            </span>
                          )}
                          {column.sortable && (column.align === 'center' || column.align === 'right') && (
                            <span className="ml-1 opacity-60">
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
                      <td colSpan={columns.length} className="py-6 text-center text-gray-500">
                        {settings.search ? `Не найдено: "${settings.search}"` : 'Загрузка...'}
                      </td>
                    </tr>
                  ) : (
                    dataArray.map(([ticker, data]) => {
                      const change15s = formatShortTermChange(data.change_15s);
                      const change30s = formatShortTermChange(data.change_30s);
                      const isExpanded = expandedRows.has(ticker);
                      
                      return (
                        <React.Fragment key={ticker}>
                          {/* Компактная строка данных */}
                          <tr className="border-b border-gray-700/30 hover:bg-gray-700/10 transition-colors">
                            <td className="py-2 px-2">
                              <span className="text-white font-mono text-sm">
                                {formatCurrency(ticker)}
                              </span>
                            </td>
                            
                            <td className="py-2 px-2 text-right">
                              <span className="text-white font-mono text-sm">
                                ${formatPrice(data.price)}
                              </span>
                            </td>
                            
                            {/* Dynamic interval columns */}
                            {settings.tableIntervals.map((interval, index) => {
                              const changeData = formatConfigurableChange(data, index);
                              return (
                                <td key={`interval-${index}`} className="py-2 px-2 text-center">
                                  <span className={`font-mono text-sm ${changeData.color}`}>
                                    {changeData.text}
                                  </span>
                                </td>
                              );
                            })}
                            
                            <td className="py-2 px-2 text-center">
                              <span className={`font-mono text-sm ${
                                data.changePercent24h >= 0 
                                  ? 'text-green-400' 
                                  : 'text-red-400'
                              }`}>
                                {data.changePercent24h > 0 ? '+' : ''}{data.changePercent24h.toFixed(2)}%
                              </span>
                            </td>
                            
                            <td className="py-2 px-2 text-right">
                              <span className="text-gray-300 font-mono text-sm">
                                {formatVolume(data.volume)}
                              </span>
                            </td>
                            
                            <td className="py-2 px-2 text-center">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => toggleRowExpansion(ticker)}
                                className="text-blue-400 hover:bg-blue-600/20 px-2 py-1"
                              >
                                📊 {isExpanded ? '▼' : '▶'}
                              </Button>
                            </td>
                          </tr>
                          
                          {/* Развернутая строка с графиками */}
                          {isExpanded && (
                            <tr className="bg-gray-800/30">
                              <td colSpan={columns.length} className="py-4 px-4">
                                {/* Наши графики MEXC с увеличенной высотой */}
                                <div className="space-y-4">
                                  <div className="flex items-center justify-between mb-3">
                                    <h4 className="text-white font-semibold">
                                      📊 Краткосрочные графики - {formatCurrency(ticker)}
                                    </h4>
                                    <div className="text-xs text-gray-400">
                                      {settings.chartTimeframes.length} активных таймфрейма • MEXC данные
                                    </div>
                                  </div>
                                  
                                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    {settings.chartTimeframes.map((timeframe) => {
                                      // Фильтруем свечи только для данного таймфрейма
                                      const timeframeCandles = (data.candles || []).filter(candle => 
                                        candle.timeframe === timeframe
                                      );
                                      
                                      return (
                                        <div key={timeframe} className="space-y-2">
                                          <TradingViewChart
                                            candles={timeframeCandles}
                                            symbol={ticker}
                                            timeframe={timeframe}
                                            width={300}
                                            height={180}
                                          />
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                                
                                <div className="mt-6 text-center">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => toggleRowExpansion(ticker)}
                                    className="text-gray-400 border-gray-600"
                                  >
                                    Скрыть графики ▲
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Signals Table */}
        {settings.showSignalsTable && (
          <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm mt-6">
            <CardHeader className="pb-2">
              <div className="flex justify-between items-center">
                <CardTitle className="text-white text-xl">
                  🚨 Таблица сигналов • Порог: {settings.signalThreshold.toFixed(2)} • {signalsData.length} сигналов
                </CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSignalsData([])}
                  className="text-red-400 border-red-500 hover:bg-red-600/20"
                >
                  Очистить
                </Button>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="py-2 px-3 text-left text-gray-300 font-medium text-xs">
                        Время
                      </th>
                      <th className="py-2 px-3 text-left text-gray-300 font-medium text-xs">
                        Тикер
                      </th>
                      <th className="py-2 px-3 text-right text-gray-300 font-medium text-xs">
                        Превышение порога
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {signalsData.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="py-6 text-center text-gray-500">
                          Сигналы не обнаружены
                        </td>
                      </tr>
                    ) : (
                      signalsData.map((signal) => (
                        <tr key={signal.id} className="border-b border-gray-700/30 hover:bg-gray-700/10 transition-colors">
                          <td className="py-2 px-3">
                            <span className="text-gray-300 font-mono text-xs">
                              {signal.time}
                            </span>
                          </td>
                          <td className="py-2 px-3">
                            <span className="text-white font-mono text-sm">
                              {formatCurrency(signal.ticker)}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-right">
                            <div className="flex flex-col items-end space-y-1">
                              <Badge 
                                variant={signal.isPositive ? "default" : "destructive"}
                                className={`font-mono text-xs px-2 py-1 ${
                                  signal.isPositive 
                                    ? 'bg-green-600/80 text-green-100' 
                                    : 'bg-red-600/80 text-red-100'
                                }`}
                              >
                                {signal.value}
                              </Badge>
                              <div className="text-xs text-gray-500 font-mono">
                                {signal.lastMinuteChange} / {signal.averageChange}
                              </div>
                              <div className="text-xs text-gray-400">
                                {signal.trendDirection} усилен
                              </div>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              {signalsData.length > 0 && (
                <div className="mt-3 text-center text-xs text-gray-500">
                  Показано последние {signalsData.length} сигналов (максимум 50)
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Status Indicator */}
        <div className="mt-6 text-center">
          <div className={`inline-flex items-center space-x-2 ${statusInfo.color} border rounded-full px-4 py-2`}>
            <div className={statusInfo.icon}></div>
            <span className={`${statusInfo.textColor} text-sm font-medium`}>
              {statusInfo.text}
            </span>
          </div>
          
          <div className="mt-2 text-xs text-gray-500">
            TradingView стиль • 8 таймфреймов • Компактный дизайн • Продвинутая аналитика
          </div>
        </div>
      </div>
    </div>
  );
};

export default CompactCryptoScreener;