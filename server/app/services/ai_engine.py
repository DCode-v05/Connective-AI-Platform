import os
import json
from typing import List, Dict, Any, Tuple, Optional
from groq import Groq
from app.core.config import settings

TOOL_NAME_MAP = {}
METADATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "metadata.json")
GLOBAL_METADATA = {}
GROQ_CLIENT = None

def init_engine():
    global GLOBAL_METADATA, GROQ_CLIENT
    if not GLOBAL_METADATA:
        try:
            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH, "r") as f:
                    GLOBAL_METADATA = json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {e}")
            GLOBAL_METADATA = {}
    
    if not GROQ_CLIENT:
        GROQ_CLIENT = Groq(api_key=settings.GROQ_API_KEY)
    return GROQ_CLIENT, GLOBAL_METADATA

def route_query(client: Groq, message: str, history: List[Dict[str, Any]] = []) -> Dict[str, str]:
    context = ""
    if history:
        last_msgs = history[-3:]
        context = "RECENT CONTEXT:\n" + "\n".join([f"{m['role']}: {m.get('parts', [{}])[0].get('text', '')}" for m in last_msgs])

    prompt = (
        "You are a STRICT routing engine in a multi-service AI platform.\n\n"
        "Your task is to classify the user's latest message and identify the target service if applicable.\n\n"
        "CATEGORIES:\n"
        "1. SERVICE_RELATED: Requires external data (GitHub, Notion, Slack, Google Mail, etc.)\n"
        "2. NORMAL_CHAT: Purely conversational/informational.\n\n"
        "SERVICES: github, notion, gmail, calendar, slack, web-search, salesforce, platform, none.\n\n"
        "RULES:\n"
        "- Classify as SERVICE_RELATED only if a service action is explicit or implied by context.\n"
        "- Identify the primary service name.\n"
        "- Respond in JSON format ONLY.\n\n"
        "CONTEXT:\n"
        f"{context}\n\n"
        "LATEST MESSAGE:\n"
        f"{message}\n\n"
        "OUTPUT FORMAT:\n"
        "{\"category\": \"SERVICE_RELATED|NORMAL_CHAT\", \"service\": \"service_name\"}"
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=100
    )

    try:
        res = json.loads(response.choices[0].message.content)
        return {
            "category": res.get("category", "NORMAL_CHAT").upper(),
            "service": res.get("service", "none").lower()
        }
    except:
        return {"category": "NORMAL_CHAT", "service": "none"}

def validate_tool_availability(client: Groq, message: str, targeted_service: str, history: List[Dict[str, Any]] = []) -> Tuple[bool, str, Optional[str], str]:
    metadata = GLOBAL_METADATA
    
    services_to_check = ["platform"]
    if targeted_service and targeted_service != "none":
        services_to_check.append(targeted_service)
        if targeted_service in ["gmail", "calendar"]: services_to_check.append("google")
        if targeted_service in ["web-search"]: services_to_check.append("web-search")

    detailed_metadata = ""
    for service in set(services_to_check):
        if service in metadata:
            detailed_metadata += f"--- {service.upper()} ---\n"
            for t in metadata[service]:
                detailed_metadata += f"Tool: {t['name']} - {t['description']}\n"

    context = ""
    if history:
        last_msgs = [m for m in history if not (m.get("role") == "model" and "No tool available" in m.get("parts", [{}])[0].get("text", ""))]
        last_msgs = last_msgs[-3:]
        context = "HISTORY:\n" + "\n".join([f"{m['role']}: {m.get('parts', [{}])[0].get('text', '')}" for m in last_msgs])

    prompt = (
        "Role: Capability Checker. Task: Determine if any of the provided tools can perform the ACTION requested.\n"
        "Respond in JSON format ONLY.\n"
        "STRICT RULE: If a tool exists for the general task (e.g., 'create_repo' for a 'make repository' request), "
        "set can_fulfill=True even if the user hasn't provided all parameters (like owner or repo name).\n"
        "The execution engine will handle missing parameters later.\n\n"
        f"HISTORY:\n{context}\n\n"
        f"REQUEST: {message}\n\n"
        f"AVAILABLE TOOLS:\n{detailed_metadata}\n\n"
        "FORMAT:\n"
        "{\"can_fulfill\": bool, \"operation_type\": \"READ|WRITE\", \"message\": \"tool_name or denial_reason\"}"
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=300
    )

    try:
        res = json.loads(response.choices[0].message.content)
        op_type = res.get("operation_type", "READ")
        msg = res.get("message")
        
        if res.get("can_fulfill") is True:
            return True, op_type, targeted_service, msg
        
        return False, "READ", targeted_service, msg or "I'm sorry, I don't have a tool to handle that specific request."
    except Exception:
        return False, "READ", None, "I'm sorry, I couldn't verify tool availability right now."

