// Mock данные для криптовалютных тикеров
const basePrices = {
  LTCUSDT: 85.42,
  SHIBUSDT: 0.00002156,
  AVAXUSDT: 28.91,
  LINKUSDT: 12.84,
  BCHUSDT: 341.28,
  ATOMUSDT: 6.73,
  XMRUSDT: 152.89,
  APTUSDT: 9.15,
  FILUSDT: 4.26,
  NEARUSDT: 3.87
};

// Функция для генерации случайных изменений цен
const generatePriceVariation = (basePrice) => {
  // Случайное изменение от -2% до +2%
  const variation = (Math.random() - 0.5) * 0.04;
  return basePrice * (1 + variation);
};

// Функция для генерации случайных изменений за 24 часа
const generate24hChange = (currentPrice) => {
  const changePercent = (Math.random() - 0.5) * 20; // от -10% до +10%
  const change24h = currentPrice * (changePercent / 100);
  return {
    change24h,
    changePercent24h: changePercent
  };
};

export const getMockPriceData = () => {
  const data = {};
  
  Object.keys(basePrices).forEach(ticker => {
    const basePrice = basePrices[ticker];
    const currentPrice = generatePriceVariation(basePrice);
    const { change24h, changePercent24h } = generate24hChange(currentPrice);
    
    data[ticker] = {
      symbol: ticker,
      price: currentPrice,
      change24h,
      changePercent24h,
      timestamp: Date.now()
    };
    
    // Обновляем базовую цену для следующего обновления
    basePrices[ticker] = currentPrice;
  });
  
  return data;
};