from fastmcp import FastMCP

mcp = FastMCP("platform-manager")

@mcp.tool()
def redirect_to_auth(service: str) -> str:
    """
    Triggers an automatic login redirect for the specified service. 
    Supported services: github, notion, google, slack, salesforce
    """
    return f"AUTH_REDIR: {service.lower()}"

@mcp.tool()
def list_integrations() -> str:
    """
    List all available external services that can be connected.
    """
    return "Available services: GitHub, Notion, Google (Gmail & Drive), Slack, Salesforce."

if __name__ == "__main__":
    mcp.run()