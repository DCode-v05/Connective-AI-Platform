import os
import sys
from dotenv import load_dotenv

load_dotenv()

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVERS_DIR = os.path.join(CORE_DIR, "mcp_servers")

def get_mcp_config(connections):

    config = {
        "platform": {
            "command": sys.executable,
            "args": [os.path.join(SERVERS_DIR, "platform_manager.py")],
            "env": {}
        },
        "web-search": {
            "command": "npx",
            "args": ["-y", "@oevortex/ddg_search@latest"],
            "env": {}
        }
    }

    if "github" in connections:
        config["github"] = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": connections["github"]["token"]
            }
        }

    if "notion" in connections:
        config["notion"] = {
            "command": "npx",
            "args": ["-y", "@notionhq/notion-mcp-server"],
            "env": {
                "NOTION_TOKEN": connections["notion"]["token"]
            }
        }

    if "google" in connections:
        config["google-mail"] = {
            "command": sys.executable,
            "args": [os.path.join(SERVERS_DIR, "google_mail.py")],
            "env": {
                "GOOGLE_CLIENT_ID": os.environ.get("GOOGLE_CLIENT_ID"),
                "GOOGLE_CLIENT_SECRET": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "GOOGLE_USER_TOKEN": connections["google"]["token"]
            }
        }
        config["google-calendar"] = {
            "command": sys.executable,
            "args": [os.path.join(SERVERS_DIR, "google_calendar.py")],
            "env": {
                "GOOGLE_CLIENT_ID": os.environ.get("GOOGLE_CLIENT_ID"),
                "GOOGLE_CLIENT_SECRET": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "GOOGLE_USER_TOKEN": connections["google"]["token"]
            }
        }

    if "slack" in connections:
        config["slack"] = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-slack"],
            "env": {
                "SLACK_BOT_TOKEN": connections["slack"]["token"],
                "SLACK_TEAM_ID": connections["slack"].get("team_id", os.environ.get("SLACK_TEAM_ID"))
            }
        }

    if "salesforce" in connections:
        config["salesforce"] = {
            "command": "npx",
            "args": ["-y", "@advanced-communities/salesforce-mcp-server"],
            "env": {
                "SALESFORCE_AUTH_TYPE": "oauth",
                "SALESFORCE_ACCESS_TOKEN": connections["salesforce"]["token"],
                "SALESFORCE_INSTANCE_URL": connections["salesforce"]["instance_url"]
            }
        }


    return config