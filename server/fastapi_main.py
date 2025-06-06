from fastapi import FastAPI
from langserve import add_routes
from server.competitor_analysis_agent import graph  # Import your compiled graph
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Competitor Analysis API",
    description="LangGraph-powered competitor analysis agent for MCP exposure.",
    version="1.0.0"
)

# Expose the graph as a LangServe endpoint (enables /invoke, /stream, /batch, etc.)
add_routes(
    app,
    graph,
    path="/analyze",  # This will expose /analyze/invoke, /analyze/stream, etc.
    # Optionally, you can enable/disable endpoints:
    # enabled_endpoints=["invoke", "stream", "batch", "playground"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)