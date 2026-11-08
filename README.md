# Connective AI Platform

A chat app that lets you work with GitHub, Notion, Gmail, Google Calendar, Slack, Salesforce and web search from one conversation. The FastAPI backend is an MCP (Model Context Protocol) client: it starts an MCP server per connected service, hands its tools to a Llama 3.1 model on Groq, and lets the model pick the tool calls. The frontend is React with Vite.

I built it as the capstone of a series of MCP experiments (GitHub, Notion, Google, Slack, Salesforce servers), to wire them all into one orchestrating model. It runs locally and was a solo project.

## How it works

A message to `POST /api/chat` goes through these stages (`server/app/services/ai_engine.py`, `server/app/api/chat.py`):

1. **Route.** `llama-3.1-8b-instant` at temperature 0 with JSON output labels the message `NORMAL_CHAT` or `SERVICE_RELATED` and names the target service (github, notion, gmail, calendar, slack, web-search, salesforce, platform, or none), using the last few turns as context.
2. **Plain chat.** If it is not service-related, the model just answers.
3. **Auth check.** If the target service is not connected, the response carries a redirect URL to that service's OAuth login. Web search needs no connection.
4. **Gatekeeper.** The model sees the service's tool metadata and says whether a tool can do the requested action and whether it is a read or a write. Missing parameters are filled in later.
5. **Account or context selection.** For a write on a service with several connected accounts, the API returns `select_account` so the UI can ask which one. For Notion it returns `select_context` with pages and databases found by a live search.
6. **Execute.** The MCP tools are converted to Groq's tool-call schema (names sanitised, noisy fields such as Notion `children`, `icon`, `cover` and Slack `cursor` stripped) and the model is called with `tool_choice="auto"`. Reads fan out across all connected accounts in parallel.
7. **Summarise.** Tool results go back to the model for a final answer, which is saved to the chat history.

`mcp_manager.py` keeps one `fastmcp` client per user and rebuilds it only when the active accounts or target service change. `mcp_config.py` defines how each server is started:

- GitHub, Notion, Slack, Salesforce and web search (DuckDuckGo) run through `npx` using their published MCP packages.
- Google Mail and Google Calendar are local Python `fastmcp` servers using the Google API client.
- `platform_manager.py` is a small local server with `list_integrations` and `redirect_to_auth`.

`auth.py` implements the OAuth authorization-code flow for GitHub, Notion, Google, Slack and Salesforce and issues an HS256 JWT. `storage.py` keeps users, connections and chat history in JSON files, with SHA-256 password hashes.

The client has a login screen, a `/` slash menu with example prompts per service, modals for account and Notion page selection, and a chat history sidebar.

## Tech stack

- Backend: Python, FastAPI, Uvicorn, `fastmcp`, `groq`, httpx, PyJWT, Google API client
- Frontend: React 18, Vite 5, lucide-react
- MCP servers: `@modelcontextprotocol/server-github`, `@notionhq/notion-mcp-server`, `@modelcontextprotocol/server-slack`, `@advanced-communities/salesforce-mcp-server`, `@oevortex/ddg_search`
- Storage: JSON files

## Setup

You need Python 3.10+, Node 18+ (the `npx` servers need it), a Groq API key, and OAuth app credentials for each service you want to use.

There is no `requirements.txt`. These are the third-party packages the backend imports:

```bash
cd server
pip install fastapi uvicorn groq fastmcp python-dotenv pyjwt httpx pydantic \
            google-auth google-api-python-client
cp .env.template .env      # fill in GROQ_API_KEY, OAuth client IDs/secrets, JWT_SECRET
cd ../client
npm install
```

Register each OAuth app with the redirect URI `http://localhost:3000/auth/<service>/callback`.

```bash
# backend, from server/
uvicorn app.main:app --port 3000

# frontend, from client/
npm run dev        # http://localhost:5173
```

The client calls `http://localhost:3000` directly, so keep the backend on port 3000.

## Usage

Sign up, then type `/` for the service menu or just write a request, for example:

- `Create a private repository named 'Project-X'`
- `List my recently edited Notion pages`
- `Send 'Finished the task' to #general`
- `What's on my calendar today?`
- `Search the web for the latest MCP news`

The first time you target a service you have not connected, you are sent through its OAuth login and returned to the chat.

## Project structure

```
client/                 React + Vite app (App.jsx, Auth.jsx, styles)
server/
  .env.template
  app/
    main.py             FastAPI app, CORS, routers
    api/                auth.py (signup, login, OAuth), chat.py (chat pipeline, chat CRUD)
    core/               config.py, security.py (JWT)
    models/             Pydantic request models
    services/           ai_engine, mcp_manager, mcp_config, storage
      mcp_servers/      platform_manager.py, google_calendar.py
```

## Limitations

- `mcp_config.py` starts `google_mail.py`, but that file is not in the repo, so Gmail does not work as committed.
- No `requirements.txt` and no tests.
- Passwords are hashed with plain SHA-256, tokens are stored in a JSON file, and CORS allows all origins, so this is for local use only.
- The backend falls back to a default `JWT_SECRET` if none is set.
