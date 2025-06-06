from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
import requests
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# --- Config ---
load_dotenv()
# Database configuration
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD").replace("@", "%40")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

# Default access token
long_user_access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")

# Define input schema
class ScraperInput(TypedDict):
    post_limit: int
    comment_limit: int

# Define output schema
class ScraperOutput(TypedDict):
    posts_scraped: int
    comments_scraped: int
    posts_data: list[dict]
    comments_data: list[dict]
    status: str
    message: str

# Combined state for internal processing
class ScraperState(ScraperInput, ScraperOutput):
    access_token: str
    raw_posts_data: dict
    processed_posts_df: pd.DataFrame
    processed_comments_df: pd.DataFrame
    db_engine: object

# --- Node 1: Initialize ---
def initialize_scraper(state: ScraperInput) -> dict:
    post_limit = state.get("post_limit", 5)
    comment_limit = state.get("comment_limit", 5)
    try:
        engine = create_engine(
            f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
        with engine.connect() as connection:
            connection.execute(text("SELECT version();"))
        return {
            "post_limit": post_limit,
            "comment_limit": comment_limit,
            "access_token": long_user_access_token,
            "db_engine": engine,
            "status": "initialized",
            "message": "Scraper initialized successfully"
        }
    except Exception as e:
        return {
            "post_limit": post_limit,
            "comment_limit": comment_limit,
            "access_token": long_user_access_token,
            "db_engine": None,
            "status": "error",
            "message": f"Database connection failed: {str(e)}"
        }

# --- Node 2: Fetch Instagram posts and comments ---
def fetch_instagram_posts(state: ScraperState) -> dict:
    access_token = state["access_token"]
    post_limit = state["post_limit"]
    comment_limit = state["comment_limit"]
    # Fetch posts
    media_url = "https://graph.instagram.com/me/media"
    media_params = {
        "fields": "id,caption,like_count,comments_count,timestamp",
        "access_token": access_token,
        "limit": post_limit
    }
    try:
        media_response = requests.get(media_url, params=media_params)
        media_response.raise_for_status()
        media_list = media_response.json().get("data", [])
        # For each post, fetch comments (up to comment_limit)
        for media in media_list:
            media_id = media["id"]
            comments_url = f"https://graph.instagram.com/{media_id}/comments"
            comments_params = {
                "fields": "id,username,text,timestamp",
                "access_token": access_token,
                "limit": comment_limit
            }
            comments_response = requests.get(comments_url, params=comments_params)
            comments_response.raise_for_status()
            comments_data = comments_response.json().get("data", [])
            media["comments_data"] = comments_data
        return {
            "raw_posts_data": {"data": media_list},
            "status": "posts_fetched",
            "message": f"Successfully fetched {len(media_list)} posts"
        }
    except Exception as e:
        return {
            "raw_posts_data": {},
            "status": "error",
            "message": f"Failed to fetch posts: {str(e)}"
        }

# --- Node 3: Process posts ---
def process_posts_data(state: ScraperState) -> dict:
    try:
        if not state.get("raw_posts_data") or "data" not in state["raw_posts_data"]:
            return {
                "processed_posts_df": pd.DataFrame(),
                "status": "error",
                "message": "No posts data to process"
            }
        data = state["raw_posts_data"]
        df_main = pd.DataFrame(data["data"])
        if df_main.empty:
            return {
                "processed_posts_df": pd.DataFrame(),
                "posts_scraped": 0,
                "posts_data": [],
                "status": "success",
                "message": "No posts found"
            }
        # Extract and map fields
        df_posts_db = pd.DataFrame()
        df_posts_db["user_id"] = 1
        df_posts_db["agent_id"] = 3
        df_posts_db["post_url"] = "https://www.instagram.com/p/" + df_main["id"].astype(str)
        df_posts_db["platform"] = "instagram"
        df_posts_db["post_id"] = df_main["id"].astype(str)
        df_posts_db["post_caption"] = df_main["caption"].fillna("").astype(str) if "caption" in df_main else ""
        df_posts_db["time_stamp"] = df_main["timestamp"] if "timestamp" in df_main else ""
        df_posts_db["total_likes"] = df_main["like_count"] if "like_count" in df_main else 0
        df_posts_db["total_comments"] = df_main["comments_count"] if "comments_count" in df_main else 0
        df_posts_db["total_shares"] = 0  # Instagram API does not provide shares
        return {
            "processed_posts_df": df_posts_db,
            "posts_scraped": len(df_posts_db),
            "posts_data": df_posts_db.to_dict('records'),
            "status": "posts_processed",
            "message": f"Successfully processed {len(df_posts_db)} posts"
        }
    except Exception as e:
        return {
            "processed_posts_df": pd.DataFrame(),
            "posts_scraped": 0,
            "posts_data": [],
            "status": "error",
            "message": f"Failed to process posts: {str(e)}"
        }

# --- Node 4: Process comments ---
def process_comments_data(state: ScraperState) -> dict:
    try:
        if not state.get("raw_posts_data") or "data" not in state["raw_posts_data"]:
            return {
                "processed_comments_df": pd.DataFrame(),
                "comments_scraped": 0,
                "comments_data": [],
                "status": "error",
                "message": "No posts data available for comment processing"
            }
        data = state["raw_posts_data"]
        comments_list = []
        for post in data["data"]:
            post_id = post["id"]
            for comment in post.get("comments_data", []):
                comments_list.append({
                    "post_id": post_id,
                    "comment_id": comment.get("id"),
                    "comment_message": comment.get("text"),
                    "comment_time": comment.get("timestamp"),
                    "commenter": comment.get("username")
                })
        df_comments = pd.DataFrame(comments_list)
        return {
            "processed_comments_df": df_comments,
            "comments_scraped": len(df_comments),
            "comments_data": df_comments.to_dict('records') if not df_comments.empty else [],
            "status": "comments_processed",
            "message": f"Successfully processed {len(df_comments)} comments"
        }
    except Exception as e:
        return {
            "processed_comments_df": pd.DataFrame(),
            "comments_scraped": 0,
            "comments_data": [],
            "status": "error",
            "message": f"Failed to process comments: {str(e)}"
        }

# --- Node 5: Save to database ---
def save_to_database(state: ScraperState) -> dict:
    try:
        if state.get("db_engine") is None:
            return {
                "status": "error",
                "message": "Database connection not available"
            }
        # Save posts data
        if not state.get("processed_posts_df", pd.DataFrame()).empty:
            state["processed_posts_df"].to_sql(
                'social_media_scraped_data_stg',
                state["db_engine"],
                if_exists='replace',
                index=False
            )
            print(f"✅ Saved {len(state['processed_posts_df'])} posts to database")
            #Delete existing data
            sql_delete = """DELETE FROM social_media_scraped_data 
            USING social_media_scraped_data_stg WHERE social_media_scraped_data.post_id = social_media_scraped_data_stg.post_id;"""

            with state["db_engine"].connect() as connection:
                trans = connection.begin()
                connection.execute(text(sql_delete))
                trans.commit()
                print("✅ Deleted existing data from social_media_scraped_data")

            # Save to social_media_scraped_data table --Final step
            columns_post = list(state["processed_posts_df"].columns)
            headers_post = ", ".join([f"{i}" for i in columns_post])

            sql = f"""INSERT INTO social_media_scraped_data ({headers_post})
                            SELECT {headers_post} FROM social_media_scraped_data_stg;"""

            with state["db_engine"].connect() as connection:
                trans = connection.begin()
                connection.execute(text(sql))

                connection.execute(text("DROP TABLE social_media_scraped_data_stg;"))
                trans.commit()
                print("✅ Inserted data into social_media_scraped_data")

            
        # Save comments data
        if not state.get("processed_comments_df", pd.DataFrame()).empty:
            state["processed_comments_df"].to_sql(
                'social_media_scraped_data_comments_stg',
                state["db_engine"],
                if_exists='replace',
                index=False
            )
            print(f"✅ Saved {len(state['processed_comments_df'])} comments to database")
            # Delete existing data
            sql_delete = """DELETE FROM social_media_scraped_data_comments 
            USING social_media_scraped_data_comments_stg 
            WHERE social_media_scraped_data_comments.post_id = social_media_scraped_data_comments_stg.post_id
            AND social_media_scraped_data_comments.comment_id = social_media_scraped_data_comments_stg.comment_id;"""

            with state["db_engine"].connect() as connection:
                trans = connection.begin()
                connection.execute(text(sql_delete))
                trans.commit()
                print("✅ Deleted data from social_media_scraped_data_comments")

            # Insert to social_media_scraped_data_comments table --Final step
            columns_comments = list(state["processed_comments_df"].columns)
            headers_comments = ", ".join([f"{i}" for i in columns_comments])

            sql = f"""INSERT INTO social_media_scraped_data_comments ({headers_comments})
                            SELECT {headers_comments} FROM social_media_scraped_data_comments_stg;"""
            with state["db_engine"].connect() as connection:
                trans = connection.begin()
                connection.execute(text(sql))

                connection.execute(text("DROP TABLE social_media_scraped_data_comments_stg;"))
                trans.commit()
                print("✅ Inserted data into social_media_scraped_data_comments")

        return {
            "status": "success",
            "message": f"Successfully saved {state.get('posts_scraped', 0)} posts and {state.get('comments_scraped', 0)} comments to database"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to save to database: {str(e)}"
        }

# --- Node 6: Finalize ---
def finalize_results(state: ScraperState) -> dict:
    return {
        "posts_scraped": state.get("posts_scraped", 0),
        "comments_scraped": state.get("comments_scraped", 0),
        "posts_data": state.get("posts_data", []),
        "comments_data": state.get("comments_data", []),
        "status": state.get("status", "completed"),
        "message": state.get("message", "Scraping completed")
    }

# --- Build the graph ---
builder = StateGraph(
    ScraperState,
    input=ScraperInput,
    output=ScraperOutput
)
builder.add_node("initialize", initialize_scraper)
builder.add_node("fetch_posts", fetch_instagram_posts)
builder.add_node("process_posts", process_posts_data)
builder.add_node("process_comments", process_comments_data)
builder.add_node("save_to_db", save_to_database)
builder.add_node("finalize", finalize_results)
builder.add_edge(START, "initialize")
builder.add_edge("initialize", "fetch_posts")
builder.add_edge("fetch_posts", "process_posts")
builder.add_edge("process_posts", "process_comments")
builder.add_edge("process_comments", "save_to_db")
builder.add_edge("save_to_db", "finalize")
builder.add_edge("finalize", END)
graph = builder.compile()

# if __name__ == "__main__":
#     print("Instagram Social Media Scraper Agent (local mode)")
#     try:
#         post_limit = int(input("Enter post limit (default 5): ") or "5")
#     except ValueError:
#         post_limit = 5
#     try:
#         comment_limit = int(input("Enter comment limit (default 5): ") or "5")
#     except ValueError:
#         comment_limit = 5
#     scraper_input = {
#         "post_limit": post_limit,
#         "comment_limit": comment_limit
#     }
#     try:
#         result = graph.invoke(scraper_input)
#         print("\n" + "="*50)
#         print("SCRAPING RESULTS")
#         print("="*50)
#         print(f"Status: {result['status']}")
#         print(f"Message: {result['message']}")
#         print(f"Posts scraped: {result['posts_scraped']}")
#         print(f"Comments scraped: {result['comments_scraped']}")
#     except Exception as e:
#         print(f"\n❌ Error running scraper: {str(e)}")
