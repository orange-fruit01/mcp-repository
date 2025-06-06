# AI Agents Collection

This repository contains multiple AI agents built with LangGraph and exposed via MCP (Model Context Protocol).

## Available Agents

### 1. Documentation Assistant
- **Path**: `agent/documentation_assistant.py`
- **Description**: An AI assistant that answers documentation questions with confidence scoring and source attribution
- **Input**: 
  - `question` (str): The question to ask
  - `context` (str): Optional context for the question
- **Output**:
  - `answer` (str): The AI's response
  - `sources_used` (list[str]): Sources used for the answer

### 2. Facebook Agent
- **Path**: `agent/facebook_agent.py`
- **Description**: An agent that retrieves Facebook user information using the Graph API
- **Requirements**: `FACEBOOK_ACCESS_TOKEN` environment variable
- **Input**: `{"request_type": "user_info"}`
- **Output**: User data with success/error status

### 3. Competitor Analysis Agent
- **Path**: `agent/competitor_analysis_agent.py`
- **Description**: An AI agent that performs comprehensive social media competitor analysis
- **Requirements**: `OPENROUTER_API_KEY` environment variable
- **Input**:
  - `company` (str): Your company name
  - `industry` (str): The industry you operate in
  - `competitor` (str): The competitor to analyze
- **Output**:
  - `report` (str): Comprehensive analysis report
  - `analysis_summary` (str): Executive summary
  - `key_insights` (list[str]): Key findings from the analysis

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your API keys:
   ```
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   FACEBOOK_ACCESS_TOKEN=your_facebook_access_token_here
   ```

3. The agents are configured in `langgraph.json` and can be accessed via MCP tools.

## Competitor Analysis Agent Features

The competitor analysis agent performs a comprehensive 8-step analysis:

1. **Platform Identification**: Identifies relevant social media platforms for the industry
2. **Social Media Presence Analysis**: Analyzes the competitor's presence across platforms
3. **Content Strategy Analysis**: Examines content themes, posting patterns, and storytelling approach
4. **Engagement Metrics Analysis**: Studies audience interaction and community building
5. **Competitor Profiling**: Creates a comprehensive social media profile
6. **Competitive Advantage Analysis**: Identifies strengths and weaknesses vs your company
7. **Strategy Recommendations**: Provides actionable recommendations organized by timeline
8. **Report Generation**: Compiles everything into a structured report

The analysis covers:
- Platform usage and posting frequency
- Content types and themes
- Engagement rates and audience response
- Brand voice and visual identity
- Community management strategies
- Growth metrics and trends
- Strategic recommendations for competitive positioning

## Usage via MCP

When using these agents through MCP tools, they will be available as functions that you can call with the specified input parameters and will return the structured output as defined in each agent's schema. 