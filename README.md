# Connective AI Platform

**One chat box that talks to GitHub, Notion, Gmail, Calendar, Slack, Salesforce and the web, through the Model Context Protocol.**

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white) ![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black) ![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat&logo=vite&logoColor=white) ![Groq](https://img.shields.io/badge/Groq-F55036?style=flat&logo=groq&logoColor=white) ![Llama](https://img.shields.io/badge/Llama_3.1-0467DF?style=flat&logo=meta&logoColor=white) ![MCP](https://img.shields.io/badge/Model_Context_Protocol-000000?style=flat&logo=anthropic&logoColor=white) ![JWT](https://img.shields.io/badge/JWT-000000?style=flat&logo=jsonwebtokens&logoColor=white)

## Overview

Connective AI Platform is a chat app that sits between you and a handful of external services and lets you drive them in plain English. Your code is in GitHub, your notes are in Notion, your mail and meetings are in Google, your conversations are in Slack and your CRM data is in Salesforce. Normally you switch tabs all day to move between them. This app puts one chat window in front of all of them.

The backend is a FastAPI server that acts as an MCP (Model Context Protocol) client. It starts an MCP server for each connected service, hands their tools to a Groq-hosted Llama 3.1 model, and lets the model decide which tool to call. The frontend is a React + Vite single-page app with a slash-command menu, per-service account selection and a chat history sidebar.

I built it as the capstone of an MCP learning series. I had wired up individual MCP servers (GitHub, Notion, Google, Slack, Salesforce, a math/weather demo) and wanted to connect them all to one orchestrating model. It's a solo project, built over Nov–Dec 2025, and it runs locally. One caveat: `mcp_config.py` starts `google_mail.py`, but that file was never committed, so Gmail doesn't work as the repo stands.

## Key Features

- **One chat, seven integrations**: GitHub, Notion, Slack, Gmail, Google Calendar, Salesforce and DuckDuckGo web search, each behind its own MCP server. (Gmail is missing its server file, see the note above.)
- **LLM tool routing**: a Llama 3.1 model on Groq classifies each message, picks the target service, decides whether a tool can do the job, then calls it through the tool-calling API and summarises the result.
- **Three-stage request pipeline**: a router stage, a capability gatekeeper and an execution stage, so the model only attempts actions it has tools for and says so when it doesn't.
- **OAuth 2.0 onboarding**: authorization-code flows for GitHub, Notion, Google, Slack and Salesforce. When you ask for a service you haven't connected, the app redirects you to log in and then sends you back to the chat.
- **Multi-account support**: you can connect more than one account per service. Read requests fan out across all your accounts in parallel, and write requests ask you which account to use.
- **Slash-command UI**: type `/` to open a service menu with example prompts for each integration.
- **Context picker for Notion**: before a Notion action runs, the app searches your workspace and lets you choose the page or database to work on.
- **Web search without keys**: DuckDuckGo search runs through a public MCP server, so it needs no API key.
- **Per-user accounts and chat history**: username/password signup with SHA-256 hashing and JWT sessions, persistent multi-session chat history, and create/delete chat management.
- **Internal platform tools**: a small built-in MCP server the model can call to list the available integrations or trigger an auth redirect mid-conversation.

## How It Works

### Frontend (React + Vite)

The client (`client/`) is a single-page React 18 app built with Vite, using `lucide-react` for icons and hand-written CSS for a glassmorphism look. It handles:

- The auth screen (signup/login) and JWT storage in `localStorage`.
- A chat composer with a `/` slash-command menu that lists the seven services and example prompts for each.
- Modals driven by the backend: account selection (when a write needs a specific account) and context selection (when Notion needs a target page).
- The chat history sidebar: new chat, switch chat, delete chat, over a small REST API.

All calls go to `http://localhost:3000/api/...` with a `Bearer` token header, so the backend has to stay on port 3000.

### Backend (FastAPI as an MCP client)

The server (`server/app/`) is a FastAPI app. On startup it initialises the AI engine and loads tool metadata, and on shutdown it closes every open MCP client. Routes are split into `auth` (signup, login, status, and the OAuth login/callback endpoints) and `chat` (the main `/api/chat` endpoint plus chat CRUD).

### The chat pipeline

A message to `/api/chat` goes through these stages:

1. **Route**: `route_query` sends the message (plus the last few turns of context) to `llama-3.1-8b-instant` with `temperature=0` and JSON output. It labels the message `NORMAL_CHAT` or `SERVICE_RELATED` and names the target service (github, notion, gmail, calendar, slack, web-search, salesforce, platform, or none).
2. **Normal chat**: if it's just conversation, the model answers directly with a short system prompt and the cleaned history. No tools are touched.
3. **Auth check**: if a service is targeted and you haven't connected it, the response carries a redirect URL to that service's OAuth login. Web search is skipped here because it needs no key.
4. **Gatekeeper**: `validate_tool_availability` shows the model the tool metadata for the targeted service and asks, in JSON, whether any tool can do the requested *action* and whether it is a READ or a WRITE. Missing parameters are allowed, and the execution stage fills them in later.
5. **Account selection**: for WRITE operations on a service with several accounts, the backend returns a `select_account` action so the UI can ask which account to use. For Notion, it returns a `select_context` action with a list of pages/databases from a live search.
6. **Execute**: the resolved MCP client lists its tools, and they're converted into Groq's tool-call schema (names sanitised, noisy fields like Notion `children`/`icon`/`cover` and Slack `cursor` stripped, schemas flattened). The model is called with `tool_choice="auto"`. Each tool call runs against the MCP server, or is fanned out across all accounts for multi-account reads.
7. **Summarise**: the tool results go back to the model for a final answer, which is saved to chat history and returned.

### MCP connection management

`mcp_manager.py` keeps one `fastmcp` client per user and reuses it when the active accounts and target service match, rebuilding it only when they change. `mcp_config.py` builds the spawn config for each server:

- **GitHub**: `npx @modelcontextprotocol/server-github`, authed with the user's token.
- **Notion**: `npx @notionhq/notion-mcp-server`.
- **Slack**: `npx @modelcontextprotocol/server-slack` (bot token + team ID).
- **Salesforce**: `npx @advanced-communities/salesforce-mcp-server` (OAuth access token + instance URL).
- **Web search**: `npx @oevortex/ddg_search` (DuckDuckGo, no key).
- **Google Mail / Calendar**: local Python MCP servers (`google_mail.py`, `google_calendar.py`) built with `fastmcp` and the Google API client, using the user's OAuth token. Only `google_calendar.py` is in the repo.
- **Platform**: a local `platform_manager.py` MCP server exposing `list_integrations` and `redirect_to_auth`.

### Auth and storage

`security.py` issues and verifies HS256 JWTs with a configurable expiry. If `JWT_SECRET` isn't set, `config.py` falls back to a default value. `auth.py` implements the OAuth authorization-code flow for all five external providers: it builds the consent URL, exchanges the code for an access token at the callback, fetches the account identity, saves the connection, and redirects back to the frontend with a fresh JWT. `storage.py` is a JSON-file store (`storage.json` for users/connections, `chat_history.json` for chats) with plain SHA-256 password hashing, multi-account connection records and light schema migration for older data. Tokens sit in that JSON file and CORS allows all origins, so this is meant for local use only.

## Tech Stack

- **Languages:** Python, JavaScript, CSS, HTML
- **Frontend:** React 18, Vite 5, lucide-react, hand-written glassmorphism CSS
- **Backend:** FastAPI, Uvicorn, Pydantic, httpx, PyJWT, python-dotenv
- **AI / orchestration:** Groq SDK with `llama-3.1-8b-instant`, Model Context Protocol via `fastmcp`
- **MCP servers:** `@modelcontextprotocol/server-github`, `@notionhq/notion-mcp-server`, `@modelcontextprotocol/server-slack`, `@advanced-communities/salesforce-mcp-server`, `@oevortex/ddg_search`, plus local Python servers for Google Calendar and platform management
- **Google APIs:** `google-auth`, `google-api-python-client` (Gmail + Calendar v3)
- **Storage:** flat JSON files (users, connections, chat history)

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm (also used to launch the JS MCP servers through `npx`)
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

There is no `requirements.txt`, so the `pip install` line lists the third-party packages the backend imports.

### Configure environment

Copy the template and fill in your credentials:

```bash
cd server
cp .env.template .env
```

`.env` keys (only app-level OAuth credentials live here; individual user tokens are stored after login):

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

Set `JWT_SECRET` yourself. When registering each OAuth app, point its redirect URI at `http://localhost:3000/auth/<service>/callback`.

### Running

```bash
# Backend (from server/)
uvicorn app.main:app --port 3000
# serves on http://localhost:3000

# Frontend (from client/)
npm run dev
# opens on http://localhost:5173
```

There is no `server/main.py` runner, so start the backend with `uvicorn` as above.

## Usage

1. Open `http://localhost:5173`, sign up, and log in.
2. Type `/` to see the service menu, or just write what you want. The first time you target a service you haven't connected, you'll be redirected to its OAuth login and returned to the chat afterwards.
3. Ask things like:
   - `Create a private repository named 'Project-X'`
   - `List my recently edited Notion pages`
   - `Send 'Finished the task' to #general`
   - `What's on my calendar today?`
   - `Search the web for the latest MCP news`
4. For write actions on a service with several connected accounts, you'll be asked to pick the account first. For Notion, you'll pick the target page. Read actions across multiple accounts run in parallel and the results come back grouped per account.

Gmail requests will fail until a `google_mail.py` server is added to `server/app/services/mcp_servers/`. The repo has no tests.

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
│   ├── .env.template                # OAuth + Groq + JWT config template
│   └── app/
│       ├── main.py                  # FastAPI app, lifespan, CORS, routers (run with uvicorn)
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
