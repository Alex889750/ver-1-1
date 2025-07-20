# Список всех поддерживаемых тикеров
SUPPORTED_TICKERS_RAW = [
    "ETH", "BTC", "SOL", "DOGE", "XRP", "XTZ", "PEPE", "LTC", "ENA", "SUI",
    "PENGU", "PUMP", "ADA", "C", "FARTCOIN", "BONK", "ETC", "BNB", "AVAX", "LINK",
    "EPIC", "WIF", "ERA", "TRUMP", "UNI", "CROSS", "XLM", "AAVE", "CRV", "BCH",
    "CFX", "SHIB", "SUSHI", "FLOKI", "HBAR", "FXS", "PUMPFUN", "ARB", "ELX", "TRX",
    "WLD", "DOT", "FIL", "OP", "LDO", "HYPE", "NEAR", "TIA", "DIA", "APT",
    "NEIRO", "ARK", "ONDO", "PNUT", "MEW", "VIRTUAL", "SEI", "THE", "TAO", "SPX",
    "MASK", "ETHFI", "ACX", "BANANAS", "FET", "GALA", "HEI", "INJ", "HAEDAL", "ALGO",
    "BB", "MOODENG", "IMX", "FUN", "MKR", "BOME", "KNC", "ATOM", "HYPER", "POPCAT",
    "TAC", "ENS", "ORDI", "SAHARA", "EIGEN", "TURBO", "M", "ICP", "TON", "S",
    "DYM", "AIXBT", "PHB", "MYX", "H", "SPK", "VELVET", "BSV", "MAGIC", "BID",
    "PENDLE", "SAND", "LOKA", "TRB", "GAS", "OM", "PEOPLE", "DYDX", "HOT", "BOB",
    "NEO", "ACH", "COMP", "RENDER", "GOAT", "SYRUP", "VET", "USUAL", "RSR", "A",
    "CHESS", "MOVE", "ARKM", "POL", "BANK", "GRIFFAIN", "JUP", "INIT", "XEC", "JTO",
    "LA", "ZRO", "WCT", "STRK", "CVX", "CAKE", "AERGO", "APE", "TANSSI", "MANA",
    "ORDER", "KDA", "SATS", "STX", "ALT", "SKYAI", "BERA", "KAITO", "THETA", "PYTH",
    "COOKIE", "MOG", "NEIROCTO", "DEXE", "W", "LPT", "GRT", "CHILLGUY", "MANTA", "AR",
    "OMNI", "IP", "AVAAI", "ACE", "AIN", "MELANIA", "RUNE", "FLOW", "NXPC", "SXP",
    "VINE", "MUBARAK", "ARC", "SSV", "AXS", "1INCH", "BRETT", "IOTA", "SAGA", "SNX",
    "XVG", "RESOLV", "CELO", "IOST", "ZRX", "MEME", "KAIA", "RVN", "SWARMS", "NEIROETH",
    "NOT", "USTC", "LAUNCHCOIN", "REZ", "AIOT", "GMT", "BTCDOM", "IO", "XAI", "ZEN",
    "UMA", "ROSE", "HMSTR", "DOGS", "KAS", "AERO", "XMR", "ZK", "GTC", "HFT",
    "RPL", "LQTY", "NEWT", "GRASS", "DEGO", "BABYDOGE", "ALU", "BULLA", "MINA", "XDC", "NMR"
]

# Преобразуем в формат USDT пар
SUPPORTED_TICKERS = []

for ticker in SUPPORTED_TICKERS_RAW:
    # Обрабатываем специальные случаи
    if ticker == "BANANAS31":
        SUPPORTED_TICKERS.append("BANANASUSDT")
    elif ticker == "KAITO":  # Может быть недоступен на MEXC
        continue  # Пропускаем пока
    elif ticker in ["GRIFFAIN", "SKYAI", "AVAAI", "MELANIA"]:  # Новые токены, могут быть недоступны
        continue
    elif ticker == "BTCDOM":  # Это индекс, не торговая пара
        continue
    elif len(ticker) == 1:  # Однобуквенные тикеры могут вызвать проблемы
        continue
    else:
        SUPPORTED_TICKERS.append(f"{ticker}USDT")

# Финальный список для использования
print(f"Total tickers configured: {len(SUPPORTED_TICKERS)}")

# Группы тикеров для batch обработки
BATCH_SIZE = 50  # Максимум тикеров в одном batch запросе