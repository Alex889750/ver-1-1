import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Checkbox } from './ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

const AdvancedSettingsPanel = ({ 
  settings, 
  onSettingsChange, 
  isOpen, 
  onToggle,
  totalTickers = 0,
  activeTickers = 0,
  availableTimeframes = []
}) => {
  // Доступные интервалы для фильтров
  const availableIntervals = [
    { value: 'none', label: 'Нет', seconds: 0 },
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
    { value: '1d', label: '1 день', seconds: 86400 }
  ];

  const handleDisplayCountChange = (e) => {
    const value = Math.max(1, Math.min(30, parseInt(e.target.value) || 10));
    onSettingsChange({
      ...settings,
      displayCount: value
    });
  };

  const handleSearchChange = (e) => {
    onSettingsChange({
      ...settings,
      search: e.target.value
    });
  };

  const handleTimeframeToggle = (timeframe) => {
    const currentTimeframes = settings.chartTimeframes || ['30s', '1m', '5m'];
    let newTimeframes;
    
    if (currentTimeframes.includes(timeframe)) {
      newTimeframes = currentTimeframes.filter(tf => tf !== timeframe);
      if (newTimeframes.length === 0) {
        newTimeframes = [timeframe];
      }
    } else {
      if (currentTimeframes.length < 3) {
        newTimeframes = [...currentTimeframes, timeframe];
      } else {
        newTimeframes = [...currentTimeframes.slice(0, 2), timeframe];
      }
    }
    
    onSettingsChange({
      ...settings,
      chartTimeframes: newTimeframes
    });
  };

  const handleFilterChange = (filterIndex, type, value) => {
    const currentFilters = settings.customFilters || [
      { interval: 'none', operator: '>', value: 0 },
      { interval: 'none', operator: '>', value: 0 },
      { interval: 'none', operator: '>', value: 0 }
    ];
    
    const newFilters = [...currentFilters];
    newFilters[filterIndex] = { ...newFilters[filterIndex], [type]: value };
    
    onSettingsChange({
      ...settings,
      customFilters: newFilters
    });
  };

  const currentFilters = settings.customFilters || [
    { interval: 'none', operator: '>', value: 0 },
    { interval: 'none', operator: '>', value: 0 },
    { interval: 'none', operator: '>', value: 0 }
  ];

  if (!isOpen) {
    return (
      <div className="fixed top-4 right-4 z-50">
        <Button 
          onClick={onToggle}
          className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg"
        >
          ⚙️ Настройки
        </Button>
      </div>
    );
  }

  return (
    <div className="fixed top-4 right-4 z-50 w-96">
      <Card className="bg-gray-800/95 border-gray-700 backdrop-blur-sm shadow-2xl max-h-screen overflow-y-auto">
        <CardHeader className="pb-3">
          <div className="flex justify-between items-center">
            <CardTitle className="text-white text-lg">⚙️ Продвинутые настройки</CardTitle>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={onToggle}
              className="text-gray-400 hover:text-white"
            >
              ✕
            </Button>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* Статистика */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-gray-700/50 rounded-lg p-2 text-center">
              <div className="text-xs text-gray-400">Всего тикеров</div>
              <div className="text-white font-bold">{totalTickers}</div>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-2 text-center">
              <div className="text-xs text-gray-400">Активные</div>
              <div className="text-green-400 font-bold">{activeTickers}</div>
            </div>
          </div>

          {/* Количество отображаемых тикеров */}
          <div className="space-y-2">
            <Label className="text-gray-300 text-sm font-medium">
              Тикеров на экране (1-30)
            </Label>
            <Input
              type="number"
              min="1"
              max="30"
              value={settings.displayCount}
              onChange={handleDisplayCountChange}
              className="bg-gray-700 border-gray-600 text-white"
              placeholder="10"
            />
            <div className="text-xs text-gray-500">
              Текущее значение: {settings.displayCount}
            </div>
          </div>

          {/* Поиск */}
          <div className="space-y-2">
            <Label className="text-gray-300 text-sm font-medium">
              Поиск по символу
            </Label>
            <Input
              type="text"
              value={settings.search}
              onChange={handleSearchChange}
              className="bg-gray-700 border-gray-600 text-white"
              placeholder="Например: BTC, ETH..."
            />
            {settings.search && (
              <div className="text-xs text-gray-500">
                Поиск: "{settings.search}"
              </div>
            )}
          </div>

          {/* Настраиваемые фильтры */}
          <div className="space-y-3">
            <Label className="text-gray-300 text-sm font-medium">
              🔍 Настраиваемые фильтры (3 столбца)
            </Label>
            {currentFilters.map((filter, index) => (
              <div key={index} className="bg-gray-700/50 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-2">Фильтр {index + 1}</div>
                <div className="grid grid-cols-3 gap-2">
                  {/* Временной интервал */}
                  <div>
                    <Label className="text-xs text-gray-400">Интервал</Label>
                    <Select 
                      value={filter.interval} 
                      onValueChange={(value) => handleFilterChange(index, 'interval', value)}
                    >
                      <SelectTrigger className="bg-gray-600 border-gray-500 text-white text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-800 border-gray-600">
                        {availableIntervals.map((interval) => (
                          <SelectItem key={interval.value} value={interval.value} className="text-white">
                            {interval.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {/* Оператор */}
                  <div>
                    <Label className="text-xs text-gray-400">Оператор</Label>
                    <Select 
                      value={filter.operator} 
                      onValueChange={(value) => handleFilterChange(index, 'operator', value)}
                    >
                      <SelectTrigger className="bg-gray-600 border-gray-500 text-white text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-800 border-gray-600">
                        <SelectItem value=">" className="text-white">{">"}</SelectItem>
                        <SelectItem value=">=" className="text-white">{">="}</SelectItem>
                        <SelectItem value="<" className="text-white">{"<"}</SelectItem>
                        <SelectItem value="<=" className="text-white">{"<="}</SelectItem>
                        <SelectItem value="=" className="text-white">{"="}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {/* Значение % */}
                  <div>
                    <Label className="text-xs text-gray-400">Значение %</Label>
                    <Input
                      type="number"
                      step="0.1"
                      value={filter.value}
                      onChange={(e) => handleFilterChange(index, 'value', parseFloat(e.target.value) || 0)}
                      className="bg-gray-600 border-gray-500 text-white text-xs"
                      placeholder="0.0"
                    />
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {filter.interval !== 'none' ? 
                    `Показывать если изменение за ${availableIntervals.find(i => i.value === filter.interval)?.label} ${filter.operator} ${filter.value}%` 
                    : 'Фильтр отключен'
                  }
                </div>
              </div>
            ))}
          </div>

          {/* Сортировка */}
          <div className="space-y-2">
            <Label className="text-gray-300 text-sm font-medium">
              Сортировка
            </Label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <select
                  value={settings.sortBy}
                  onChange={(e) => onSettingsChange({
                    ...settings,
                    sortBy: e.target.value
                  })}
                  className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded-md px-2 py-1"
                >
                  <option value="symbol">Символ</option>
                  <option value="price">Цена</option>
                  <option value="change_15s">15 секунд</option>
                  <option value="change_30s">30 секунд</option>
                  <option value="changePercent24h">24ч %</option>
                  <option value="volume">Объем</option>
                </select>
              </div>
              <div>
                <select
                  value={settings.sortOrder}
                  onChange={(e) => onSettingsChange({
                    ...settings,
                    sortOrder: e.target.value
                  })}
                  className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded-md px-2 py-1"
                >
                  <option value="asc">↑ По возрастанию</option>
                  <option value="desc">↓ По убыванию</option>
                </select>
              </div>
            </div>
          </div>

          {/* Настройки таймфреймов графиков */}
          <div className="space-y-2">
            <Label className="text-gray-300 text-sm font-medium">
              📊 Таймфреймы графиков (выберите 1-3)
            </Label>
            <div className="grid grid-cols-2 gap-2">
              {availableTimeframes.map((tf) => (
                <div key={tf.value} className="flex items-center space-x-2">
                  <Checkbox
                    id={`tf-${tf.value}`}
                    checked={settings.chartTimeframes?.includes(tf.value) || false}
                    onCheckedChange={() => handleTimeframeToggle(tf.value)}
                    className="border-gray-600"
                  />
                  <label 
                    htmlFor={`tf-${tf.value}`}
                    className="text-sm text-gray-300 cursor-pointer flex items-center space-x-1"
                  >
                    <div 
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: tf.color }}
                    ></div>
                    <span>{tf.label}</span>
                  </label>
                </div>
              ))}
            </div>
            <div className="text-xs text-gray-500">
              Выбрано: {settings.chartTimeframes?.length || 0}/3 таймфрейма
            </div>
          </div>

          {/* Быстрые фильтры */}
          <div className="space-y-2">
            <Label className="text-gray-300 text-sm font-medium">
              Быстрые фильтры
            </Label>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant={settings.sortBy === 'change_15s' && settings.sortOrder === 'desc' ? 'default' : 'outline'}
                onClick={() => onSettingsChange({
                  ...settings,
                  sortBy: 'change_15s',
                  sortOrder: 'desc'
                })}
                className="text-xs"
              >
                ⚡ 15с рост
              </Button>
              <Button
                size="sm"
                variant={settings.sortBy === 'change_30s' && settings.sortOrder === 'desc' ? 'default' : 'outline'}
                onClick={() => onSettingsChange({
                  ...settings,
                  sortBy: 'change_30s',
                  sortOrder: 'desc'
                })}
                className="text-xs"
              >
                🔥 30с рост
              </Button>
              <Button
                size="sm"
                variant={settings.sortBy === 'changePercent24h' && settings.sortOrder === 'desc' ? 'default' : 'outline'}
                onClick={() => onSettingsChange({
                  ...settings,
                  sortBy: 'changePercent24h',
                  sortOrder: 'desc'
                })}
                className="text-xs"
              >
                🚀 Топ рост
              </Button>
              <Button
                size="sm"
                variant={settings.sortBy === 'changePercent24h' && settings.sortOrder === 'asc' ? 'destructive' : 'outline'}
                onClick={() => onSettingsChange({
                  ...settings,
                  sortBy: 'changePercent24h',
                  sortOrder: 'asc'
                })}
                className="text-xs"
              >
                📉 Топ падение
              </Button>
            </div>
          </div>

          {/* Кнопки действий */}
          <div className="space-y-2">
            <Button 
              onClick={() => onSettingsChange({
                ...settings,
                customFilters: [
                  { interval: 'none', operator: '>', value: 0 },
                  { interval: 'none', operator: '>', value: 0 },
                  { interval: 'none', operator: '>', value: 0 }
                ]
              })}
              variant="outline"
              size="sm"
              className="w-full text-gray-300 border-gray-600"
            >
              🔄 Сбросить фильтры
            </Button>
          </div>

          {/* Автообновление */}
          <div className="flex items-center justify-between bg-gray-700/50 rounded-lg p-2">
            <span className="text-gray-300 text-sm">Автообновление</span>
            <Badge variant="default" className="bg-green-600">
              Включено (3с)
            </Badge>
          </div>

          {/* Информация */}
          <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-700">
            MEXC TradingView Pro • Кастомные фильтры • История котировок • v3.1
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdvancedSettingsPanel;