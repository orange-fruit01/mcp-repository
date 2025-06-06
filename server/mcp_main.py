from fastmcp import FastMCP
from competitor_analysis_agent import graph
from fastapi.responses import JSONResponse

mcp = FastMCP(name="MyServer")

def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

@mcp.tool(description="Greets the user with their name.")
def greet(name: str) -> JSONResponse:
    """
    Greets the user.

    Parameters:
    - name (str): The name of the user to greet.
    """
    response = JSONResponse(content={"message": f"Hello {name}!"})
    return add_cors_headers(response)

@mcp.tool(description="Performs a comprehensive social media competitor analysis.")
def competitor_analysis(company: str, industry: str, competitor: str) -> JSONResponse:
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
    response = JSONResponse(content=result)
    return add_cors_headers(response)

if __name__ == "__main__":
    mcp.run(transport="streamable-http",
            host="0.0.0.0",
            port=8000)
            