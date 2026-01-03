import base64
import httpx
import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.core.security import create_access_token, get_current_user
from app.models.schemas import UserAuth
from app.services.mcp_manager import remove_client, get_mcp_client
from app.services import storage

api_router = APIRouter()
callback_router = APIRouter()

@api_router.post("/signup")
async def signup(auth: UserAuth):
    success, msg = storage.create_user(auth.username, auth.password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@api_router.post("/login")
async def login(auth: UserAuth):
    if storage.verify_user(auth.username, auth.password):
        token = create_access_token(auth.username)
        return {"username": auth.username, "token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@api_router.get("/status")
async def get_status(username: str = Depends(get_current_user)):
    conns = storage.get_all_connections(username)
    chats = storage.get_all_chats(username)
    return {
        "status": "running",
        "github_connected": "github" in conns,
        "notion_connected": "notion" in conns,
        "slack_connected": "slack" in conns,
        "gmail_connected": "google" in conns,
        "calendar_connected": "google" in conns,
        "salesforce_connected": "salesforce" in conns,
        "google_connected": "google" in conns,
        "chats": chats
    }

@api_router.get("/auth/github/login")
async def github_login(userId: str):
    scope = "repo user"
    redirect_uri = f"http://localhost:3000/auth/github/callback"
    return RedirectResponse(f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&redirect_uri={redirect_uri}&scope={scope}&state={userId}")

@callback_router.get("/auth/github/callback")
async def github_callback(code: str, state: str):
    token_url = "https://github.com/login/oauth/access_token"
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, json={"client_id": settings.GITHUB_CLIENT_ID, "client_secret": settings.GITHUB_CLIENT_SECRET, "code": code}, headers={"Accept": "application/json"})
        data = resp.json()
        if "error" in data: raise HTTPException(status_code=400, detail=data.get("error_description"))
        access_token = data.get("access_token")
        user_resp = await client.get("https://api.github.com/user", headers={"Authorization": f"Bearer {access_token}"})
        username = user_resp.json().get("login")
        storage.save_user_connection(state, "github", {"token": access_token, "username": username})
        remove_client(state)
        await get_mcp_client(state)
        token = create_access_token(state)
        return RedirectResponse(f"{settings.FRONTEND_URL}?auth_success=true&userId={state}&token={token}")

@api_router.get("/auth/notion/login")
async def notion_login(userId: str):
    redirect_uri = "http://localhost:3000/auth/notion/callback"
    return RedirectResponse(f"https://api.notion.com/v1/oauth/authorize?client_id={settings.NOTION_CLIENT_ID}&response_type=code&owner=user&redirect_uri={redirect_uri}&state={userId}")

@callback_router.get("/auth/notion/callback")
async def notion_callback(code: str, state: str):
    token_url = "https://api.notion.com/v1/oauth/token"
    auth_str = base64.b64encode(f"{settings.NOTION_CLIENT_ID}:{settings.NOTION_CLIENT_SECRET}".encode()).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, json={"grant_type": "authorization_code", "code": code, "redirect_uri": "http://localhost:3000/auth/notion/callback"}, headers={"Authorization": f"Basic {auth_str}", "Notion-Version": "2022-06-28"})
        data = resp.json()
        if "error" in data: raise HTTPException(status_code=400, detail=data.get("error"))
        storage.save_user_connection(state, "notion", {"token": data.get("access_token"), "username": data.get("owner", {}).get("user", {}).get("name") or "Notion Workspace"})
        remove_client(state)
        await get_mcp_client(state)
        token = create_access_token(state)
        return RedirectResponse(f"{settings.FRONTEND_URL}?auth_success=true&userId={state}&token={token}")

@api_router.get("/auth/google/login")
async def google_login(userId: str):
    scope = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events"
    redirect_uri = "http://localhost:3000/auth/google/callback"
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope={scope}&access_type=offline&prompt=consent&state={userId}")

@callback_router.get("/auth/google/callback")
async def google_callback(code: str, state: str):
    token_url = "https://oauth2.googleapis.com/token"
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data={"client_id": settings.GOOGLE_CLIENT_ID, "client_secret": settings.GOOGLE_CLIENT_SECRET, "code": code, "grant_type": "authorization_code", "redirect_uri": "http://localhost:3000/auth/google/callback"})
        data = resp.json()
        if "error" in data: raise HTTPException(status_code=400, detail=data.get("error_description"))
        access_token = data.get("access_token")
        user_resp = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        email = user_resp.json().get("email")
        storage.save_user_connection(state, "google", {"token": access_token, "refresh_token": data.get("refresh_token"), "email": email})
        remove_client(state)
        await get_mcp_client(state)
        token = create_access_token(state)
        return RedirectResponse(f"{settings.FRONTEND_URL}?auth_success=true&userId={state}&token={token}")

@api_router.get("/auth/slack/login")
async def slack_login(userId: str):
    scope = "chat:write channels:read groups:read"
    redirect_uri = "http://localhost:3000/auth/slack/callback"
    return RedirectResponse(f"https://slack.com/oauth/v2/authorize?client_id={settings.SLACK_CLIENT_ID}&user_scope={scope}&redirect_uri={redirect_uri}&state={userId}")

@callback_router.get("/auth/slack/callback")
async def slack_callback(code: str, state: str):
    token_url = "https://slack.com/api/oauth.v2.access"
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data={"client_id": settings.SLACK_CLIENT_ID, "client_secret": settings.SLACK_CLIENT_SECRET, "code": code, "redirect_uri": "http://localhost:3000/auth/slack/callback"})
        data = resp.json()
        if not data.get("ok"): raise HTTPException(status_code=400, detail=data.get("error"))
        access_token = data.get("authed_user", {}).get("access_token") or data.get("access_token")
        storage.save_user_connection(state, "slack", {"token": access_token, "team_id": data.get("team", {}).get("id"), "username": data.get("team", {}).get("name") or "Slack Workspace"})
        remove_client(state)
        await get_mcp_client(state)
        token = create_access_token(state)
        return RedirectResponse(f"{settings.FRONTEND_URL}?auth_success=true&userId={state}&token={token}")

@api_router.get("/auth/salesforce/login")
async def salesforce_login(userId: str):
    redirect_uri = "http://localhost:3000/auth/salesforce/callback"
    return RedirectResponse(f"https://login.salesforce.com/services/oauth2/authorize?client_id={settings.SALESFORCE_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&state={userId}")

@callback_router.get("/auth/salesforce/callback")
async def salesforce_callback(code: str, state: str):
    token_url = "https://login.salesforce.com/services/oauth2/token"
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data={"grant_type": "authorization_code", "client_id": settings.SALESFORCE_CLIENT_ID, "client_secret": settings.SALESFORCE_CLIENT_SECRET, "code": code, "redirect_uri": "http://localhost:3000/auth/salesforce/callback"})
        data = resp.json()
        if "error" in data: raise HTTPException(status_code=400, detail=data.get("error_description"))
        storage.save_user_connection(state, "salesforce", {"token": data.get("access_token"), "instance_url": data.get("instance_url")})
        remove_client(state)
        await get_mcp_client(state)
        token = create_access_token(state)
        return RedirectResponse(f"{settings.FRONTEND_URL}?auth_success=true&userId={state}&token={token}")

