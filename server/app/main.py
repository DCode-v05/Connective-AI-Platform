import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import auth, chat
from app.services.mcp_manager import close_all_mcp_clients
from app.core.config import settings

from app.services.ai_engine import init_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    yield
    await close_all_mcp_clients()

app = FastAPI(title="Connective AI Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.api_router, prefix="/api", tags=["Authentication"])
app.include_router(auth.callback_router, tags=["OAuth Callbacks"])
app.include_router(chat.router, prefix="/api", tags=["Chat & AI"])

@app.get("/")
async def root():
    return {"message": "Connective AI Backend is running."}