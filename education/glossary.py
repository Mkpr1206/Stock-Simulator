GLOSSARY = {
    "stock": {"definition": "A share of ownership in a company.", "related": ["share", "equity", "dividend"]},
    "share": {"definition": "A single unit of ownership in a company. Same as a stock.", "related": ["stock"]},
    "dividend": {"definition": "A payment companies make to shareholders from their profits, usually quarterly.", "related": ["yield", "stock"]},
    "bull market": {"definition": "A market that has risen 20%+ from its recent low. Associated with economic optimism.", "related": ["bear market"]},
    "bear market": {"definition": "A market that has declined 20%+ from its recent high. Associated with economic pessimism.", "related": ["bull market", "correction"]},
    "correction": {"definition": "A decline of 10-20% from a recent peak. More minor than a bear market.", "related": ["bear market"]},
    "p/e ratio": {"definition": "Price-to-Earnings ratio. Stock price divided by earnings per share. Measures how much investors pay per $1 of profit.", "related": ["eps", "valuation"]},
    "eps": {"definition": "Earnings Per Share. Company's net profit divided by total shares outstanding.", "related": ["p/e ratio", "earnings report"]},
    "etf": {"definition": "Exchange-Traded Fund. A basket of many stocks that trades like a single stock.", "example": "SPY tracks the S&P 500 with 500 companies in one fund.", "related": ["diversification", "index"]},
    "diversification": {"definition": "Spreading investments across many assets to reduce risk.", "related": ["portfolio", "etf"]},
    "market cap": {"definition": "Total market value of a company. Stock price × total shares outstanding.", "related": ["large cap", "small cap"]},
    "market order": {"definition": "An order to buy/sell immediately at the current market price.", "related": ["limit order", "stop-loss"]},
    "limit order": {"definition": "An order to buy/sell only at a specific price or better.", "related": ["market order", "stop-loss"]},
    "stop-loss": {"definition": "An order to automatically sell if price drops to a set level. Protects against large losses.", "related": ["limit order"]},
    "volatility": {"definition": "How much a stock's price fluctuates. High volatility = large price swings.", "related": ["beta", "risk"]},
    "beta": {"definition": "Measures how much a stock moves relative to the overall market. Beta of 1 = moves with market.", "related": ["volatility", "risk"]},
    "rsi": {"definition": "Relative Strength Index. A 0-100 indicator. Above 70 = overbought, below 30 = oversold.", "related": ["technical analysis"]},
    "moving average": {"definition": "Average stock price over a set number of days. 50-day and 200-day MAs identify trends.", "related": ["technical analysis"]},
    "ipo": {"definition": "Initial Public Offering. When a private company sells shares to the public for the first time.", "related": ["stock exchange"]},
    "s&p 500": {"definition": "An index tracking the 500 largest US publicly traded companies.", "related": ["index", "etf"]},
    "nasdaq": {"definition": "A US stock exchange focused on technology companies.", "related": ["nyse"]},
    "nyse": {"definition": "New York Stock Exchange — the world's largest stock exchange by market cap.", "related": ["nasdaq"]},
    "earnings report": {"definition": "Quarterly report where a public company discloses revenue, profit, and future guidance.", "related": ["eps", "guidance"]},
    "guidance": {"definition": "Forward-looking statements from company management about expected future performance.", "related": ["earnings report"]},
    "compound interest": {"definition": "Earning returns on your returns. Money grows exponentially over time.", "related": ["return"]},
    "portfolio": {"definition": "Your complete collection of investments — all stocks, bonds, and cash you own.", "related": ["diversification"]},
    "yield": {"definition": "Income from an investment as a percentage of its price. Dividend yield = annual dividend / stock price.", "related": ["dividend"]},
    "recession": {"definition": "Economic decline. Typically two consecutive quarters of negative GDP growth.", "related": ["bear market"]},
    "bid price": {"definition": "The highest price a buyer is willing to pay for a stock.", "related": ["ask price", "spread"]},
    "ask price": {"definition": "The lowest price a seller is willing to accept.", "related": ["bid price", "spread"]},
    "spread": {"definition": "The difference between ask and bid price. Represents the cost of trading.", "related": ["bid price", "ask price"]},
    "blue chip": {"definition": "Shares in large, well-established, financially stable companies.", "example": "Apple, Microsoft, Coca-Cola are blue-chip stocks."},
    "short selling": {"definition": "Borrowing shares and selling them, hoping to buy back cheaper to profit from a price drop. Very risky.", "related": ["long position"]},
    "dollar-cost averaging": {"definition": "Investing a fixed amount regularly regardless of market conditions. Reduces timing risk.", "related": ["timing the market"]},
    "fundamental analysis": {"definition": "Evaluating a stock by studying the company's financials, industry, and economy.", "related": ["p/e ratio", "eps"]},
    "technical analysis": {"definition": "Analyzing price charts and patterns to predict future price movements.", "related": ["moving average", "rsi"]},
    "volume": {"definition": "Number of shares traded in a given period. High volume confirms price moves.", "related": ["liquidity"]},
    "liquidity": {"definition": "How easily an asset can be bought or sold without affecting its price.", "related": ["volume"]},
    "capital gain": {"definition": "Profit from selling an asset for more than you paid.", "related": ["capital loss"]},
    "capital loss": {"definition": "Loss from selling an asset for less than you paid.", "related": ["capital gain"]},
}


def get_term(term: str) -> dict:
    key = term.lower().strip()
    result = GLOSSARY.get(key)
    if result:
        return {"term": key, **result}
    matches = [k for k in GLOSSARY if key in k or k in key]
    if matches:
        return {"term": matches[0], **GLOSSARY[matches[0]], "note": f"Closest match for '{term}'"}
    return {"error": f"Term '{term}' not found in glossary"}


def search_glossary(query: str) -> list:
    query = query.lower()
    return [{"term": k, "definition": v["definition"]}
            for k, v in GLOSSARY.items()
            if query in k or query in v["definition"].lower()]


def get_all_terms() -> list:
    return sorted([{"term": k, "definition": v["definition"]} for k, v in GLOSSARY.items()], key=lambda x: x["term"])
