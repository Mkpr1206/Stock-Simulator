import os

print("\n=== STOCKSIM BACKEND SCANNER ===\n")

keywords = ['register', 'UserCreate', 'UserRegister', 'class User', 
            'def buy', 'def sell', 'def trade', 'BuyRequest', 'SellRequest',
            'TradeRequest', 'hashed_password', 'full_name']

for root, dirs, files in os.walk('.'):
    # Skip hidden folders and cache
    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(path, encoding='utf-8') as fp:
                    for i, line in enumerate(fp, 1):
                        if any(k.lower() in line.lower() for k in keywords):
                            print(f"{path}:{i}:  {line}", end='')
            except:
                pass

print("\n=== END ===")
