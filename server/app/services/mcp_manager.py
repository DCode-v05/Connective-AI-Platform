from fastmcp import Client
from app.services import storage
from app.services.mcp_config import get_mcp_config
import asyncio

mcp_clients = {}

async def get_mcp_client(username: str, selected_accounts: dict = None, target_service: str = None):
    global mcp_clients
    
    if target_service:
        target_service = target_service.lower()
        if target_service in ["gmail", "mail", "google-mail", "calendar", "google-calendar"]:
            target_service = "google"
        if target_service in ["search", "web-search", "duckduckgo", "ddg"]:
            target_service = "web-search"

    current = mcp_clients.get(username)
    if current:
        match = True
        current_active = list(current["accounts"].keys())
        if target_service and (len(current_active) > 2 or target_service not in current_active):
            match = False

        if selected_accounts:
            for s, acc in selected_accounts.items():
                if current["accounts"].get(s) != acc:
                    match = False
                    break

        if match:
            return current["client"]
        else:
            try: await current["client"].__aexit__(None, None, None)
            except: pass
            del mcp_clients[username]

    try:
        all_conns = storage.get_all_connections(username)
        resolved_conns = {}
        active_map = {}

        for service, accounts in all_conns.items():
            if not accounts: continue

            storage_service = "google" if service in ["google-mail", "google-calendar"] else service
            
            normalized_target = target_service.lower() if target_service else None
            if normalized_target in ["gmail", "mail", "google-mail", "calendar", "google-calendar"]: normalized_target = "google"
            if normalized_target in ["search", "web-search", "duckduckgo", "ddg"]: normalized_target = "web-search"

            if normalized_target and storage_service != normalized_target and service != "platform":
                continue

            sel_id = (selected_accounts or {}).get(storage_service)
            match = None
            if sel_id:
                match = next((a for a in accounts if a["account_id"] == sel_id), None)

            if not match:
                match = accounts[0]

            resolved_conns[service] = match["data"]
            active_map[storage_service] = match["account_id"]

        current_config = get_mcp_config(resolved_conns)
        if not current_config: return None

        client = Client(current_config)
        await client.__aenter__()
        mcp_clients[username] = {"client": client, "accounts": active_map}
        return client
    except Exception as e:
        print(f"Error managing MCP servers for user {username}: {e}")
        return None

async def close_all_mcp_clients():
    global mcp_clients
    for username, data in mcp_clients.items():
        try: await data["client"].__aexit__(None, None, None)
        except: pass
    mcp_clients = {}

def remove_client(username: str):
    global mcp_clients
    if username in mcp_clients:
        del mcp_clients[username]

async def execute_multi_account_tool(username: str, service: str, tool_name: str, tool_args: dict):
    accounts = storage.get_service_accounts(username, service)
    if not accounts:
        return "No accounts connected for this service."

    async def call_single(acc):
        config = get_mcp_config({service: acc["data"]})
        try:
            async with Client(config) as client:
                res = await client.call_tool(tool_name, tool_args)
                text = "\n".join([c.text for c in res.content if hasattr(c, 'text')]) if hasattr(res, 'content') else str(res)
                return f"### Account: {acc['label']}\n{text}"
        except Exception as e:
            return f"### Account: {acc['label']}\nError: {str(e)}"

    results = await asyncio.gather(*(call_single(a) for a in accounts))
    return "\n\n" + "\n\n---\n\n".join(results)