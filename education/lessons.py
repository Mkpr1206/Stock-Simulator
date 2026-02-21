import sys, os
sys.path.insert(0, r'C:\Users\PRANAV\Desktop\stocksim')

from config import QUIZ_PASS_SCORE

LESSONS = [
    {
        "id": 1, "title": "What is a Stock?", "difficulty": "Beginner",
        "estimated_minutes": 5, "xp_reward": 50,
        "content": "A stock represents ownership in a company. When you buy a stock, you become a part-owner (shareholder). If the company grows, your shares increase in value. You can also earn dividends — regular profit payouts.",
        "quiz": [
            {"question": "What does buying a stock mean?",
             "options": ["You lend money to a company", "You become a part-owner of a company", "You get a guaranteed return", "You work for the company"],
             "answer": 1, "explanation": "Buying stock makes you a shareholder — a partial owner."},
            {"question": "Which is a way to make money from stocks?",
             "options": ["Company pays you a salary", "Only dividends", "Price appreciation and/or dividends", "Stocks always go up"],
             "answer": 2, "explanation": "You profit through price rising OR dividends — or both!"},
        ]
    },
    {
        "id": 2, "title": "How the Stock Market Works", "difficulty": "Beginner",
        "estimated_minutes": 7, "xp_reward": 60,
        "content": "The stock market is a giant auction matching buyers and sellers. US markets (NYSE, NASDAQ) are open Monday-Friday 9:30AM-4:00PM ET. Prices are driven by supply and demand — more buyers means price goes up, more sellers means price goes down.",
        "quiz": [
            {"question": "What determines a stock's price?",
             "options": ["The government sets prices", "Supply and demand from buyers and sellers", "The CEO decides", "It's fixed at IPO"],
             "answer": 1, "explanation": "Stock prices are driven by supply and demand."},
        ]
    },
    {
        "id": 3, "title": "Market Orders vs Limit Orders", "difficulty": "Beginner",
        "estimated_minutes": 8, "xp_reward": 70,
        "content": "A MARKET ORDER buys/sells immediately at the current price. A LIMIT ORDER only executes at your specified price or better. A STOP-LOSS automatically sells if price drops to a set level — your safety net.",
        "quiz": [
            {"question": "Which order executes immediately at current price?",
             "options": ["Limit order", "Stop-loss", "Market order", "Pending order"],
             "answer": 2, "explanation": "A market order executes immediately at the best available price."},
            {"question": "You want to buy only if TSLA drops to $200. Which order?",
             "options": ["Market order", "Limit buy order", "Stop-loss", "Sell order"],
             "answer": 1, "explanation": "A limit buy order lets you set the maximum price you'll pay."},
        ]
    },
    {
        "id": 4, "title": "Understanding the P/E Ratio", "difficulty": "Intermediate",
        "estimated_minutes": 10, "xp_reward": 80,
        "content": "P/E Ratio = Stock Price / Earnings Per Share. It tells you how much investors pay per $1 of profit. A P/E of 20 means investors pay $20 for every $1 of annual earnings. Low P/E may mean undervalued; high P/E means high growth expectations.",
        "quiz": [
            {"question": "Stock is $100, EPS is $5. What is the P/E ratio?",
             "options": ["5", "10", "20", "500"],
             "answer": 2, "explanation": "P/E = Price / EPS = $100 / $5 = 20."},
        ]
    },
    {
        "id": 5, "title": "Diversification", "difficulty": "Beginner",
        "estimated_minutes": 8, "xp_reward": 70,
        "content": "Don't put all your eggs in one basket. Spread investments across multiple companies and sectors. If one stock crashes, others protect your portfolio. An ETF like SPY gives you 500 companies in one purchase.",
        "quiz": [
            {"question": "Why is diversification important?",
             "options": ["It guarantees profits", "It eliminates all risk", "It reduces the impact of any single bad investment", "It lets you trade more"],
             "answer": 2, "explanation": "Diversification means one bad investment won't ruin your portfolio."},
        ]
    },
    {
        "id": 6, "title": "Reading a Stock Chart", "difficulty": "Intermediate",
        "estimated_minutes": 12, "xp_reward": 90,
        "content": "Candlestick charts show Open/High/Low/Close for each period. Green candle = price rose. Red candle = price fell. Volume bars show how many shares traded. Moving averages (50-day, 200-day) show trends.",
        "quiz": [
            {"question": "What does a green candlestick indicate?",
             "options": ["Price fell that day", "Price rose that day", "No trading occurred", "All-time high"],
             "answer": 1, "explanation": "Green means closing price was higher than opening price."},
        ]
    },
    {
        "id": 7, "title": "Bull Markets and Bear Markets", "difficulty": "Beginner",
        "estimated_minutes": 6, "xp_reward": 60,
        "content": "Bull market = prices rising 20%+ (optimism, growth). Bear market = prices falling 20%+ (fear, recession). Every bear market in history has eventually recovered. Long-term investors who held through crashes were rewarded.",
        "quiz": [
            {"question": "How is a bear market defined?",
             "options": ["Any down day", "5% drop", "20%+ drop from recent highs", "One year of no growth"],
             "answer": 2, "explanation": "A bear market is a decline of 20% or more from recent highs."},
        ]
    },
    {
        "id": 8, "title": "How Earnings Reports Move Prices", "difficulty": "Intermediate",
        "estimated_minutes": 10, "xp_reward": 85,
        "content": "Every quarter, companies report revenue, profit (EPS), and future guidance. The key isn't whether they made money — it's whether they beat or missed analyst EXPECTATIONS. Beat = stock often jumps 5-15%. Miss = stock often drops 5-20%.",
        "quiz": [
            {"question": "Company reports $2.00 EPS, analysts expected $2.50. What happens?",
             "options": ["Rises — still profitable", "Falls — missed expectations", "Nothing", "Rises — analysts were wrong"],
             "answer": 1, "explanation": "Missing expectations usually causes the stock to fall, even if profitable."},
        ]
    },
    {
        "id": 9, "title": "Compound Growth", "difficulty": "Beginner",
        "estimated_minutes": 8, "xp_reward": 75,
        "content": "Compound interest earns returns on your returns. Rule of 72: divide 72 by your annual return to find years to double. At 10% return, money doubles every 7.2 years. $10,000 at 10% for 40 years = $452,000. Start early!",
        "quiz": [
            {"question": "Using Rule of 72, how long to double money at 9% return?",
             "options": ["4 years", "8 years", "12 years", "18 years"],
             "answer": 1, "explanation": "72 / 9 = 8 years."},
        ]
    },
    {
        "id": 10, "title": "Common Investing Mistakes", "difficulty": "Intermediate",
        "estimated_minutes": 10, "xp_reward": 100,
        "content": "1. Panic selling during dips. 2. FOMO buying at peaks. 3. Overtrading (fees add up). 4. No diversification. 5. Following tips blindly. 6. Trying to time the market. 7. Confusing cheap price with good value.",
        "quiz": [
            {"question": "What is panic selling?",
             "options": ["Selling at year end", "Selling out of fear during a drop, often at a loss", "Broker auto-selling", "Quick profit capture"],
             "answer": 1, "explanation": "Panic selling means selling from fear — often the worst time to sell."},
            {"question": "Why is a $5 stock not necessarily cheap?",
             "options": ["Price is always a good indicator", "Cheap stocks are always bad", "Value depends on fundamentals not just share price", "Only $100+ stocks are worth buying"],
             "answer": 2, "explanation": "A $5 stock with 10 billion shares has a $50B market cap. Price alone means nothing."},
        ]
    },
]


