from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    # Placeholder logic
    if token != "demo-token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"username": "demo"}