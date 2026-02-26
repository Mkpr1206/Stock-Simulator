"""
StockSim Patcher — run this ONCE from your stocksim folder.
It directly patches api/routes.py and app.js with all pending fixes.

Usage:
    cd C:\Users\PRANAV\Desktop\stocksim
    python patch_stocksim.py
"""

import os, sys, re, shutil
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
ROUTES = os.path.join(BASE, "api", "routes.py")
APPJS  = os.path.join(BASE, "app.js")

def backup(path):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = path + f".bak_{ts}"
    shutil.copy2(path, dst)
    print(f"  ✓ Backed up to {os.path.basename(dst)}")

def patch_routes():
    print("\n── Patching api/routes.py ──")
    if not os.path.exists(ROUTES):
        print("  ✗ Not found:", ROUTES); return
    backup(ROUTES)
    src = open(ROUTES, encoding="utf-8").read()
    changes = 0

    # Fix 1: case-insensitive login (username OR email)
    old = '''        with get_db() as conn:
            # Accept username OR email, case-insensitive for both
            user = conn.execute(
                "SELECT * FROM users WHERE LOWER(username)=LOWER(?) OR LOWER(email)=LOWER(?)",
                (form.username, form.username)
            ).fetchone()'''
    new = '''        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE LOWER(username)=LOWER(?) OR LOWER(email)=LOWER(?)",
                (form.username, form.username)
            ).fetchone()'''
    if old in src:
        src = src.replace(old, new, 1); changes += 1
        print("  ✓ Login query already correct")
    else:
        # Try to find and fix the old version
        old2 = '''        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username=?", (form.username,)
            ).fetchone()'''
        old3 = '''        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username=?",
                (form.username,)
            ).fetchone()'''
        replaced = False
        for o in [old2, old3]:
            if o in src:
                src = src.replace(o, new, 1); changes += 1
                print("  ✓ Fixed login to accept username OR email"); replaced = True; break
        if not replaced:
            # Generic regex fix
            src2 = re.sub(
                r'SELECT \* FROM users WHERE username=\?.*?\.fetchone\(\)',
                'SELECT * FROM users WHERE LOWER(username)=LOWER(?) OR LOWER(email)=LOWER(?)"\n            ).fetchone()',
                src, flags=re.DOTALL, count=1
            )
            if src2 != src:
                src = src2; changes += 1
                print("  ✓ Fixed login query (regex)")
            else:
                print("  ~ Login query: no change needed or already fixed")

    # Fix 2: ensure delete account uses id not email
    if 'DELETE FROM users WHERE id=?' in src:
        print("  ✓ Delete account already uses id")
    else:
        src2 = re.sub(
            r'DELETE FROM users WHERE email=\?',
            'DELETE FROM users WHERE id=?',
            src
        )
        if src2 != src:
            src = src2; changes += 1
            print("  ✓ Fixed delete to use id")

    # Fix 3: ensure init_db and seed_database are called at startup
    if 'init_db()' in src and 'seed_database()' in src:
        print("  ✓ init_db/seed_database already present")
    else:
        # Add after imports block
        insert = "\n# Auto-initialize DB on startup (required for Render deployment)\nfrom data.db import init_db\nfrom data.seed import seed_database\ninit_db()\nseed_database()\n"
        src = src.replace("app = FastAPI(", insert + "\napp = FastAPI(", 1)
        changes += 1
        print("  ✓ Added init_db/seed_database at startup")

    open(ROUTES, "w", encoding="utf-8").write(src)
    print(f"  → {changes} change(s) applied to routes.py")

def patch_appjs():
    print("\n── Patching app.js ──")
    if not os.path.exists(APPJS):
        print("  ✗ Not found:", APPJS); return
    backup(APPJS)
    src = open(APPJS, encoding="utf-8").read()
    changes = 0

    # Fix 1: login should NOT lowercase the username (breaks case-sensitive usernames)
    old = "d = await apiForm('/auth/login', { username: usernameOrEmail.toLowerCase(), password });"
    new = "d = await apiForm('/auth/login', { username: usernameOrEmail, password });"
    if old in src:
        src = src.replace(old, new, 1); changes += 1
        print("  ✓ Removed toLowerCase() from login username")
    else:
        print("  ~ Login username: already correct or not found")

    # Fix 2: modalConfirm must be a regular function (not async) for onclick= to work reliably
    # Some browsers have issues with async functions called from onclick
    # Wrap it to handle properly
    if 'async function modalConfirm()' in src:
        src = src.replace(
            'async function modalConfirm()',
            'function modalConfirm()'
        )
        # Also fix the internal await
        src = src.replace(
            '  if (action) {\n    try { await action(); }\n    catch(e) { toast(e.message || \'Action failed\', \'error\'); }\n  }',
            '  if (action) {\n    Promise.resolve(action()).catch(e => toast(e.message || \'Action failed\', \'error\'));\n  }'
        )
        changes += 1
        print("  ✓ Fixed modalConfirm to work reliably with onclick=")
    else:
        print("  ~ modalConfirm: already correct or not found")

    # Fix 3: remove any remaining leaderboard references
    before = src.count('leaderboard') + src.count('Leaderboard') + src.count('profRank')
    src = re.sub(r".*leaderboard.*\n", "", src, flags=re.IGNORECASE)
    src = re.sub(r".*profRank.*\n", "", src)
    src = re.sub(r".*myRank.*\n", "", src)
    after = src.count('leaderboard') + src.count('Leaderboard') + src.count('profRank')
    if before > after:
        changes += 1
        print(f"  ✓ Removed {before - after} leaderboard/rank references")
    else:
        print("  ~ Leaderboard: already clean")

    open(APPJS, "w", encoding="utf-8").write(src)
    print(f"  → {changes} change(s) applied to app.js")

def git_push():
    print("\n── Git commit & push ──")
    os.system('git add .')
    ret = os.system('git commit -m "fix: patch_stocksim.py - login, delete account, leaderboard cleanup"')
    if ret == 0:
        os.system('git push origin main')
        print("  ✓ Pushed to GitHub! Wait 2 min for Render to redeploy.")
    else:
        print("  ~ Nothing new to commit — already up to date")
        print("  → Go to Render dashboard and click Manual Deploy")

if __name__ == "__main__":
    print("=" * 50)
    print("  StockSim Patcher")
    print("=" * 50)
    patch_routes()
    patch_appjs()
    git_push()
    print("\n✅ Done! Check https://stock-simulator-1-vlo6.onrender.com in 2 minutes.")
