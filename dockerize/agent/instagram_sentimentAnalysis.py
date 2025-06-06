import os
import json
import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from datetime import datetime

# --- Config ---
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD").replace("@", "%40")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- Sentiment analysis helper function ---
def analyze_sentiment(text_data, label):
    openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = (
        "Sentiment Analysis Agent\n"
        "You monitor audience sentiment around a brand and products on social media. "
        "Given the following batch of user texts (comments and messages), write a concise, executive-style sentiment analysis report in markdown.\n\n"
        "Highlight:\n"
        "- The overall sentiment (Positive/Negative/Neutral, with a score from 0 to 100)\n"
        "- Key positive trends and opportunities\n"
        "- Key negative trends and potential issues\n"
        "- Mention any outliers or notable themes\n"
        "- Suggest any recommended actions if relevant\n"
        f"\nContext: This data is from {label}.\n"
        "\nData:\n"
        + json.dumps(text_data, ensure_ascii=False, indent=2) +
        "\n\nReturn only a markdown report suitable for management (do not return a JSON or table)."
    )
    body = {
        "model": "openai/gpt-4.1-mini",
        "messages": [
            {"role": "system", "content": "You are a professional social media sentiment analysis agent."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(openrouter_url, headers=headers, json=body)
    response.raise_for_status()
    reply = response.json()
    return reply['choices'][0]['message']['content']

# --- LangGraph State ---
class SentimentInput(TypedDict):
    pass  # No input needed

class SentimentOutput(TypedDict):
    num_reports: int
    status: str
    message: str

class SentimentState(SentimentInput, SentimentOutput):
    db_engine: object
    comments_df: pd.DataFrame
    reports: list[dict]

# --- Node 1: Initialize ---
def initialize_sentiment(state: SentimentInput) -> dict:
    try:
        engine = create_engine(
            f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
        with engine.connect() as connection:
            connection.execute(text("SELECT version();"))
        return {
            "db_engine": engine,
            "status": "initialized",
            "message": "Connected to database"
        }
    except Exception as e:
        return {
            "db_engine": None,
            "status": "error",
            "message": f"Database connection failed: {str(e)}"
        }

# --- Node 2: Fetch comments from DB ---
def fetch_comments_from_db(state: SentimentState) -> dict:
    try:
        engine = state["db_engine"]
        query = text("SELECT * FROM social_media_scraped_data WHERE platform = :platform")
        df = pd.read_sql_query(query, engine, params={"platform": "instagram"})
        return {
            "comments_df": df,
            "status": "comments_fetched",
            "message": f"Fetched {len(df)} comments from DB (platform=instagram)"
        }
    except Exception as e:
        return {
            "comments_df": pd.DataFrame(),
            "status": "error",
            "message": f"Failed to fetch comments: {str(e)}"
        }

# --- Node 3: Analyze sentiment and insert into DB ---
def analyze_and_insert_sentiment(state: SentimentState) -> dict:
    try:
        engine = state["db_engine"]
        df = state["comments_df"]
        if df.empty:
            return {"reports": [], "num_reports": 0, "status": "success", "message": "No comments to analyze"}
        grouped = df.groupby("post_id")
        reports = []
        for post_id, group in grouped:
            post_url = group["post_id"].iloc[0]
            platform = "instagram"
            user_id = 1
            num_comments = len(group)
            num_posts = 1
            comment_data = [
                {"username": row.get("commenter", "unknown"), "text": row.get("comment_message", "")}
                for _, row in group.iterrows()
            ]
            output = analyze_sentiment(comment_data, f"Comments on Post ID {post_id}")
            now = datetime.utcnow()
            report_row = {
                "user_id": user_id,
                "post_id": post_id,
                "post_url": f"https://www.instagram.com/p/{post_id}",
                "num_posts": num_posts,
                "num_comments": num_comments,
                "output": output,
                "notes": None,
                "platform": platform,
                "created_at": now,
                "updated_at": now
            }
            # Insert into DB
            pd.DataFrame([report_row]).to_sql(
                'social_media_sentiment_analysis_logs',
                engine,
                if_exists='append',
                index=False
            )
            reports.append(report_row)
        return {
            "reports": reports,
            "num_reports": len(reports),
            "status": "success",
            "message": f"Inserted {len(reports)} sentiment reports into DB"
        }
    except Exception as e:
        return {
            "reports": [],
            "num_reports": 0,
            "status": "error",
            "message": f"Failed to analyze/insert: {str(e)}"
        }

# --- Node 4: Finalize ---
def finalize_sentiment(state: SentimentState) -> dict:
    return {
        "num_reports": state.get("num_reports", 0),
        "status": state.get("status", "completed"),
        "message": state.get("message", "Sentiment analysis completed")
    }

# --- Build the graph ---
builder = StateGraph(
    SentimentState,
    input=SentimentInput,
    output=SentimentOutput
)
builder.add_node("initialize", initialize_sentiment)
builder.add_node("fetch_comments", fetch_comments_from_db)
builder.add_node("analyze_and_insert", analyze_and_insert_sentiment)
builder.add_node("finalize", finalize_sentiment)
builder.add_edge(START, "initialize")
builder.add_edge("initialize", "fetch_comments")
builder.add_edge("fetch_comments", "analyze_and_insert")
builder.add_edge("analyze_and_insert", "finalize")
builder.add_edge("finalize", END)
graph = builder.compile()

# if __name__ == "__main__":
#     print("Instagram Sentiment Analysis Agent (local mode)")
#     try:
#         result = graph.invoke({})
#         print("\n" + "="*50)
#         print("SENTIMENT ANALYSIS RESULTS")
#         print("="*50)
#         print(f"Status: {result['status']}")
#         print(f"Message: {result['message']}")
#         print(f"Number of reports: {result['num_reports']}")
#     except Exception as e:
#         print(f"\n❌ Error running sentiment analysis: {str(e)}") 