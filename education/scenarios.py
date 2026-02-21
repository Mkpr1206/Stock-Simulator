import sys, os
sys.path.insert(0, r'C:\Users\PRANAV\Desktop\stocksim')

SCENARIOS = [
    {"id": 1, "title": "The Complete Beginner", "difficulty": "Beginner", "xp_reward": 100,
     "description": "Make your very first stock purchase.",
     "objectives": ["Search for a company you know", "Check its stock chart", "Buy at least 1 share using a market order", "Check your portfolio to confirm"],
     "completion_criteria": {"min_trades": 1}},
    {"id": 2, "title": "Build a Diversified Portfolio", "difficulty": "Beginner", "xp_reward": 200,
     "description": "Buy stocks from at least 4 different sectors.",
     "objectives": ["Pick stocks from Technology, Healthcare, Finance, and Consumer Goods", "No single stock over 30% of portfolio"],
     "completion_criteria": {"min_sectors": 4}},
    {"id": 3, "title": "Value Hunter", "difficulty": "Intermediate", "xp_reward": 250,
     "description": "Find and buy a stock that looks undervalued based on P/E ratio.",
     "objectives": ["Compare P/E ratios of 5 stocks", "Find one below its industry average", "Buy it and hold for 5 days"],
     "completion_criteria": {"hold_days": 5}},
    {"id": 4, "title": "Survive the Crash!", "difficulty": "Intermediate", "xp_reward": 300,
     "description": "A simulated market crash hits. Protect your portfolio.",
     "objectives": ["Review your portfolio", "Decide: sell, hold, or set stop-losses?", "Analyse the outcome after the event"],
     "completion_criteria": {"scenario_completed": True}},
    {"id": 5, "title": "Limit Order Master", "difficulty": "Intermediate", "xp_reward": 250,
     "description": "Trade exclusively using limit orders.",
     "objectives": ["Set a limit buy 5% below current price", "Set a stop-loss on an existing holding", "Check back in 3 days"],
     "completion_criteria": {"limit_orders_placed": 2}},
    {"id": 6, "title": "The Dividend Portfolio", "difficulty": "Advanced", "xp_reward": 350,
     "description": "Build a portfolio of dividend-paying stocks.",
     "objectives": ["Find 5 stocks with dividend yield above 2%", "Calculate expected annual dividends", "Hold for 2 weeks"],
     "starter_stocks": [{"ticker": "KO", "yield": "3.1%"}, {"ticker": "JNJ", "yield": "3.0%"}, {"ticker": "PG", "yield": "2.4%"}],
     "completion_criteria": {"dividend_stocks_held": 5}},
    {"id": 7, "title": "Earnings Season Challenge", "difficulty": "Advanced", "xp_reward": 400,
     "description": "Navigate earnings season — the most volatile period.",
     "objectives": ["Find 3 companies reporting earnings soon", "Decide: hold, buy, or avoid before each report", "Analyse whether your thesis was correct"],
     "completion_criteria": {"earnings_tracked": 3}},
    {"id": 8, "title": "Index Fund vs Stock Picker", "difficulty": "Advanced", "xp_reward": 500,
     "description": "Invest 50% in SPY (index) and 50% in your own stock picks. Compare after 30 days.",
     "objectives": ["Buy SPY with half your SimBucks", "Pick 5 individual stocks with the other half", "Compare returns after 30 days"],
     "famous_context": "Warren Buffett bet $1M that an S&P 500 index fund would beat hedge funds over 10 years. He won by a landslide.",
     "completion_criteria": {"comparison_period_days": 30}},
]


def get_scenario(scenario_id: int) -> dict:
    for s in SCENARIOS:
        if s["id"] == scenario_id:
            return s
    return None


def get_all_scenarios() -> list:
    return [{"id": s["id"], "title": s["title"], "difficulty": s["difficulty"],
             "description": s["description"], "xp_reward": s["xp_reward"]} for s in SCENARIOS]


def check_scenario_completion(scenario_id: int, user_id: int) -> dict:
    from data.db import get_db
    scenario = get_scenario(scenario_id)
    if not scenario:
        return {"error": "Scenario not found"}
    criteria = scenario.get("completion_criteria", {})
    results = {}
    with get_db() as conn:
        if "min_trades" in criteria:
            count = conn.execute("SELECT COUNT(*) as c FROM trades WHERE user_id=?", (user_id,)).fetchone()["c"]
            results["min_trades"] = {"required": criteria["min_trades"], "actual": count, "met": count >= criteria["min_trades"]}
        if "limit_orders_placed" in criteria:
            count = conn.execute("SELECT COUNT(*) as c FROM limit_orders WHERE user_id=?", (user_id,)).fetchone()["c"]
            results["limit_orders_placed"] = {"required": criteria["limit_orders_placed"], "actual": count, "met": count >= criteria["limit_orders_placed"]}
    all_met = all(v.get("met", True) for v in results.values())
    return {"scenario_id": scenario_id, "completed": all_met, "criteria": results,
            "xp_reward": scenario["xp_reward"] if all_met else 0}