def clean_schema(schema):
    if not schema: return None
    if "anyOf" in schema: return clean_schema(schema["anyOf"][0])
    if "oneOf" in schema: return clean_schema(schema["oneOf"][0])

    clean = {}
    if "type" in schema:
        val = schema["type"]
        if isinstance(val, list):
            types = [t for t in val if t != "null"]
            clean["type"] = types[0].lower() if types else "string"
        else:
            clean["type"] = val.lower() if isinstance(val, str) else "object"

    if "description" in schema: 
        clean["description"] = schema["description"] or "No description provided."

    if "properties" in schema:
        clean["properties"] = {k: clean_schema(v) for k, v in schema["properties"].items()}

    if "required" in schema: clean["required"] = schema["required"]
    return clean

def convert_to_groq_tools(mcp_tools: List[Any]) -> List[Dict[str, Any]]:
    tools = []
    TOOL_NAME_MAP.clear()
    for tool in mcp_tools:
        schema = tool.inputSchema if tool.inputSchema else {"type": "object", "properties": {}}

        if "properties" in schema:
            if tool.name.startswith("slack"):
                schema["properties"].pop("cursor", None)

            if tool.name.startswith("notion"):
                schema["properties"].pop("icon", None)
                schema["properties"].pop("cover", None)
                schema["properties"].pop("children", None)

            if "required" in schema:
                schema["required"] = [r for r in schema["required"] if r in schema["properties"]]

        safe_name = tool.name.replace("-", "_").replace(".", "_")
        TOOL_NAME_MAP[safe_name] = tool.name
        tools.append({
            "type": "function",
            "function": {
                "name": safe_name,
                "description": tool.description or "No description provided.",
                "parameters": clean_schema(schema)
            }
        })
    return tools

def clean_history_for_groq(history: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    messages = []
    trimmed_history = history[-limit:] if history else []

    for idx, msg in enumerate(trimmed_history):
        role = msg.get("role")
        parts = msg.get("parts", [])
        content = ""
        tool_calls = []
        
        if role == "function":
            for p_idx, part in enumerate(parts):
                if "functionResponse" in part:
                    resp = part["functionResponse"]
                    t_name = resp.get("name", "unknown").replace("-", "_").replace(".", "_")
                    text_content = str(resp.get("response", {}).get("result", "")) or "Done."
                    if len(text_content) > 2000:
                        text_content = text_content[:1000] + "\n...[TRUNCATED]...\n" + text_content[-1000:]
                    messages.append({
                        "role": "tool", 
                        "tool_call_id": f"call_{t_name}_{idx}_{p_idx}", 
                        "name": t_name, 
                        "content": text_content
                    })
            continue

        for p_idx, part in enumerate(parts):
            if "text" in part:
                content += part["text"]
            elif "functionCall" in part:
                fc = part["functionCall"]
                t_name = fc["name"].replace("-", "_").replace(".", "_")
                tool_calls.append({
                    "id": f"call_{t_name}_{idx}_{p_idx}", 
                    "type": "function", 
                    "function": {
                        "name": t_name, 
                        "arguments": json.dumps(fc.get("args", {}))
                    }
                })
        
        if role == "model": role = "assistant"
        if role == "assistant":
            msg_obj = {"role": role, "content": content if content.strip() else (None if tool_calls else "...")}
            if tool_calls: msg_obj["tool_calls"] = tool_calls
            messages.append(msg_obj)
        elif role == "user":
            u_content = content or "..."
            if len(u_content) > 1000: u_content = u_content[:1000] + "..."
            messages.append({"role": role, "content": u_content})
    return messages

def get_tool_map():
    return TOOL_NAME_MAP
