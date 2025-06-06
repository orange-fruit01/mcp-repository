FROM langchain/langgraph-api:3.11



RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -c /api/constraints.txt langgraph>=0.2.40 langgraph-api>=0.2.3 langgraph-sdk>=0.1.61 langchain-openai>=0.2.0 langchain-core>=0.3.0 typing-extensions>=4.8.0 httpx python-dotenv openai mcp langchain-mcp-adapters pandas sqlalchemy requests psycopg2-binary

# -- Installing local requirements --
ADD requirements.txt /deps/__outer_dev-justin/src/requirements.txt
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -c /api/constraints.txt -r /deps/__outer_dev-justin/src/requirements.txt
# -- End of local requirements install --

# -- Adding non-package dependency dev-justin --
ADD . /deps/__outer_dev-justin/src
RUN set -ex && \
    for line in '[project]' \
                'name = "dev-justin"' \
                'version = "0.1"' \
                '[tool.setuptools.package-data]' \
                '"*" = ["**/*"]'; do \
        echo "$line" >> /deps/__outer_dev-justin/pyproject.toml; \
    done
# -- End of non-package dependency dev-justin --

# -- Installing all local dependencies --
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -c /api/constraints.txt -e /deps/*
# -- End of local dependencies install --
ENV LANGSERVE_GRAPHS='{"competitor_analysis_agent": {"path": "/deps/__outer_dev-justin/src/agent/competitor_analysis_agent.py:graph", "description": "An AI agent that performs comprehensive social media competitor analysis, analyzing platform presence, content strategy, engagement metrics, and providing strategic recommendations"}, "facebook_scraper_agent": {"path": "/deps/__outer_dev-justin/src/agent/facebook_scraper.py:graph", "description": "A social media scraper that scrapes Facebook posts and comments using the Graph API"}, "instagram_scraper_agent": {"path": "/deps/__outer_dev-justin/src/agent/instagram_scraper.py:graph", "description": "A social media scraper that scrapes Instagram posts and comments using the Graph API"}, "facebook_sentiment_analysis_agent": {"path": "/deps/__outer_dev-justin/src/agent/facebook_sentimentAnalysis.py:graph", "description": "A social media sentiment analysis agent that analyzes Facebook posts and comments using the OpenRouter API"}, "instagram_sentiment_analysis_agent": {"path": "/deps/__outer_dev-justin/src/agent/instagram_sentimentAnalysis.py:graph", "description": "A social media sentiment analysis agent that analyzes Instagram posts and comments using the OpenRouter API"}}'



WORKDIR /deps/__outer_dev-justin/src