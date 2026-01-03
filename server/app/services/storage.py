import json
import os
import hashlib
import uuid

DATA_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STORAGE_FILE = os.path.join(DATA_DIR, "storage.json")
HISTORY_FILE = os.path.join(DATA_DIR, "chat_history.json")

def load_json(filename, default_structure):
    if not os.path.exists(filename):
        save_json(filename, default_structure)
        return default_structure
    with open(filename, "r") as f:
        try:
            data = json.load(f)
            return data if isinstance(data, dict) else default_structure
        except:
            return default_structure

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def load_storage():
    data = load_json(STORAGE_FILE, {"users": {}})
    if not isinstance(data, dict) or "users" not in data:
        data = {"users": {}}

    modified = False
    for username, user_data in data.get("users", {}).items():
        conns = user_data.get("connections", {})
        for service, conn_data in conns.items():
            if not isinstance(conn_data, list):
                label = conn_data.get("username") or conn_data.get("email") or conn_data.get("instance_url") or "Main Account"
                conns[service] = [{"account_id": label, "data": conn_data, "label": label}]
                modified = True

    if modified:
        save_json(STORAGE_FILE, data)
    return data

def save_storage(data):
    save_json(STORAGE_FILE, data)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    storage = load_storage()
    if username in storage["users"]:
        return False, "User already exists"

    storage["users"][username] = {
        "password": hash_password(password),
        "connections": {}
    }
    save_storage(storage)
    return True, "User created successfully"

def verify_user(username, password):
    storage = load_storage()
    user = storage["users"].get(username)
    if user and user["password"] == hash_password(password):
        return True
    return False

def get_user_connection(username, service, account_id=None):
    storage = load_storage()
    conns = storage["users"].get(username, {}).get("connections", {}).get(service, [])
    if not conns:
        return None
    if account_id:
        for c in conns:
            if c["account_id"] == account_id:
                return c["data"]
    return conns[0]["data"]

def save_user_connection(username, service, data):
    storage = load_storage()
    if username not in storage["users"]:
        storage["users"][username] = {"connections": {}, "password": ""}

    if "connections" not in storage["users"][username]:
        storage["users"][username]["connections"] = {}

    if service not in storage["users"][username]["connections"]:
        storage["users"][username]["connections"][service] = []

    account_id = data.get("username") or data.get("email") or data.get("instance_url") or "Default"
    label = account_id

    conns = storage["users"][username]["connections"][service]
    existing = next((c for c in conns if c["account_id"] == account_id), None)
    if existing:
        existing["data"] = data
    else:
        conns.append({"account_id": account_id, "data": data, "label": label})

    save_storage(storage)

def get_service_accounts(username, service):
    storage = load_storage()
    return storage["users"].get(username, {}).get("connections", {}).get(service, [])

def get_all_connections(username):
    storage = load_storage()
    return storage["users"].get(username, {}).get("connections", {})

def _get_history_with_migration(username):
    history = load_json(HISTORY_FILE, {})
    sessions = history.get(username, [])

    needs_migration = False
    if sessions and isinstance(sessions, list):
        if len(sessions) > 0 and "id" not in sessions[0]:
            needs_migration = True

    if needs_migration:
        legacy_messages = sessions
        new_id = str(uuid.uuid4())
        session = {
            "id": new_id,
            "title": "Migrated Chat",
            "messages": legacy_messages
        }
        history[username] = [session]
        save_json(HISTORY_FILE, history)
        return [session]

    return sessions

def get_all_chats(username):

    sessions = _get_history_with_migration(username)
    return [{"id": s["id"], "title": s["title"]} for s in sessions if isinstance(s, dict) and "id" in s]

def get_chat_messages(username, chat_id):

    sessions = _get_history_with_migration(username)
    for s in sessions:
        if isinstance(s, dict) and s.get("id") == chat_id:
            return s.get("messages", [])
    return []

def create_new_chat(username, title="New Chat"):

    history = load_json(HISTORY_FILE, {})
    if username not in history:
        history[username] = []

    _get_history_with_migration(username)
    history = load_json(HISTORY_FILE, {})

    new_id = str(uuid.uuid4())
    history[username].insert(0, {
        "id": new_id,
        "title": title,
        "messages": []
    })
    save_json(HISTORY_FILE, history)
    return new_id

def add_message(username, chat_id, role, text):

    history = load_json(HISTORY_FILE, {})

    _get_history_with_migration(username)
    history = load_json(HISTORY_FILE, {})

    sessions = history.get(username, [])
    session = None
    for s in sessions:
        if isinstance(s, dict) and s.get("id") == chat_id:
            session = s
            break

    if not session:
        if sessions:
            session = sessions[0]
        else:
            new_id = str(uuid.uuid4())
            session = {"id": new_id, "title": text[:30] + "...", "messages": []}
            history[username] = [session]

    session["messages"].append({"role": role, "text": text})

    if session.get("title") == "New Chat" and role == "user":
        session["title"] = text[:40] if len(text) <= 40 else text[:37] + "..."

    save_json(HISTORY_FILE, history)
    return session["id"]

def delete_chat(username, chat_id):
    history = load_json(HISTORY_FILE, {})
    if username in history:
        history[username] = [s for s in history[username] if isinstance(s, dict) and s.get("id") != chat_id]
        save_json(HISTORY_FILE, history)