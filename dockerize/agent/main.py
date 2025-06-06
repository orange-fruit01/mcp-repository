from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import competitor_analysis_agent  # assuming your agent is saved as this filename

app = FastAPI(
    title="Competitor Analysis API",
    description="LangGraph-powered competitor analysis agent for MCP exposure.",
    version="1.0.0"
)

# Pydantic models for request/response validation
class CompetitorAnalysisRequest(BaseModel):
    company: str
    industry: str
    competitor: str

class CompetitorAnalysisResponse(BaseModel):
    report: str
    analysis_summary: str
    key_insights: List[str]

@app.post("/analyze", response_model=CompetitorAnalysisResponse)
def analyze(request: CompetitorAnalysisRequest):
    # Prepare input for the graph
    input_data = request.dict()
    try:
        # Call the LangGraph agent synchronously
        result = competitor_analysis_agent.graph.invoke(input_data)
        return CompetitorAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