def get_lesson(lesson_id: int) -> dict:
    for lesson in LESSONS:
        if lesson["id"] == lesson_id:
            return lesson
    return None


def get_all_lessons_summary() -> list:
    return [
        {
            "id": l["id"], "title": l["title"], "difficulty": l["difficulty"],
            "estimated_minutes": l["estimated_minutes"], "xp_reward": l["xp_reward"],
            "num_quiz_questions": len(l.get("quiz", [])),
        }
        for l in LESSONS
    ]


def grade_quiz(lesson_id: int, answers: list) -> dict:
    lesson = get_lesson(lesson_id)
    if not lesson:
        return {"error": "Lesson not found"}
    quiz = lesson.get("quiz", [])
    if not quiz:
        return {"score": 1.0, "passed": True, "feedback": []}

    correct = 0
    feedback = []
    for i, question in enumerate(quiz):
        user_answer = answers[i] if i < len(answers) else -1
        is_correct = user_answer == question["answer"]
        if is_correct:
            correct += 1
        feedback.append({
            "question": question["question"],
            "your_answer": question["options"][user_answer] if 0 <= user_answer < len(question["options"]) else "No answer",
            "correct_answer": question["options"][question["answer"]],
            "is_correct": is_correct,
            "explanation": question["explanation"],
        })

    score = correct / len(quiz)
    passed = score >= QUIZ_PASS_SCORE
    return {
        "lesson_id": lesson_id, "score": round(score, 2),
        "score_pct": round(score * 100, 1), "correct": correct,
        "total": len(quiz), "passed": passed,
        "xp_earned": lesson["xp_reward"] if passed else int(lesson["xp_reward"] * score),
        "feedback": feedback,
        "message": "Lesson passed!" if passed else f"Need {int(QUIZ_PASS_SCORE*100)}% to pass. Keep learning!",
    }
