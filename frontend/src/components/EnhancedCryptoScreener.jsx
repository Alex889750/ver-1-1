import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import TradingViewChart from './TradingViewChart';
import AdvancedSettingsPanel from './AdvancedSettingsPanel';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const EnhancedCryptoScreener = () => {
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
  
  // Расширенные настройки
  const [settings, setSettings] = useState({
    displayCount: 15,
    search: '',
    sortBy: 'symbol',
    sortOrder: 'asc',
    chartTimeframes: ['30s', '1m', '5m'],
    customFilters: [
      { interval: 'none', operator: '>', value: 0 },
      { interval: 'none', operator: '>', value: 0 },
      { interval: 'none', operator: '>', value: 0 }
    ],
    // Настраиваемые интервалы для колонок таблицы
    tableIntervals: ['15s', '30s', '24h']
  });

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

  // Компактные колонки (с настраиваемыми интервалами)
  const columns = [
    { key: 'symbol', label: 'Символ', sortable: true, width: '200px' },
    { key: 'price', label: 'Цена (USDT)', sortable: true, align: 'right', width: '120px' },
    { 
      key: 'change_interval_0', 
      label: availableTableIntervals.find(i => i.value === settings.tableIntervals[0])?.label || '15с', 
      sortable: true, 
      align: 'right', 
      width: '80px' 
    },
    { 
      key: 'change_interval_1', 
      label: availableTableIntervals.find(i => i.value === settings.tableIntervals[1])?.label || '30с', 
      sortable: true, 
      align: 'right', 
      width: '80px' 
    },
    { 
      key: 'change_interval_2', 
      label: availableTableIntervals.find(i => i.value === settings.tableIntervals[2])?.label || '24ч %', 
      sortable: true, 
      align: 'right', 
      width: '90px' 
    },
    { key: 'volume', label: 'Объем', sortable: true, align: 'right', width: '100px' },
    { key: 'actions', label: 'Действия', sortable: false, align: 'center', width: '100px' },
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

  // Получаем изменение цены для настраиваемого интервала
  const getCustomIntervalChange = useCallback((data, intervalValue) => {
    const interval = availableTableIntervals.find(i => i.value === intervalValue);
    if (!interval) return { text: 'N/A', color: 'text-gray-500' };
    
    // Для 24h используем данные MEXC
    if (intervalValue === '24h') {
      const percent_change = data.changePercent24h || 0;
      const color = getPriceChangeColor(percent_change);
      const sign = percent_change > 0 ? '+' : '';
      return {
        text: `${sign}${percent_change.toFixed(2)}%`,
        color
      };
    }
    
    // Для других интервалов используем динамически вычисленные данные
    const changeKey = `change_${interval.seconds}s`;
    const changeData = data[changeKey];
    
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
  }, [availableTableIntervals, getPriceChangeColor]);

  // Проверка соответствия кастомным фильтрам
  const passesCustomFilters = useCallback((data) => {
    for (const filter of settings.customFilters) {
      if (filter.interval === 'none') continue;
      
      // Получаем значение изменения для данного интервала
      let changePercent = 0;
      if (filter.interval === '15s' && data.change_15s) {
        changePercent = data.change_15s.percent_change;
      } else if (filter.interval === '30s' && data.change_30s) {
        changePercent = data.change_30s.percent_change;
      } else if (filter.interval === '24h') {
        changePercent = data.changePercent24h;
      }
      // Можно добавить больше интервалов когда они будут доступны
      
      // Применяем оператор
      switch (filter.operator) {
        case '>':
          if (!(changePercent > filter.value)) return false;
          break;
        case '>=':
          if (!(changePercent >= filter.value)) return false;
          break;
        case '<':
          if (!(changePercent < filter.value)) return false;
          break;
        case '<=':
          if (!(changePercent <= filter.value)) return false;
          break;
        case '=':
          if (Math.abs(changePercent - filter.value) > 0.01) return false;
          break;
        default:
          break;
      }
    }
    return true;
  }, [settings.customFilters]);

  const loadHistoricalData = async () => {
    try {
      setHistoryLoading(true);
      const response = await axios.post(`${API}/crypto/load-history`);
      
      if (response.data && response.data.success) {
        setHistoryLoaded(true);
        // Обновляем данные после загрузки истории
        await fetchPrices();
      }
    } catch (err) {
      console.error('Error loading historical data:', err);
      setError('Ошибка загрузки исторических данных');
    } finally {
      setHistoryLoading(false);
    }
  };

  const checkHistoryStatus = async () => {
    try {
      const response = await axios.get(`${API}/crypto/history-status`);
      if (response.data) {
        setHistoryLoaded(response.data.historical_data_loaded);
      }
    } catch (err) {
      console.error('Error checking history status:', err);
    }
  };

  useEffect(() => {
    checkHistoryStatus();
  }, []);

  const fetchPrices = useCallback(async () => {
    try {
      setError(null);
      
      const params = new URLSearchParams({
        limit: settings.displayCount.toString(),
        sort_by: settings.sortBy,
        sort_order: settings.sortOrder,
        timeframes: settings.chartTimeframes.join(','),
        intervals: settings.tableIntervals.join(','), // Передаем настраиваемые интервалы
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
    const interval = setInterval(fetchPrices, 3000);
    return () => clearInterval(interval);
  }, [fetchPrices]);

  const handleSort = (columnKey) => {
    const column = columns.find(col => col.key === columnKey);
    if (!column?.sortable) return;
    
    // Определяем реальный ключ для сортировки
    let realSortKey = columnKey;
    
    // Для настраиваемых интервальных колонок используем соответствующий интервал
    if (columnKey === 'change_interval_0') {
      const interval = settings.tableIntervals[0];
      realSortKey = interval === '24h' ? 'changePercent24h' : `change_${convert_interval_to_seconds_frontend(interval)}s`;
    } else if (columnKey === 'change_interval_1') {
      const interval = settings.tableIntervals[1]; 
      realSortKey = interval === '24h' ? 'changePercent24h' : `change_${convert_interval_to_seconds_frontend(interval)}s`;
    } else if (columnKey === 'change_interval_2') {
      const interval = settings.tableIntervals[2];
      realSortKey = interval === '24h' ? 'changePercent24h' : `change_${convert_interval_to_seconds_frontend(interval)}s`;
    }
    
    setSettings(prev => ({
      ...prev,
      sortBy: realSortKey,
      sortOrder: prev.sortBy === realSortKey && prev.sortOrder === 'asc' ? 'desc' : 'asc'
    }));
  };
  
  // Функция для конвертации интервала в секунды (frontend версия)
  const convert_interval_to_seconds_frontend = (interval) => {
    const interval_map = {
      '2s': 2, '5s': 5, '10s': 10, '15s': 15, '30s': 30,
      '1m': 60, '2m': 120, '3m': 180, '5m': 300, '10m': 600,
      '15m': 900, '20m': 1200, '30m': 1800, '1h': 3600,
      '4h': 14400, '24h': 86400
    };
    return interval_map[interval] || 15;
  };

  const getSortIcon = (columnKey) => {
    // Определяем реальный ключ для сортировки
    let realSortKey = columnKey;
    
    if (columnKey === 'change_interval_0') {
      const interval = settings.tableIntervals[0];
      realSortKey = interval === '24h' ? 'changePercent24h' : `change_${convert_interval_to_seconds_frontend(interval)}s`;
    } else if (columnKey === 'change_interval_1') {
      const interval = settings.tableIntervals[1];
      realSortKey = interval === '24h' ? 'changePercent24h' : `change_${convert_interval_to_seconds_frontend(interval)}s`;
    } else if (columnKey === 'change_interval_2') {
      const interval = settings.tableIntervals[2];
      realSortKey = interval === '24h' ? 'changePercent24h' : `change_${convert_interval_to_seconds_frontend(interval)}s`;
    }
    
    if (settings.sortBy !== realSortKey) return '↕️';
    return settings.sortOrder === 'asc' ? '↑' : '↓';
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
          text: `MEXC подключен • ${activeTickers}/${totalTickers} тикеров • Кастомные фильтры`
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
  
  // Применяем кастомные фильтры к данным
  const filteredData = Object.entries(priceData).filter(([ticker, data]) => {
    return passesCustomFilters(data);
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-800 p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <h2 className="text-white text-2xl font-semibold mb-2">Загрузка Enhanced Screener</h2>
          <p className="text-gray-400">Инициализация кастомных фильтров и исторических данных...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-800 p-4 relative">
      {/* Settings Panel */}
      <AdvancedSettingsPanel
        settings={settings}
        onSettingsChange={setSettings}
        isOpen={settingsOpen}
        onToggle={() => setSettingsOpen(!settingsOpen)}
        totalTickers={totalTickers}
        activeTickers={filteredData.length}
        availableTimeframes={availableTimeframes}
      />

      <div className="max-w-full mx-auto">
        {/* Header */}
        <div className="mb-6 text-center">
          <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">
            MEXC Enhanced Screener
            <span className="text-blue-400 text-xl ml-2">v3.1</span>
          </h1>
          <div className="flex justify-center items-center space-x-3">
            <Badge variant="secondary" className="px-3 py-1 text-xs">
              🔍 Кастомные фильтры
            </Badge>
            <Badge variant="outline" className="px-3 py-1 text-xs border-blue-500 text-blue-400">
              16 интервалов
            </Badge>
            {historyLoaded && (
              <Badge variant="outline" className="px-3 py-1 text-xs border-green-500 text-green-400">
                📊 История загружена
              </Badge>
            )}
            <span className="text-gray-400 text-sm">
              {lastUpdate.toLocaleTimeString()}
            </span>
          </div>
          
          {/* Кнопка загрузки истории */}
          {!historyLoaded && (
            <div className="mt-4">
              <Button
                onClick={loadHistoricalData}
                disabled={historyLoading}
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-6 py-2 rounded-lg font-semibold shadow-lg"
              >
                {historyLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    Загружаем историю...
                  </>
                ) : (
                  <>
                    📊 Загрузить историю графиков
                  </>
                )}
              </Button>
              <p className="text-gray-400 text-sm mt-2">
                Загрузит последние 50 свечей для всех таймфреймов
              </p>
            </div>
          )}
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
            <div className="text-white text-sm font-bold">{filteredData.length}</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Всего</div>
            <div className="text-blue-400 text-sm font-bold">{totalTickers}</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Интервалы</div>
            <div className="text-green-400 text-sm">
              {settings.tableIntervals ? settings.tableIntervals.map(i => 
                availableTableIntervals.find(opt => opt.value === i)?.label.split(' ')[0] || i
              ).join(', ') : '15с, 30с, 24ч'}
            </div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Графики</div>
            <div className="text-purple-400 text-sm">{settings.chartTimeframes.length} TF</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">История</div>
            <div className={`text-sm font-bold ${historyLoaded ? 'text-green-400' : 'text-yellow-400'}`}>
              {historyLoaded ? '✅ Да' : '⏳ Нет'}
            </div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 text-center border border-gray-700">
            <div className="text-gray-400 text-xs">Фильтры</div>
            <div className="text-orange-400 text-sm">
              {settings.customFilters.filter(f => f.interval !== 'none').length}/3
            </div>
          </div>
        </div>

        {/* Enhanced Price Table */}
        <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm">
          <CardHeader className="pb-2">
            <div className="flex justify-between items-center">
              <CardTitle className="text-white text-xl">
                Enhanced таблица • {filteredData.length} тикеров
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
                        className={`py-2 px-2 text-gray-300 font-medium cursor-pointer hover:text-white transition-colors ${
                          column.align === 'right' ? 'text-right' : 
                          column.align === 'center' ? 'text-center' : 'text-left'
                        } ${column.sortable ? 'select-none' : ''}`}
                        onClick={() => column.sortable && handleSort(column.key)}
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span>{column.label}</span>
                          {column.sortable && (
                            <span className="ml-1 opacity-60">
                              {getSortIcon(column.key)}
                            </span>
                          )}
                        </div>
                        {/* Сортировка мин/макс под заголовком */}
                        {column.sortable && column.key !== 'symbol' && (
                          <div className="flex gap-1 mt-1 justify-center">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                
                                // Определяем реальный ключ для сортировки
                                let realSortKey = column.key;
                                if (column.key === 'change_interval_0') {
                                  const interval = settings.tableIntervals[0];
                                  realSortKey = interval === '24h' ? 'changePercent24h' : `change_${convert_interval_to_seconds_frontend(interval)}s`;
                                } else if (column.key === 'change_interval_1') {
                                  const interval = settings.tableIntervals[1];
                                  realSortKey = interval === '24h' ? 'changePercent24h' : `change_${convert_interval_to_seconds_frontend(interval)}s`;
                                } else if (column.key === 'change_interval_2') {
                                  const interval = settings.tableIntervals[2];
                                  realSortKey = interval === '24h' ? 'changePercent24h' : `change_${convert_interval_to_seconds_frontend(interval)}s`;
                                }
                                
                                setSettings(prev => ({
                                  ...prev,
                                  sortBy: realSortKey,
                                  sortOrder: 'desc'
                                }));
                              }}
                              className="text-xs px-1 py-0.5 rounded bg-red-600/20 text-red-400 hover:bg-red-600/30"
                            >
                              Max
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                
                                // Определяем реальный ключ для сортировки
                                let realSortKey = column.key;
                                if (column.key === 'change_interval_0') {
                                  const interval = settings.tableIntervals[0];
                                  realSortKey = interval === '24h' ? 'changePercent24h' : `change_${convert_interval_to_seconds_frontend(interval)}s`;
                                } else if (column.key === 'change_interval_1') {
                                  const interval = settings.tableIntervals[1];
                                  realSortKey = interval === '24h' ? 'changePercent24h' : `change_${convert_interval_to_seconds_frontend(interval)}s`;
                                } else if (column.key === 'change_interval_2') {
                                  const interval = settings.tableIntervals[2];
                                  realSortKey = interval === '24h' ? 'changePercent24h' : `change_${convert_interval_to_seconds_frontend(interval)}s`;
                                }
                                
                                setSettings(prev => ({
                                  ...prev,
                                  sortBy: realSortKey,
                                  sortOrder: 'asc'
                                }));
                              }}
                              className="text-xs px-1 py-0.5 rounded bg-green-600/20 text-green-400 hover:bg-green-600/30"
                            >
                              Min
                            </button>
                          </div>
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredData.length === 0 ? (
                    <tr>
                      <td colSpan={columns.length} className="py-6 text-center text-gray-500">
                        {settings.search ? `Не найдено: "${settings.search}"` : 'Нет данных, соответствующих фильтрам'}
                      </td>
                    </tr>
                  ) : (
                    filteredData.map(([ticker, data]) => {
                      const change0 = getCustomIntervalChange(data, settings.tableIntervals[0]);
                      const change1 = getCustomIntervalChange(data, settings.tableIntervals[1]);
                      const change2 = getCustomIntervalChange(data, settings.tableIntervals[2]);
                      const isExpanded = expandedRows.has(ticker);
                      
                      return (
                        <React.Fragment key={ticker}>
                          {/* Компактная строка данных */}
                          <tr className="border-b border-gray-700/30 hover:bg-gray-700/10 transition-colors">
                            <td className="py-2 px-2">
                              <div className="flex items-center space-x-2">
                                <div className="w-6 h-6 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center">
                                  <span className="text-white text-xs font-bold">
                                    {formatCurrency(ticker).substring(0, 1)}
                                  </span>
                                </div>
                                <div>
                                  <div className="text-white font-semibold text-sm">{formatCurrency(ticker)}</div>
                                  <div className="text-gray-500 text-xs">{ticker}</div>
                                </div>
                              </div>
                            </td>
                            
                            <td className="py-2 px-2 text-right">
                              <span className="text-white font-mono text-sm">
                                ${formatPrice(data.price)}
                              </span>
                            </td>
                            
                            {/* Первый настраиваемый интервал */}
                            <td className="py-2 px-2 text-right">
                              <span className={`font-mono text-xs ${change0.color}`}>
                                {change0.text}
                              </span>
                            </td>
                            
                            {/* Второй настраиваемый интервал */}
                            <td className="py-2 px-2 text-right">
                              <span className={`font-mono text-xs ${change1.color}`}>
                                {change1.text}
                              </span>
                            </td>
                            
                            {/* Третий настраиваемый интервал */}
                            <td className="py-2 px-2 text-right">
                              {settings.tableIntervals[2] === '24h' ? (
                                // Специальный дизайн для 24ч %
                                <span className={`font-mono text-xs border rounded px-2 py-1 ${
                                  data.changePercent24h >= 0 
                                    ? 'border-green-500 text-green-400' 
                                    : 'border-red-500 text-red-400'
                                }`}>
                                  {change2.text}
                                </span>
                              ) : (
                                // Обычный дизайн для других интервалов
                                <span className={`font-mono text-xs ${change2.color}`}>
                                  {change2.text}
                                </span>
                              )}
                            </td>
                            
                            <td className="py-2 px-2 text-right">
                              <span className="text-gray-300 font-mono text-xs">
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
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                  {settings.chartTimeframes.map((timeframe) => {
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
                                          height={120}
                                        />
                                      </div>
                                    );
                                  })}
                                </div>
                                <div className="mt-3 text-center">
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

        {/* Status Indicator */}
        <div className="mt-6 text-center">
          <div className={`inline-flex items-center space-x-2 ${statusInfo.color} border rounded-full px-4 py-2`}>
            <div className={statusInfo.icon}></div>
            <span className={`${statusInfo.textColor} text-sm font-medium`}>
              {statusInfo.text}
            </span>
          </div>
          
          <div className="mt-2 text-xs text-gray-500">
            Enhanced фильтры • 16 временных интервалов • Исторические данные • Pro аналитика
          </div>
        </div>
      </div>
    </div>
  );
};

export default EnhancedCryptoScreener;