# Connective AI Platform

**One chat box that talks to GitHub, Notion, Gmail, Calendar, Slack, Salesforce and the web — through the Model Context Protocol.**

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white) ![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black) ![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat&logo=vite&logoColor=white) ![Groq](https://img.shields.io/badge/Groq-F55036?style=flat&logo=groq&logoColor=white) ![Llama](https://img.shields.io/badge/Llama_3.1-0467DF?style=flat&logo=meta&logoColor=white) ![MCP](https://img.shields.io/badge/Model_Context_Protocol-000000?style=flat&logo=anthropic&logoColor=white) ![JWT](https://img.shields.io/badge/JWT-000000?style=flat&logo=jsonwebtokens&logoColor=white)

## Overview

Connective AI Platform is a multi-tool chat application that sits between you and a handful of external services and lets you drive all of them with plain English. Your code is in GitHub, your notes are in Notion, your mail and meetings are in Google, conversations are in Slack, and your CRM data is in Salesforce. Normally you switch tabs and context all day to move between them. This app puts a single chat window in front of the lot.

The backend is a FastAPI server that acts as an MCP (Model Context Protocol) client. It spins up MCP servers for each connected service, exposes their tools to a Groq-hosted Llama 3.1 model, and lets the model decide which tool to call to answer a request. The frontend is a React + Vite single-page app with a slash-command menu, per-service account selection, and a chat history sidebar.

I built this as the main piece of an MCP learning series — the goal was to take everything I'd learned wiring up individual MCP servers (GitHub, Notion, Google, Slack, Salesforce, a math/weather demo) and connect them all to one orchestrating LLM at once. It's a working solo project, built over Nov–Dec 2025, that runs locally end to end.

## Key Features

- **One chat, seven integrations** — GitHub, Notion, Slack, Gmail, Google Calendar, Salesforce, and DuckDuckGo web search, each behind its own MCP server, all reachable from the same conversation.
- **LLM tool routing** — a Llama 3.1 model on Groq classifies each message, picks the target service, decides whether a tool can actually do the job, then calls it through the official tool-calling API and summarizes the result.
- **Three-stage request pipeline** — a router stage, a capability gatekeeper, and an execution stage, so the model only attempts actions it has tools for and gives an honest answer when it doesn't.
- **Full OAuth 2.0 onboarding** — proper authorization-code flows for GitHub, Notion, Google, Slack, and Salesforce. When you ask for a service you haven't connected, the app redirects you to log in, then drops you back into the chat.
- **Multi-account support** — you can connect more than one account per service. Read requests fan out across all your accounts in parallel; write requests prompt you to pick exactly which account to act as.
- **Slash-command UI** — type `/` to pop a service menu with example prompts for each integration, so you don't have to remember what's possible.
- **Context picker for Notion** — before a Notion action runs, the app searches your workspace and lets you choose the specific page or database to operate on.
- **Web search without keys** — DuckDuckGo search runs through a public MCP server, so it works with no API key attached.
- **Per-user accounts and chat history** — username/password signup with SHA-256 hashing and JWT sessions, persistent multi-session chat history, and create/delete chat management.
- **Internal platform tools** — a small built-in MCP server that the model can call to list available integrations or trigger an auth redirect mid-conversation.

## How It Works

### Frontend (React + Vite)

The client (`client/`) is a single-page React 18 app built with Vite, using `lucide-react` for icons and hand-written CSS for a glassmorphism look. It handles:

- Auth screen (signup/login) and JWT storage in `localStorage`.
- A chat composer with a `/` slash-command menu that lists the seven services and canned example prompts per service.
- Modal flows driven by the backend: an account-selection modal (when a write needs a specific account) and a context-selection modal (when Notion needs a target page).
- The chat history sidebar — new chat, switch chat, delete chat — talking to the backend over a small REST API.

All calls go to `http://localhost:3000/api/...` with a `Bearer` token header.

### Backend (FastAPI as an MCP client)

The server (`server/app/`) is a FastAPI app. On startup it initializes the AI engine and loads tool metadata; on shutdown it closes every open MCP client. Routes are split into `auth` (signup, login, status, and the OAuth login/callback endpoints) and `chat` (the main `/api/chat` endpoint plus chat CRUD).

### The chat pipeline

A single message to `/api/chat` runs through these stages:

1. **Route** — `route_query` sends the message (plus the last few turns of context) to `llama-3.1-8b-instant` with `temperature=0` and a JSON response format, classifying it as `NORMAL_CHAT` or `SERVICE_RELATED` and naming the target service (github, notion, gmail, calendar, slack, web-search, salesforce, platform, or none).
2. **Normal chat** — if it's just conversation, the model answers directly with a short system prompt and the cleaned history. No tools touched.
3. **Auth check** — if a service is targeted and you haven't connected it, the response carries a redirect URL to that service's OAuth login (web search is skipped here since it needs no key).
4. **Gatekeeper** — `validate_tool_availability` shows the model the tool metadata for the targeted service and asks, in JSON, whether any tool can perform the requested *action* and whether it's a READ or WRITE. Missing parameters are allowed; the execution stage fills them in later.
5. **Account selection** — for WRITE operations across a multi-account service, the backend returns a `select_account` action so the UI can ask which account to use. For Notion, it returns a `select_context` action with a list of pages/databases from a live search.
6. **Execute** — the resolved MCP client lists its tools, they're converted into Groq's tool-call schema (names sanitized, noisy fields like Notion `children`/`icon`/`cover` and Slack `cursor` stripped, schemas flattened), and the model is called with `tool_choice="auto"`. Each tool call is executed against the MCP server — or fanned out across all accounts for multi-account reads.
7. **Summarize** — the tool results are fed back to the model for a final natural-language answer, which is saved to chat history and returned.

### MCP connection management

`mcp_manager.py` keeps a per-user `fastmcp` client alive and reuses it when the active accounts and target service match, tearing it down and rebuilding only when they change. `mcp_config.py` builds the spawn config for each server:

- **GitHub** — `npx @modelcontextprotocol/server-github`, authed with the user's token.
- **Notion** — `npx @notionhq/notion-mcp-server`.
- **Slack** — `npx @modelcontextprotocol/server-slack` (bot token + team ID).
- **Salesforce** — `npx @advanced-communities/salesforce-mcp-server` (OAuth access token + instance URL).
- **Web search** — `npx @oevortex/ddg_search` (DuckDuckGo, no key).
- **Google Mail / Calendar** — local Python MCP servers (`google_mail.py`, `google_calendar.py`) built with `fastmcp` and the Google API client, using the user's OAuth token.
- **Platform** — a local `platform_manager.py` MCP server exposing `list_integrations` and `redirect_to_auth`.

### Auth and storage

`security.py` issues and verifies HS256 JWTs with a configurable expiry. `auth.py` implements the OAuth authorization-code dance for all five external providers — building the consent URL, exchanging the code for an access token at the callback, fetching the account identity, saving the connection, and redirecting back to the frontend with a fresh JWT. `storage.py` is a JSON-file store (`storage.json` for users/connections, `chat_history.json` for chats) with SHA-256 password hashing, multi-account connection records, and light schema migration for older data shapes.

## Tech Stack

- **Languages:** Python, JavaScript, CSS, HTML
- **Frontend:** React 18, Vite 5, lucide-react, hand-written glassmorphism CSS
- **Backend:** FastAPI, Uvicorn, Pydantic, httpx, PyJWT, python-dotenv
- **AI / orchestration:** Groq SDK with `llama-3.1-8b-instant`, Model Context Protocol via `fastmcp`
- **MCP servers:** `@modelcontextprotocol/server-github`, `@notionhq/notion-mcp-server`, `@modelcontextprotocol/server-slack`, `@advanced-communities/salesforce-mcp-server`, `@oevortex/ddg_search`, plus local Python servers for Google Mail, Google Calendar, and platform management
- **Google APIs:** `google-auth`, `google-api-python-client` (Gmail + Calendar v3)
- **Storage:** flat JSON files (users, connections, chat history)

## Getting Started

### Prerequisites

- Python 3.10+ (the bytecode in the repo is built against 3.13)
- Node.js 18+ and npm (also used to launch the JS MCP servers via `npx`)
- A Groq API key
- OAuth app credentials for whichever services you want to use (GitHub, Notion, Google, Slack, Salesforce)

### Installation

```bash
git clone https://github.com/DCode-v05/Connective-AI-Platform.git
cd Connective-AI-Platform

# Backend
cd server
pip install fastapi uvicorn groq fastmcp python-dotenv pyjwt httpx \
            google-auth google-api-python-client pydantic

# Frontend
cd ../client
npm install
```

### Configure environment

Copy the template and fill in your credentials:

```bash
cd server
cp .env.template .env
```

`.env` keys (only app-level OAuth credentials live here — individual user tokens are stored after login):

```
GROQ_API_KEY=...
GITHUB_CLIENT_ID=...        GITHUB_CLIENT_SECRET=...
NOTION_CLIENT_ID=...        NOTION_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...        GOOGLE_CLIENT_SECRET=...
SLACK_CLIENT_ID=...         SLACK_CLIENT_SECRET=...
SALESFORCE_CLIENT_ID=...    SALESFORCE_CLIENT_SECRET=...
JWT_SECRET=change_me
JWT_EXPIRY_MINUTES=60
PORT=3000
FRONTEND_URL=http://localhost:5173
```

When registering each OAuth app, point its redirect URI at `http://localhost:3000/auth/<service>/callback`.

### Running

```bash
# Backend (from server/)
python main.py
# serves on http://localhost:3000

# Frontend (from client/)
npm run dev
# opens on http://localhost:5173
```

## Usage

1. Open `http://localhost:5173`, sign up, and log in.
2. Type `/` to see the service menu, or just write what you want. The first time you target a service you haven't connected, you'll be redirected to its OAuth login and returned to the chat afterward.
3. Ask things like:
   - `Create a private repository named 'Project-X'`
   - `List my recently edited Notion pages`
   - `Send 'Finished the task' to #general`
   - `Any unread emails in Gmail?`
   - `What's on my calendar today?`
   - `Search the web for the latest MCP news`
4. For write actions on a service with multiple connected accounts, you'll be asked to pick the account first. For Notion, you'll pick the target page. Read actions across multiple accounts run in parallel and the results come back grouped per account.

## Project Structure

```
Connective-AI-Platform/
├── client/                          # React + Vite frontend
│   ├── index.html
│   ├── package.json                 # react, react-dom, lucide-react, vite
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx                 # app entry
│       ├── App.jsx                  # chat UI, slash menu, account/context modals
│       ├── Auth.jsx                 # signup / login screen
│       ├── App.css / index.css      # glassmorphism styling
│
├── server/                          # FastAPI backend (MCP client)
│   ├── main.py                      # server runner (uvicorn on :3000)
│   ├── .env.template                # OAuth + Groq + JWT config template
│   └── app/
│       ├── main.py                  # FastAPI app, lifespan, CORS, routers
│       ├── api/
│       │   ├── auth.py              # signup/login + OAuth flows for 5 providers
│       │   └── chat.py              # /api/chat pipeline + chat CRUD
│       ├── core/
│       │   ├── config.py            # settings from env
│       │   └── security.py          # JWT create/verify
│       ├── models/
│       │   └── schemas.py           # Pydantic request models
│       └── services/
│           ├── ai_engine.py         # routing, gatekeeper, Groq tool conversion
│           ├── mcp_manager.py       # per-user MCP client lifecycle, multi-account
│           ├── mcp_config.py        # spawn config per MCP server
│           ├── storage.py           # JSON store: users, connections, chats
│           └── mcp_servers/
│               ├── platform_manager.py   # internal MCP: list/redirect integrations
│               └── google_calendar.py    # local Google Calendar MCP server
└── README.md
```

---

## Contact

<table>
  <tr><td><b>Portfolio:</b> <a href="https://www.denistan.me">Denistan</a></td><td><b>LinkedIn:</b> <a href="https://www.linkedin.com/in/denistanb">denistanb</a></td></tr>
  <tr><td><b>GitHub:</b> <a href="https://github.com/DCode-v05">DCode-v05</a></td><td><b>LeetCode:</b> <a href="https://leetcode.com/u/Denistan_B">Denistan_B</a></td></tr>
  <tr><td colspan="2" align="center"><b>Email:</b> <a href="mailto:denistanb05@gmail.com">denistanb05@gmail.com</a></td></tr>
</table>

Made with ❤️ by **Denistan B**
