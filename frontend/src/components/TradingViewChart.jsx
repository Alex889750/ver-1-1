import React, { useMemo } from 'react';

const TradingViewChart = ({ candles = [], symbol = '', timeframe = '30s', width = 300, height = 120 }) => {
  const chartData = useMemo(() => {
    if (!candles || candles.length === 0) return null;

    // Фильтруем свечи по таймфрейму для дополнительной уверенности
    const timeframeCandles = candles.filter(candle => 
      candle.timeframe === timeframe
    );

    const validCandles = timeframeCandles.filter(candle => 
      candle.open > 0 && candle.high > 0 && candle.low > 0 && candle.close > 0
    );

    if (validCandles.length === 0) return null;

    // Логирование для отладки
    console.log(`Chart ${symbol} ${timeframe}: ${validCandles.length} candles`, validCandles.slice(-3));

    // Находим min и max значения для масштабирования
    const allPrices = validCandles.flatMap(candle => [candle.high, candle.low]);
    const minPrice = Math.min(...allPrices);
    const maxPrice = Math.max(...allPrices);
    const priceRange = maxPrice - minPrice;
    
    // Добавляем небольшой отступ
    const padding = priceRange * 0.05;
    const adjustedMin = minPrice - padding;
    const adjustedMax = maxPrice + padding;
    const adjustedRange = adjustedMax - adjustedMin;

    return {
      candles: validCandles,
      minPrice,
      maxPrice,
      adjustedMin,
      adjustedMax,
      adjustedRange
    };
  }, [candles, timeframe, symbol]);

  if (!chartData) {
    return (
      <div 
        className="flex items-center justify-center bg-gray-900/80 rounded border border-gray-600"
        style={{ width, height }}
      >
        <span className="text-gray-500 text-xs">Нет данных</span>
      </div>
    );
  }

  const { candles: validCandles, adjustedMin, adjustedMax, adjustedRange } = chartData;

  // Размеры области графика
  const chartPadding = 8;
  const chartWidth = width - chartPadding * 2;
  const chartHeight = height - chartPadding * 2 - 25; // Место для информации снизу
  
  const candleWidth = Math.max(1.5, chartWidth / validCandles.length - 0.5);
  const candleSpacing = chartWidth / validCandles.length;

  // Функция для конвертации цены в Y координату
  const priceToY = (price) => {
    if (adjustedRange === 0) return chartHeight / 2 + chartPadding;
    return chartPadding + (adjustedMax - price) / adjustedRange * chartHeight;
  };

  // Рассчитываем статистику
  const firstPrice = validCandles[0]?.open || 0;
  const lastPrice = validCandles[validCandles.length - 1]?.close || 0;
  const priceChange = lastPrice - firstPrice;
  const priceChangePercent = firstPrice > 0 ? (priceChange / firstPrice) * 100 : 0;

  const getTimeframeColor = () => {
    switch (timeframe) {
      case '15s': return '#3b82f6'; // blue-500
      case '30s': return '#10b981'; // green-500  
      case '1m': return '#f59e0b';  // amber-500
      case '5m': return '#8b5cf6';  // violet-500
      case '15m': return '#ec4899'; // pink-500
      case '1h': return '#ef4444';  // red-500
      case '4h': return '#06b6d4';  // cyan-500
      case '1d': return '#84cc16';  // lime-500
      default: return '#6b7280';    // gray-500
    }
  };

  const themeColor = getTimeframeColor();

  return (
    <div className="relative bg-gray-900/90 rounded border border-gray-600 overflow-hidden backdrop-blur-sm">
      <svg width={width} height={height} className="block">
        {/* Background pattern */}
        <defs>
          <pattern id={`grid-${symbol}-${timeframe}`} width="15" height="15" patternUnits="userSpaceOnUse">
            <path d="M 15 0 L 0 0 0 15" fill="none" stroke="#374151" strokeWidth="0.3" opacity="0.4"/>
          </pattern>
          <linearGradient id={`gradient-${symbol}-${timeframe}`} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={themeColor} stopOpacity="0.2"/>
            <stop offset="100%" stopColor={themeColor} stopOpacity="0.05"/>
          </linearGradient>
        </defs>
        <rect width="100%" height="100%" fill={`url(#gradient-${symbol}-${timeframe})`} />
        <rect width="100%" height="100%" fill={`url(#grid-${symbol}-${timeframe})`} />
        
        {/* Price line (connecting close prices) */}
        <path
          d={validCandles.map((candle, index) => {
            const x = chartPadding + index * candleSpacing + candleSpacing / 2;
            const y = priceToY(candle.close);
            return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
          }).join(' ')}
          stroke={themeColor}
          strokeWidth="1.5"
          fill="none"
          opacity="0.7"
        />
        
        {/* Candles */}
        {validCandles.map((candle, index) => {
          const x = chartPadding + index * candleSpacing + candleSpacing / 2;
          const openY = priceToY(candle.open);
          const closeY = priceToY(candle.close);
          const highY = priceToY(candle.high);
          const lowY = priceToY(candle.low);
          
          const isGreen = candle.close >= candle.open;
          const color = isGreen ? '#10b981' : '#ef4444'; // green-500 : red-500
          const fillColor = isGreen ? color : 'transparent';
          
          // Тело свечи
          const bodyTop = Math.min(openY, closeY);
          const bodyHeight = Math.max(Math.abs(closeY - openY), 0.8);
          
          return (
            <g key={index}>
              {/* Wick (фитиль) */}
              <line
                x1={x}
                y1={highY}
                x2={x}
                y2={lowY}
                stroke={color}
                strokeWidth="0.8"
                opacity="0.8"
              />
              
              {/* Body (тело свечи) */}
              <rect
                x={x - candleWidth / 2}
                y={bodyTop}
                width={candleWidth}
                height={bodyHeight}
                fill={fillColor}
                stroke={color}
                strokeWidth="0.8"
                opacity="0.9"
              />
            </g>
          );
        })}
        
        {/* Price labels */}
        <text
          x={width - 5}
          y={priceToY(chartData.maxPrice) + 10}
          fontSize="8"
          fill="#9ca3af"
          textAnchor="end"
          className="font-mono"
        >
          ${chartData.maxPrice.toFixed(6)}
        </text>
        <text
          x={width - 5}
          y={priceToY(chartData.minPrice) - 2}
          fontSize="8"
          fill="#9ca3af"
          textAnchor="end"
          className="font-mono"
        >
          ${chartData.minPrice.toFixed(6)}
        </text>
      </svg>
      
      {/* Header info */}
      <div className="absolute top-1 left-2 flex items-center space-x-2">
        <div 
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: themeColor }}
        ></div>
        <span className="text-xs text-white font-semibold">
          {symbol.replace('USDT', '')}
        </span>
        <span 
          className="text-xs font-bold px-1.5 py-0.5 rounded"
          style={{ 
            backgroundColor: themeColor + '20', 
            color: themeColor,
            border: `1px solid ${themeColor}40`
          }}
        >
          {timeframe.toUpperCase()}
        </span>
      </div>
      
      {/* Bottom info */}
      <div className="absolute bottom-1 left-2 right-2 flex justify-between items-center">
        <div className="text-xs text-gray-400">
          {validCandles.length} свечей
        </div>
        <div className={`text-xs font-mono font-bold ${priceChangePercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {priceChangePercent >= 0 ? '+' : ''}{priceChangePercent.toFixed(2)}%
        </div>
      </div>
    </div>
  );
};

export default TradingViewChart;