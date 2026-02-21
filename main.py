"""
StockSim - A free, educational stock market simulator.
No real money. No ads. No pro plan. Just learning.
"""

import sys
import os

# Fix: adds the project root to Python's path so all submodules resolve correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from data.db import init_db
from data.seed import seed_database

def main():
    print("=" * 60)
    print("  StockSim - Learn to Trade Without Risk")
    print("  100% Free | No Ads | No Real Money")
    print("=" * 60)

    print("\n[*] Initializing database...")
    init_db()

    print("[*] Seeding sample data...")
    seed_database()

    print("[*] Starting StockSim API server...")
    print("[*] Visit http://localhost:8000/docs for interactive API docs\n")

    uvicorn.run(
        "api.routes:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[os.path.dirname(os.path.abspath(__file__))],
        log_level="info"
    )

if __name__ == "__main__":
    main()
