"""
core/simulator.py
Market event simulator — randomly generates realistic news events that affect
stock prices. Used for educational scenarios like earnings surprises, crashes,
and sector rotations. All changes are simulated on top of real market data.
"""

import random
from datetime import datetime
from typing import List, Optional


# ── Market Event Templates ──────────────────────────────────────────────────────

POSITIVE_EVENTS = [
    {"headline": "{company} beats earnings estimates by {pct}%",        "impact": (0.03, 0.12)},
    {"headline": "{company} announces major share buyback program",      "impact": (0.02, 0.07)},
    {"headline": "{company} raises full-year revenue guidance",          "impact": (0.04, 0.10)},
    {"headline": "{company} announces partnership with top tech firm",   "impact": (0.05, 0.15)},
    {"headline": "{company} receives FDA approval for new product",      "impact": (0.08, 0.25)},
    {"headline": "Analyst upgrades {company} to 'Strong Buy'",          "impact": (0.02, 0.08)},
    {"headline": "{company} reports record quarterly revenue",           "impact": (0.03, 0.09)},
    {"headline": "{company} expands into new international markets",     "impact": (0.02, 0.06)},
]

NEGATIVE_EVENTS = [
    {"headline": "{company} misses earnings estimates, stock drops",     "impact": (-0.12, -0.03)},
    {"headline": "{company} CEO steps down amid controversy",            "impact": (-0.10, -0.04)},
    {"headline": "{company} faces regulatory investigation",             "impact": (-0.08, -0.03)},
    {"headline": "{company} issues profit warning for Q{q}",             "impact": (-0.15, -0.05)},
    {"headline": "Major data breach reported at {company}",              "impact": (-0.07, -0.03)},
    {"headline": "Analyst downgrades {company} to 'Underperform'",      "impact": (-0.06, -0.02)},
    {"headline": "{company} announces layoffs amid cost-cutting",        "impact": (-0.05, -0.02)},
    {"headline": "{company} loses key contract worth billions",          "impact": (-0.09, -0.03)},
]

MARKET_WIDE_EVENTS = [
    {"headline": "Federal Reserve raises interest rates by 25bps",       "impact": (-0.02, -0.01), "scope": "all"},
    {"headline": "Inflation data comes in hotter than expected",         "impact": (-0.03, -0.01), "scope": "all"},
    {"headline": "Strong jobs report boosts market sentiment",           "impact": (0.01, 0.03),   "scope": "all"},
    {"headline": "US GDP growth beats forecasts — economy expanding",   "impact": (0.01, 0.02),   "scope": "all"},
    {"headline": "Market-wide sell-off on geopolitical tensions",        "impact": (-0.04, -0.02), "scope": "all"},
    {"headline": "Tech sector rally as AI investment surges",            "impact": (0.02, 0.06),   "scope": "tech"},
    {"headline": "Oil prices spike — energy stocks surge",               "impact": (0.03, 0.08),   "scope": "energy"},
]

SECTOR_MAP = {
    "tech":   ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMD"],
    "energy": ["XOM", "CVX", "COP", "SLB"],
    "finance":["JPM", "BAC", "GS", "MS", "V", "MA"],
    "health": ["JNJ", "PFE", "UNH", "ABBV"],
}


class MarketEvent:
    """Represents a simulated market news event."""

    def __init__(self, headline: str, ticker: str, impact_pct: float,
                 scope: str = "single", event_type: str = "neutral"):
        self.headline    = headline
        self.ticker      = ticker
        self.impact_pct  = impact_pct
        self.scope       = scope
        self.event_type  = event_type
        self.timestamp   = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "headline":   self.headline,
            "ticker":     self.ticker,
            "impact_pct": round(self.impact_pct * 100, 2),
            "scope":      self.scope,
            "type":       self.event_type,
            "timestamp":  self.timestamp,
            "summary":    self._educational_summary(),
        }

    def _educational_summary(self) -> str:
        """Explains WHY this event affects the stock price."""
        if self.impact_pct > 0.05:
            return (f"Strong positive news typically drives buying demand, pushing prices up. "
                    f"A {self.impact_pct*100:.1f}% move on this news is significant.")
        elif self.impact_pct > 0:
            return (f"Positive news can boost investor confidence. "
                    f"A modest {self.impact_pct*100:.1f}% gain reflects cautious optimism.")
        elif self.impact_pct < -0.05:
            return (f"Serious negative news often triggers selling. "
                    f"A {abs(self.impact_pct)*100:.1f}% drop signals strong investor concern.")
        else:
            return (f"Minor negative news caused a small {abs(self.impact_pct)*100:.1f}% dip — "
                    f"markets are reacting, but not panicking.")


