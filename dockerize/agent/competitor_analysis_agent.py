# competitor_analysis_agent.py - Competitor Analysis Agent for MCP exposure
import os
import json
from typing import TypedDict, Optional, List, Dict
from typing_extensions import Annotated
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from openai import OpenAI
import operator
import pandas as pd
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

# API settings for OpenRouter with sonar-reasoning model
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "perplexity/sonar-reasoning"  # Using the sonar-reasoning model as specified



# Database configuration
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD").replace("@", "%40")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

# Create OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Define clear input schema for MCP exposure
class AgentInput(TypedDict):
    """Input schema for the competitor analysis agent."""
    company: str
    industry: str
    competitor: str

# Define clear output schema for MCP exposure  
class AgentOutput(TypedDict):
    """Output schema for the competitor analysis agent."""
    report: str
    analysis_summary: str
    key_insights: List[str]

# Combined state for internal processing
class AgentState(AgentInput, AgentOutput):
    pass

def insert_competitor_analysis_report(company: str, industry: str, competitor: str, report: str):
    """Insert a competitor analysis report into the database."""
    try:
        engine = create_engine(
            f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
        # Prepare the data as a DataFrame
        df = pd.DataFrame([
            {
                "company": company,
                "industry": industry,
                "competitor": competitor,
                "report": report
            }
        ])
        # Insert into the table (create if not exists)
        df.to_sql(
            'social_media_competitor_analysis_logs',
            engine,
            if_exists='append',
            index=False
        )
        print(f"✅ Competitor analysis report inserted for {company} vs {competitor}")
    except Exception as e:
        print(f"❌ Failed to insert competitor analysis report: {str(e)}")

# --- Single Comprehensive Analysis Node ---
def comprehensive_analysis_node(state: AgentState) -> dict:
    """Perform complete competitor analysis in a single comprehensive call."""
    
    prompt = f"""
    Conduct a comprehensive social media competitor analysis of {state['competitor']} for {state['company']} in the {state['industry']} industry.

    Provide a detailed analysis covering ALL of the following areas:

    ## 1. PLATFORM IDENTIFICATION & PRESENCE
    - Identify the most relevant social media platforms for this industry
    - Analyze {state['competitor']}'s presence on each platform (followers, posting frequency, verification status)
    - Rank platform importance and effectiveness for this competitor

    ## 2. SOCIAL MEDIA PRESENCE ANALYSIS
    - Account sizes and growth trends across platforms
    - Posting frequency and timing patterns
    - Visual identity and brand consistency
    - Content formats and types used

    ## 3. CONTENT STRATEGY ANALYSIS
    - Main content pillars and themes
    - Content calendar patterns and seasonal strategies
    - Brand voice, tone, and storytelling approach
    - Balance of promotional vs. value-based content
    - Top-performing content types and examples

    ## 4. ENGAGEMENT METRICS & COMMUNITY
    - Average engagement rates by platform and content type
    - Audience response patterns and sentiment
    - Community management approach
    - Customer service on social platforms
    - User-generated content and advocacy

    ## 5. COMPETITIVE POSITIONING
    - {state['competitor']}'s social media strengths and weaknesses
    - How {state['company']} can differentiate on social platforms
    - Content gaps and underserved audience segments
    - Platform-specific opportunities for {state['company']}

    ## 6. STRATEGIC RECOMMENDATIONS
    Provide actionable recommendations organized by timeline:
    - Quick wins (implementable within days)
    - Short-term tactics (1-3 months)
    - Medium-term initiatives (3-6 months)
    - Long-term strategic positioning (6+ months)

    ## 7. MONITORING FRAMEWORK
    - Key metrics to track for ongoing competitive intelligence
    - Social listening priorities and keywords
    - Frequency and methods for monitoring competitor activities

    Format your response as a comprehensive report with clear headings, bullet points, and specific actionable insights. Include numerical data and metrics wherever possible. Base your analysis on the most current information available.
    """
    
    messages = [
        {
            "role": "system", 
            "content": "You are an expert social media competitive intelligence analyst with deep knowledge of platform strategies, content marketing, and digital engagement across industries. Provide comprehensive, data-driven analysis with specific actionable recommendations."
        },
        {"role": "user", "content": prompt}
    ]
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=6000  # Increased token limit for comprehensive analysis
    )
    
    report_content = response.choices[0].message.content
    
    # Extract key insights from the comprehensive analysis
    key_insights = []
    try:
        # Look for key insight indicators in the response
        lines = report_content.lower().split('\n')
        insight_keywords = ['strength', 'weakness', 'opportunity', 'threat', 'advantage', 'gap', 'recommendation']
        
        for line in lines:
            for keyword in insight_keywords:
                if keyword in line and len(line.strip()) > 20 and len(line.strip()) < 150:
                    # Clean up the line and add as insight
                    clean_line = line.strip('- •*').strip()
                    if clean_line and clean_line not in key_insights:
                        key_insights.append(clean_line.capitalize())
                        if len(key_insights) >= 5:  # Limit to top 5 insights
                            break
            if len(key_insights) >= 5:
                break
                
        # Fallback insights if extraction doesn't work well
        if len(key_insights) < 3:
            key_insights = [
                f"Comprehensive social media analysis of {state['competitor']} completed",
                f"Platform presence and content strategy evaluated for {state['industry']} industry",
                f"Strategic recommendations developed for {state['company']}'s competitive positioning",
                "Engagement metrics and community building approaches analyzed",
                "Monitoring framework established for ongoing competitive intelligence"
            ]
    except Exception:
        key_insights = [
            f"Comprehensive competitor analysis of {state['competitor']} completed",
            f"Social media strategy insights generated for {state['company']}",
            "Actionable recommendations provided across multiple timeframes"
        ]
    
    # Create analysis summary
    analysis_summary = f"Completed comprehensive social media competitive analysis of {state['competitor']} in the {state['industry']} industry for {state['company']}. Analysis covered platform presence, content strategy, engagement metrics, competitive positioning, and strategic recommendations with actionable timelines."
    
    # Insert the report into the database
    insert_competitor_analysis_report(
        state['company'],
        state['industry'],
        state['competitor'],
        report_content
    )

    return {
        "report": report_content,
        "analysis_summary": analysis_summary,
        "key_insights": key_insights[:5]  # Limit to top 5 insights
    }

# Build the simplified graph with explicit input/output schemas
builder = StateGraph(
    AgentState,
    input=AgentInput,  # This defines what the MCP tool expects
    output=AgentOutput  # This defines what the MCP tool returns
)

# Add single comprehensive analysis node
builder.add_node("comprehensive_analysis", comprehensive_analysis_node)

# Add simple edges - just start -> analysis -> end
builder.add_edge(START, "comprehensive_analysis")
builder.add_edge("comprehensive_analysis", END)

# Compile the graph
graph = builder.compile() 

# # --- Local runner for testing ---
# def main():
#     """Run a sample competitor analysis locally for testing purposes."""
#     sample_input = {
#         "company": "SM Development Corporation",
#         "industry": "Real Estate",
#         "competitor": "Double Dragon Corporation"
#     }
#     print("Running competitor analysis for sample input:\n", sample_input)
#     # Run the graph synchronously
#     result = graph.invoke(sample_input)
#     print("\n--- Analysis Output ---\n")
#     for k, v in result.items():
#         print(f"{k}:\n{v}\n{'-'*40}")

# if __name__ == "__main__":
#     main() 

