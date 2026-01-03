import os
import json
import traceback
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from groq import Groq

from app.core.config import settings
from app.core.security import get_current_user
from app.models.schemas import ChatRequest
from app.services.mcp_manager import get_mcp_client, execute_multi_account_tool
from app.services.ai_engine import (
    init_engine, 
    route_query, 
    validate_tool_availability, 
    convert_to_groq_tools, 
    clean_history_for_groq, 
    get_tool_map
)
from app.services import storage

router = APIRouter()

@router.get("/chats/{chat_id}")
async def get_chat(chat_id: str, username: str = Depends(get_current_user)):
    return {"messages": storage.get_chat_messages(username, chat_id)}

@router.post("/chats/new")
async def create_chat(username: str = Depends(get_current_user)):
    chat_id = storage.create_new_chat(username)
    return {"chatId": chat_id}

@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str, username: str = Depends(get_current_user)):
    storage.delete_chat(username, chat_id)
    return {"status": "deleted"}

@router.post("/chat")
async def chat_endpoint(request: ChatRequest, username: str = Depends(get_current_user)):
    try:
        # 1. Global Initialization
        client, metadata = init_engine()

        chat_id = request.chatId or storage.create_new_chat(username)
        if not request.isRetry:
            storage.add_message(username, chat_id, "user", request.message)

        # 2. Routing with specific service identification
        route = route_query(client, request.message, request.history)
        
        # 3. Normal Chat handling
        if route["category"] == "NORMAL_CHAT":
            messages = [
                {"role": "system", "content": "You are a helpful AI. Scope: Conversational/Informational. Do NOT mention tools/integrations."}
            ]
            messages.extend(clean_history_for_groq(request.history))
            messages.append({"role": "user", "content": request.message})

            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.7,
                max_tokens=1024
            )
            content = response.choices[0].message.content
            storage.add_message(username, chat_id, "model", content)
            return {"response": content, "chatId": chat_id}

        # 4. Service Related - Validation
        target_service = route["service"]
        
        # 8 & 9. Immediate Authentication Check (Move this up)
        # Even before validation, if we know the service, check auth
        if target_service and target_service not in ["none", "platform"]:
            storage_service = ("google" if any(x in target_service for x in ["google", "gmail", "calendar"]) else target_service).lower()
            
            # Skip auth check for keyless services
            if storage_service not in ["web-search"]:
                accounts = storage.get_service_accounts(username, storage_service)
                if not accounts:
                    redirect_url = f"http://localhost:3000/api/auth/{storage_service}/login?userId={username}"
                    msg = f"It looks like you want to use {storage_service.title()}. I'll redirect you to connect your account now."
                    storage.add_message(username, chat_id, "model", msg)
                    return {"response": msg, "redirect": redirect_url, "chatId": chat_id}

        is_available, operation_type, active_service, gatekeeper_msg = validate_tool_availability(
            client, request.message, target_service, request.history
        )

        # 6. Genuine response if tools don't satisfy
        if not is_available:
            storage.add_message(username, chat_id, "model", gatekeeper_msg)
            return {"response": gatekeeper_msg, "chatId": chat_id}

        # Derive service for account handling
        storage_service = ("google" if any(x in active_service for x in ["google", "gmail", "calendar"]) else active_service).lower()
        accounts = storage.get_service_accounts(username, storage_service)

        # 10. Multi-Account Logic
        selected_account_id = (request.selectedAccounts or {}).get(storage_service)
        
        if operation_type == "WRITE" and not selected_account_id and storage_service != "platform":
            return {
                "action": "select_account",
                "service": storage_service,
                "accounts": [{"id": a["account_id"], "label": a["label"]} for a in accounts],
                "chatId": chat_id
            }

        # Notion Selection logic (preserve)
        if storage_service == "notion":
            page_id = (request.selectedContext or {}).get("notion_page")
            if not page_id:
                mcp_client = await get_mcp_client(username, request.selectedAccounts, target_service="notion")
                if mcp_client:
                    try:
                        mcp_tools = await mcp_client.list_tools()
                        search_tool = next((t.name for t in mcp_tools if "search" in t.name.lower()), "notion_search")
                        search_res = await mcp_client.call_tool(search_tool, {"query": "", "page_size": 15})
                        items = []
                        if hasattr(search_res, 'content') and isinstance(search_res.content, list):
                            for part in search_res.content:
                                try:
                                    data = json.loads(part.text)
                                    results = data.get("results", [])
                                    for item in results:
                                        title = "Untitled"
                                        if item.get("object") in ["page", "database"]:
                                            props = item.get("properties", {})
                                            title_prop = props.get("title") or props.get("Name")
                                            if title_prop and title_prop.get("title"):
                                                title = title_prop["title"][0].get("plain_text", "Untitled")
                                            elif item.get("object") == "database":
                                                title = item.get("title", [{}])[0].get("plain_text", "Untitled")
                                        items.append({"id": item["id"], "label": title, "type": item["object"]})
                                except: pass
                        if items:
                            return {"action": "select_context", "service": "notion", "context_type": "page", "options": items[:15], "chatId": chat_id}
                    except: pass

        active_account = next((a for a in accounts if a["account_id"] == selected_account_id), accounts[0] if accounts else None)
        active_label = active_account["label"] if active_account else None

        # 7. Execute MCP tool loop
        mcp_client = await get_mcp_client(username, request.selectedAccounts, target_service=active_service)
        if not mcp_client:
            return {"response": "Failed to initialize service client. Please try again."}
            
        mcp_tools = await mcp_client.list_tools()
        groq_tools = convert_to_groq_tools(mcp_tools)
        tool_name_map = get_tool_map()

        system_prompt = (
            "You are Connective AI, a professional assistant.\n"
            f"You are currently acting as '{active_label}' on {storage_service.title()}.\n\n"
            "INSTRUCTIONS:\n"
            f"1. Help the user by using the available tools. (Recommendation: {gatekeeper_msg})\n"
            "2. Always use the official tool-calling API. Never write manual <function> tags.\n"
            "3. Use real values provided in the USER IDENTITY or context. Do not use placeholders.\n"
            "4. If a piece of information is missing, ask the user for it politely."
        )
        if storage_service == "notion" and (request.selectedContext or {}).get("notion_page"):
            system_prompt += f"\n5. Selected Notion ID: '{request.selectedContext['notion_page']}' (Use this for page/database operations)."

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(clean_history_for_groq(request.history, limit=12))
        messages.append({"role": "user", "content": request.message})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            tools=groq_tools,
            tool_choice="auto",
            temperature=0
        )
        
        resp_msg = response.choices[0].message
        messages.append(resp_msg)

        if not resp_msg.tool_calls:
            storage.add_message(username, chat_id, "model", resp_msg.content)
            return {"response": resp_msg.content, "chatId": chat_id}

        for tool_call in resp_msg.tool_calls:
            t_name = tool_name_map.get(tool_call.function.name, tool_call.function.name)
            t_args = json.loads(tool_call.function.arguments)

            # Special handling for multi-account READ
            if operation_type == "READ" and len(accounts) > 1 and not selected_account_id and storage_service != "platform":
                result_text = await execute_multi_account_tool(username, storage_service, t_name, t_args)
            else:
                try:
                    res = await mcp_client.call_tool(t_name, t_args)
                    result_text = "\n".join([c.text for c in res.content if hasattr(c, 'text')]) if hasattr(res, 'content') else str(res)
                except Exception as e: result_text = f"Error executing tool: {e}"

            messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": result_text})

        # 11. Final summary after tool call
        summary_resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.3
        )
        final_text = summary_resp.choices[0].message.content
        storage.add_message(username, chat_id, "model", final_text)
        return {"response": final_text, "chatId": chat_id}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
