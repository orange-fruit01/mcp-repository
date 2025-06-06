from fastmcp import FastMCP
from competitor_analysis_agent import graph
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# Allow all origins (not recommended for production)
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

mcp = FastMCP(name="MyServer")

@mcp.tool(description="Greets the user with their name.")
def greet(name: str) -> str:
    """
    Greets the user.

    Parameters:
    - name (str): The name of the user to greet.
    """
    return f"Hello {name}!"

@mcp.tool(description="Performs a comprehensive social media competitor analysis.")
def competitor_analysis(company: str, industry: str, competitor: str) -> dict:
    """
    Performs a comprehensive social media competitor analysis using the competitor_analysis_agent.

    Parameters:
    - company (str): The name of the company requesting the analysis.
    - industry (str): The industry of the company.
    - competitor (str): The competitor to analyze.

    Returns:
    - dict: Contains 'report', 'analysis_summary', and 'key_insights'.
    """
    result = graph.invoke({
        "company": company,
        "industry": industry,
        "competitor": competitor
    })
    return result

if __name__ == "__main__":
    import uvicorn

    http_app = mcp.http_app(middleware=middleware)

    uvicorn.run(http_app, host="0.0.0.0", port=8000)