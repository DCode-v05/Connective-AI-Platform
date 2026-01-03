# Connective AI Platform

## Project Description
Connective AI Platform is a sophisticated multi-tool AI chat application that acts as a central hub (or "Connective" tissue) between a user, the Gemini AI model, and various external services using the **Model Context Protocol (MCP)**. It currently integrates **GitHub** (via SSE) and **Notion** (via Stdio), allowing users to interact with their codebases and knowledge bases seamlessly through a unified, modern chat interface powered by **Google's Gemini 2.0 Flash** model.

---

## Project Details

### Problem Statement
Developers and teams often struggle with data fragmentation across different platforms—code lives in GitHub, while documentation and wikis reside in Notion. switching contexts to retrieve information or perform actions is inefficient. This project solves this by providing a single natural language interface that can "talk" to both platforms simultaneously, orchestrating complex workflows that involve both code and documentation.

### Key Features
- **Unified Chat Interface**: A single window to interact with multiple distinct data sources.
- **Dual MCP Integration**:
  - **GitHub MCP**: Connects via Server-Sent Events (SSE) to search repositories, read code, and manage issues.
  - **Notion MCP**: Connects via Stdio to search pages and read content.
- **Intelligent Orchestration**: Uses `gemini-2.0-flash-exp` to intelligently route user queries to the appropriate tool (or both) and synthesize the results.
- **Modern UI**: Features a sleek, responsive Glassmorphism design with continuous chat history and Markdown rendering.

### Architecture
- **Backend**: A specialized MCP Client built with **FastAPI** that manages connections to multiple MCP servers and handles the OAuth/Token authentication flows.
- **Frontend**: A **React + Vite** application that provides a rich user experience, communicating with the backend via REST API.
- **AI Engine**: Deep integration with Google's Generative AI SDK for tool calling and reasoning.

---

## Tech Stack
- **Frontend**:
  - React.js
  - Vite
  - Vanilla CSS (Glassmorphism Design)
- **Backend**:
  - Python 3.x
  - FastAPI
  - Google Generative AI (Gemini 2.0 Flash)
  - Model Context Protocol (MCP) SDK
- **MCP Servers**:
  - `mcp-server-github` (Docker integration capable)
  - `mcp-server-notion`

---

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/DCode-v05/Connective-AI-Platform.git
cd Connective-AI-Platform
```

### 2. Configure Environment Variables
Navigate to the `server/` directory and create your `.env` file:
```bash
cd server
cp .env.template .env
```
Fill in the following keys in `.env`:
- `GEMINI_API_KEY`: Your Google GenAI API key.
- `GITHUB_MCP_PAT`: Your Personal Access Token for GitHub.
- `NOTION_TOKEN`: Your Notion Integration Token.

### 3. Install dependencies
**Server:**
```bash
cd server
pip install -r requirements.txt
```

**Client:**
```bash
cd ../client
npm install
```

### 4. Run the Application
**Start the Backend:**
```bash
# In the server/ directory
python main.py
```
_The server runs on http://localhost:3000_

**Start the Frontend:**
```bash
# In the client/ directory
npm run dev
```
_Open the URL shown (usually http://localhost:5173)_

---

## Usage
1.  Open the web interface at `http://localhost:5173`.
2.  Type a query like "Summarize the latest changes in the main branch of my repo" or "Find the Notion page about Q3 Goals".
3.  The agent will identify the correct tool, fetch the data, and provide a synthesized answer.

---

## Project Structure
```
Connective-AI-Platform/
│
├── client/                 # Frontend React Application
│   ├── src/                # Source code (Components, Styles)
│   ├── public/             # Static assets
│   ├── package.json        # Frontend dependencies
│   └── vite.config.js      # Vite configuration
│
├── server/                 # Backend FastAPI Application
│   ├── app/                # Application logic
│   │   ├── api/            # API Routers (Auth, Chat)
│   │   ├── core/           # Config and Settings
│   │   ├── services/       # MCP Manager and AI Engine
│   │   └── main.py         # Entry point
│   ├── main.py             # Server runner
│   ├── requirements.txt    # Backend dependencies
│   └── .env.template       # Environment variable template
│
└── README.md               # Project documentation
```

---

## Contributing

Contributions are welcome! To contribute:
1. Fork the repository
2. Create a new branch:
   ```bash
   git checkout -b feature/your-feature
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add your feature"
   ```
4. Push to your branch:
   ```bash
   git push origin feature/your-feature
   ```
5. Open a pull request describing your changes.

---

## Contact
- **GitHub:** [DCode-v05](https://github.com/DCode-v05)
- **Email:** denistanb05@gmail.com
