from fastmcp import FastMCP
from competitor_analysis_agent import graph

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
    mcp.run(transport="streamable-http",
            host="0.0.0.0",
            port=8000)
            