from fastmcp import FastMCP

mcp = FastMCP(name="MyServer")

@mcp.tool(description="Greets the user with their name.")
def greet(name: str) -> str:
    """
    Greets the user.

    Parameters:
    - name (str): The name of the user to greet.
    """
    return f"Hello {name}!"

@mcp.tool(description="Provides the weather for a given city.")
def get_weather(city: str) -> str:
    """
    Provides the weather for a city.

    Parameters:
    - city (str): The city to get the weather for.
    """
    return f"The weather in {city} is sunny."

@mcp.tool(description="Gives news about a specific topic.")
def get_news(topic: str) -> str:
    """
    Provides news about a topic.

    Parameters:
    - topic (str): The topic to get news about.
    """
    return f"The news about {topic} is that it is a good day."

@mcp.tool(description="Gives a summary of a given transcript.")
def get_summary(transcript: str) -> str:
    """
    Provides a summary of a transcript.

    Parameters:
    - transcript (str): The transcript to summarize.
    """
    return f"The summary of the transcript is that it is a good day."

if __name__ == "__main__":
    mcp.run(transport="streamable-http",
            host="0.0.0.0",
            port=8000)
            