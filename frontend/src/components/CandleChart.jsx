import React from 'react';

const CandleChart = ({ candles = [], symbol = '', width = 200, height = 60 }) => {
  if (!candles || candles.length === 0) {
    return (
      <div 
        className="flex items-center justify-center bg-gray-800 rounded border border-gray-700"
        style={{ width, height }}
      >
        <span className="text-gray-500 text-xs">Нет данных</span>
      </div>
    );
  }

  // Подготавливаем данные
  const validCandles = candles.filter(candle => 
    candle.open > 0 && candle.high > 0 && candle.low > 0 && candle.close > 0
  );

  if (validCandles.length === 0) {
    return (
      <div 
        className="flex items-center justify-center bg-gray-800 rounded border border-gray-700"
        style={{ width, height }}
      >
        <span className="text-gray-500 text-xs">Загрузка...</span>
      </div>
    );
  }

  // Находим min и max значения для масштабирования
  const allPrices = validCandles.flatMap(candle => [candle.high, candle.low]);
  const minPrice = Math.min(...allPrices);
  const maxPrice = Math.max(...allPrices);
  const priceRange = maxPrice - minPrice;
  
  // Добавляем небольшой отступ
  const padding = priceRange * 0.1;
  const adjustedMin = minPrice - padding;
  const adjustedMax = maxPrice + padding;
  const adjustedRange = adjustedMax - adjustedMin;

  // Размеры области графика
  const chartPadding = 10;
  const chartWidth = width - chartPadding * 2;
  const chartHeight = height - chartPadding * 2;
  
  const candleWidth = Math.max(2, chartWidth / validCandles.length - 1);
  const candleSpacing = chartWidth / validCandles.length;

  // Функция для конвертации цены в Y координату
  const priceToY = (price) => {
    if (adjustedRange === 0) return chartHeight / 2 + chartPadding;
    return chartPadding + (adjustedMax - price) / adjustedRange * chartHeight;
  };

  return (
    <div className="relative bg-gray-800 rounded border border-gray-700 overflow-hidden">
      <svg width={width} height={height} className="block">
        {/* Grid lines */}
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#374151" strokeWidth="0.5" opacity="0.3"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        
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
          const bodyHeight = Math.max(Math.abs(closeY - openY), 1);
          
          return (
            <g key={index}>
              {/* Wick (фитиль) */}
              <line
                x1={x}
                y1={highY}
                x2={x}
                y2={lowY}
                stroke={color}
                strokeWidth="1"
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
                strokeWidth="1"
                opacity="0.9"
              />
            </g>
          );
        })}
        
        {/* Price labels */}
        <text
          x={width - 5}
          y={priceToY(maxPrice) + 12}
          fontSize="8"
          fill="#9ca3af"
          textAnchor="end"
          className="font-mono"
        >
          ${maxPrice.toFixed(4)}
        </text>
        <text
          x={width - 5}
          y={priceToY(minPrice) - 2}
          fontSize="8"
          fill="#9ca3af"
          textAnchor="end"
          className="font-mono"
        >
          ${minPrice.toFixed(4)}
        </text>
      </svg>
      
      {/* Symbol label */}
      <div className="absolute top-1 left-1 text-xs text-gray-400 font-medium">
        {symbol.replace('USDT', '')}
      </div>
      
      {/* Time label */}
      <div className="absolute bottom-1 right-1 text-xs text-gray-500">
        30с
      </div>
    </div>
  );
};

export default CandleChart;