class MarketSimulator:
    """
    Generates random but realistic market events for educational scenarios.
    Does NOT modify real market data — purely for learning simulations.
    """

    def generate_random_event(self, ticker: str, company_name: str = None) -> MarketEvent:
        """Generate a random positive or negative event for a ticker."""
        company = company_name or ticker
        is_positive = random.random() > 0.45  # Slight positive bias (markets trend up long term)

        if is_positive:
            template = random.choice(POSITIVE_EVENTS)
            impact = random.uniform(*template["impact"])
            event_type = "positive"
        else:
            template = random.choice(NEGATIVE_EVENTS)
            impact = random.uniform(*template["impact"])
            event_type = "negative"

        headline = template["headline"].format(
            company=company,
            pct=random.randint(5, 25),
            q=random.choice([1, 2, 3, 4])
        )

        return MarketEvent(headline, ticker, impact, "single", event_type)

    def generate_market_event(self) -> MarketEvent:
        """Generate a broad market or sector event."""
        event = random.choice(MARKET_WIDE_EVENTS)
        scope = event.get("scope", "all")
        impact = random.uniform(*event["impact"])

        # Pick a representative ticker for the scope
        if scope in SECTOR_MAP:
            ticker = random.choice(SECTOR_MAP[scope])
        else:
            ticker = "SPY"

        return MarketEvent(event["headline"], ticker, impact, scope, "market")

    def simulate_crash(self) -> List[MarketEvent]:
        """Simulate a market crash scenario — great for education."""
        events = []
        crash_magnitude = random.uniform(-0.15, -0.35)

        events.append(MarketEvent(
            "MARKET CRASH: Global recession fears trigger mass sell-off",
            "SPY", crash_magnitude, "all", "crash"
        ))

        for sector, tickers in SECTOR_MAP.items():
            for ticker in tickers[:2]:
                sector_impact = crash_magnitude * random.uniform(0.8, 1.5)
                events.append(MarketEvent(
                    f"{ticker} falls amid broad market panic",
                    ticker, sector_impact, "single", "crash"
                ))

        return events

    def simulate_bull_run(self) -> List[MarketEvent]:
        """Simulate a sustained bull market — teaches the other side."""
        events = []
        events.append(MarketEvent(
            "BULL MARKET: Economic optimism drives stocks to record highs",
            "SPY", random.uniform(0.05, 0.15), "all", "bull"
        ))
        return events

    def get_market_sentiment(self) -> dict:
        """Returns a simulated market sentiment score."""
        score = random.gauss(0.5, 0.15)
        score = max(0.0, min(1.0, score))

        if score > 0.7:
            label = "Greed"
            color = "green"
            description = "Investors are optimistic. Be cautious of overvaluation."
        elif score > 0.55:
            label = "Neutral"
            color = "yellow"
            description = "Markets are balanced. Good time to review your portfolio."
        elif score > 0.35:
            label = "Fear"
            color = "orange"
            description = "Investors are nervous. Could be opportunity for long-term buyers."
        else:
            label = "Extreme Fear"
            color = "red"
            description = "Market panic. Historically, this can be a great buying opportunity."

        return {
            "score":       round(score * 100),
            "label":       label,
            "color":       color,
            "description": description,
            "education":   (
                "The Fear & Greed Index measures market sentiment. "
                "Warren Buffett's famous rule: 'Be fearful when others are greedy, "
                "and greedy when others are fearful.'"
            ),
        }

    def get_daily_briefing(self, tickers: List[str]) -> dict:
        """Generate a simulated daily market briefing for the user's holdings."""
        events = [self.generate_random_event(t) for t in random.sample(tickers, min(3, len(tickers)))]
        market_event = self.generate_market_event()
        sentiment = self.get_market_sentiment()

        return {
            "date":          datetime.utcnow().strftime("%A, %B %d %Y"),
            "sentiment":     sentiment,
            "market_event":  market_event.to_dict(),
            "stock_events":  [e.to_dict() for e in events],
            "tip_of_the_day": random.choice(DAILY_TIPS),
        }


DAILY_TIPS = [
    "💡 Diversification: Spreading investments across many stocks reduces risk if one company performs badly.",
    "💡 Dollar-cost averaging: Investing a fixed amount regularly beats trying to 'time the market'.",
    "💡 P/E Ratio: A stock's price-to-earnings ratio compares its price to its profits. Lower can mean better value.",
    "💡 Compound interest: Reinvesting your gains over time can dramatically multiply your portfolio value.",
    "💡 Market crashes are normal: The S&P 500 has recovered from every crash in its history.",
    "💡 Emotions are your enemy: Panic selling during dips and FOMO buying at peaks cost investors millions.",
    "💡 The long game: Most successful investors hold for years, not days.",
    "💡 Research before buying: Understand what a company actually does before investing in it.",
    "💡 Cash is a position: Holding cash lets you buy when others are panic-selling.",
    "💡 Never invest money you can't afford to lose — even the best investors have losing years.",
]
