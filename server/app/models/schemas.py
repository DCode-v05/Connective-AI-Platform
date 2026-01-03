from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class UserAuth(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, Any]]
    chatId: Optional[str] = None
    isRetry: Optional[bool] = False
    selectedAccounts: Optional[Dict[str, str]] = None
    selectedContext: Optional[Dict[str, Any]] = None