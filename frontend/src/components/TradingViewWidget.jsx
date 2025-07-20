import React, { useEffect, useRef } from 'react';

const TradingViewWidget = ({ symbol, width = '100%', height = '400px', interval = '1', theme = 'dark' }) => {
  const containerRef = useRef();

  useEffect(() => {
    if (containerRef.current) {
      // Очищаем контейнер перед созданием нового виджета
      containerRef.current.innerHTML = '';

      // Создаем контейнер для виджета
      const widgetContainer = document.createElement('div');
      widgetContainer.className = 'tradingview-widget-container';
      widgetContainer.style.height = height;
      widgetContainer.style.width = width;

      const widgetDiv = document.createElement('div');
      widgetDiv.className = 'tradingview-widget-container__widget';
      widgetDiv.style.height = 'calc(100% - 32px)';
      widgetDiv.style.width = '100%';

      const copyrightDiv = document.createElement('div');
      copyrightDiv.className = 'tradingview-widget-copyright';
      copyrightDiv.innerHTML = '<a href="https://ru.tradingview.com/" rel="noopener nofollow" target="_blank"><span class="blue-text">Все рынки на TradingView</span></a>';

      widgetContainer.appendChild(widgetDiv);
      widgetContainer.appendChild(copyrightDiv);
      containerRef.current.appendChild(widgetContainer);

      // Создаем и загружаем скрипт
      const script = document.createElement('script');
      script.type = 'text/javascript';
      script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
      script.async = true;

      // Конфигурация виджета
      const config = {
        allow_symbol_change: false, // Отключаем изменение символа
        calendar: false,
        details: false,
        hide_side_toolbar: true,
        hide_top_toolbar: true,
        hide_legend: false,
        hide_volume: false,
        hotlist: false,
        interval: interval,
        locale: 'ru',
        save_image: false,
        style: '1',
        symbol: symbol,
        theme: theme,
        timezone: 'Europe/Moscow',
        backgroundColor: '#0F0F0F',
        gridColor: 'rgba(242, 242, 242, 0.06)',
        watchlist: [],
        withdateranges: false,
        compareSymbols: [],
        studies: [],
        autosize: true
      };

      script.innerHTML = JSON.stringify(config);
      widgetContainer.appendChild(script);
    }
  }, [symbol, width, height, interval, theme]);

  return <div ref={containerRef} className="tradingview-chart-container" />;
};

export default TradingViewWidget;