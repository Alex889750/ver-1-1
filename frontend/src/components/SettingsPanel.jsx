import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Checkbox } from './ui/checkbox';

const SettingsPanel = ({ 
  settings, 
  onSettingsChange, 
  isOpen, 
  onToggle,
  totalTickers = 0,
  activeTickers = 0,
  availableTimeframes = [],
  availableTableIntervals = []  // Add this new prop
}) => {
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
      // Убираем таймфрейм, но не менее 1
      newTimeframes = currentTimeframes.filter(tf => tf !== timeframe);
      if (newTimeframes.length === 0) {
        newTimeframes = [timeframe]; // Оставляем хотя бы один
      }
    } else {
      // Добавляем таймфрейм, но не более 3
      if (currentTimeframes.length < 3) {
        newTimeframes = [...currentTimeframes, timeframe];
      } else {
        // Заменяем последний
        newTimeframes = [...currentTimeframes.slice(0, 2), timeframe];
      }
    }
    
    onSettingsChange({
      ...settings,
      chartTimeframes: newTimeframes
    });
  };

  const handleTableIntervalChange = (columnIndex, newInterval) => {
    const newIntervals = [...settings.tableIntervals];
    newIntervals[columnIndex] = newInterval;
    onSettingsChange({
      ...settings,
      tableIntervals: newIntervals
    });
  };

  const handleSignalThresholdChange = (e) => {
    const value = Math.max(0.01, Math.min(30, parseFloat(e.target.value) || 1.01));
    onSettingsChange({
      ...settings,
      signalThreshold: value
    });
  };

  const handleSignalCandlesCountChange = (e) => {
    const value = Math.max(3, Math.min(100, parseInt(e.target.value) || 10));
    onSettingsChange({
      ...settings,
      signalCandlesCount: value
    });
  };

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
            <CardTitle className="text-white text-lg">⚙️ TradingView Настройки</CardTitle>
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

          {/* Настраиваемые интервалы для колонок таблицы */}
          <div className="space-y-2">
            <Label className="text-gray-300 text-sm font-medium">
              🔧 Интервалы для колонок таблицы
            </Label>
            <div className="space-y-2">
              {settings.tableIntervals?.map((interval, index) => (
                <div key={`interval-${index}`} className="flex items-center space-x-2">
                  <span className="text-gray-400 text-xs w-12">
                    Кол. {index + 1}:
                  </span>
                  <select
                    value={interval}
                    onChange={(e) => handleTableIntervalChange(index, e.target.value)}
                    className="flex-1 bg-gray-700 border border-gray-600 text-white text-xs rounded-md px-2 py-1"
                  >
                    {availableTableIntervals.map((intervalOption) => (
                      <option key={intervalOption.value} value={intervalOption.value}>
                        {intervalOption.label}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
            <div className="text-xs text-gray-500">
              Настроенные интервалы: {settings.tableIntervals?.join(', ') || 'Не настроено'}
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
              <Button
                size="sm"
                variant={settings.sortBy === 'volume' && settings.sortOrder === 'desc' ? 'default' : 'outline'}
                onClick={() => onSettingsChange({
                  ...settings,
                  sortBy: 'volume',
                  sortOrder: 'desc'
                })}
                className="text-xs"
              >
                📊 Объем
              </Button>
            </div>
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
            TradingView Pro • MEXC API • 8 таймфреймов • v3.0
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SettingsPanel;