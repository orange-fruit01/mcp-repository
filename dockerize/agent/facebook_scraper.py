from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Annotated
import requests
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
import json
import os

# Database configuration
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD").replace("@", "%40")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

# Default access token
long_user_access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")

# Define clear input schema for MCP exposure
class ScraperInput(TypedDict):
    """Input schema for the social media scraper agent."""
    post_limit: int  # Number of posts to scrape (default: 5)
    comment_limit: int  # Number of comments per post to scrape (default: 5)

# Define clear output schema for MCP exposure
class ScraperOutput(TypedDict):
    """Output schema for the social media scraper agent."""
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

def initialize_scraper(state: ScraperInput) -> dict:
    """Initialize the scraper with database connection and parameters."""
    # Set default values if not provided
    post_limit = state.get("post_limit", 5)
    comment_limit = state.get("comment_limit", 5)
    
    # Initialize database connection
    try:
        engine = create_engine(
            f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
        
        # Test connection of Database
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            print("✅ Connected to PostgreSQL!")
            
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

def fetch_facebook_posts(state: ScraperState) -> dict:
    """Fetch posts from Facebook API."""
    try:
        # Load environment variables if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        # Construct Facebook API URL
        url = (
            f"https://graph.facebook.com/v22.0/me/posts"
            f"?access_token={state['access_token']}"
            f"&fields=id,message,created_time,likes.summary(true),comments.summary(true),shares"
            f"&limit={state['post_limit']}"
        )
        
        # Make API request
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        return {
            "raw_posts_data": data,
            "status": "posts_fetched",
            "message": f"Successfully fetched {len(data.get('data', []))} posts"
        }
    except Exception as e:
        return {
            "raw_posts_data": {},
            "status": "error",
            "message": f"Failed to fetch posts: {str(e)}"
        }

def process_posts_data(state: ScraperState) -> dict:
    """Process raw posts data into structured format."""
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
        
        # Extract basic post information with null handling
        df_posts = df_main[["id", "message", "created_time", "shares"]].copy()
        
        # Handle null/NaN values in message field
        df_posts["message"] = df_posts["message"].fillna("")
        
        df_posts["likes_count"] = df_main["likes"].apply(lambda x: x.get("summary", {}).get("total_count", 0) if isinstance(x, dict) else 0)
        df_posts["comments_count"] = df_main["comments"].apply(lambda x: x.get("summary", {}).get("total_count", 0) if isinstance(x, dict) else 0)
        df_posts["shares_count"] = df_main["shares"].apply(lambda x: x.get("count", 0) if isinstance(x, dict) else 0)
        
        # Format for database
        df_posts_db = pd.DataFrame()
        df_posts_db["user_id"] = 1
        df_posts_db["agent_id"] = 3
        df_posts_db["post_url"] = "https://www.facebook.com/me/posts/" + df_posts["id"].astype(str)
        df_posts_db["platform"] = "facebook"
        df_posts_db["post_id"] = df_posts["id"].astype(str)
        df_posts_db["post_caption"] = df_posts["message"].fillna("").astype(str)
        df_posts_db["time_stamp"] = df_posts["created_time"]
        df_posts_db["total_likes"] = df_posts["likes_count"]
        df_posts_db["total_comments"] = df_posts["comments_count"]
        df_posts_db["total_shares"] = df_posts["shares_count"]
        
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

def process_comments_data(state: ScraperState) -> dict:
    """Process comments data from posts."""
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
        
        # Extract comments from each post
        for post in data["data"]:
            post_id = post["id"]
            comments_data = post.get("comments", {}).get("data", [])
            
            # Limit comments per post
            for comment in comments_data[:state["comment_limit"]]:
                comments_list.append({
                    "post_id": post_id,
                    "comment_id": comment.get("id"),
                    "comment_message": comment.get("message"),
                    "comment_time": comment.get("created_time"),
                    "commenter": comment.get("from", {}).get("name")
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

def save_to_database(state: ScraperState) -> dict:
    """Save processed data to database."""
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
            
            # Delete existing data from social_media_scraped_data table
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
            sql = f"""INSERT INTO social_media_scraped_data_comments ({headers_comments}) SELECT {headers_comments} FROM social_media_scraped_data_comments_stg;"""
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

def finalize_results(state: ScraperState) -> dict:
    """Finalize and return the scraping results."""
    return {
        "posts_scraped": state.get("posts_scraped", 0),
        "comments_scraped": state.get("comments_scraped", 0),
        "posts_data": state.get("posts_data", []),
        "comments_data": state.get("comments_data", []),
        "status": state.get("status", "completed"),
        "message": state.get("message", "Scraping completed")
    }

# Build the graph with explicit input/output schemas
builder = StateGraph(
    ScraperState,
    input=ScraperInput,  # This defines what the MCP tool expects
    output=ScraperOutput  # This defines what the MCP tool returns
)

# Add nodes
builder.add_node("initialize", initialize_scraper)
builder.add_node("fetch_posts", fetch_facebook_posts)
builder.add_node("process_posts", process_posts_data)
builder.add_node("process_comments", process_comments_data)
builder.add_node("save_to_db", save_to_database)
builder.add_node("finalize", finalize_results)

# Add edges to create the workflow
builder.add_edge(START, "initialize")
builder.add_edge("initialize", "fetch_posts")
builder.add_edge("fetch_posts", "process_posts")
builder.add_edge("process_posts", "process_comments")
builder.add_edge("process_comments", "save_to_db")
builder.add_edge("save_to_db", "finalize")
builder.add_edge("finalize", END)

# Compile the graph
graph = builder.compile()

# # Test function for local execution
# if __name__ == "__main__":
#     print("Social Media Scraper Agent (local mode)")
    
#     # Get input parameters
#     try:
#         post_limit = int(input("Enter post limit (default 5): ") or "5")
#     except ValueError:
#         post_limit = 5
    
#     try:
#         comment_limit = int(input("Enter comment limit (default 5): ") or "5")
#     except ValueError:
#         comment_limit = 5
    
#     # Create input
#     scraper_input = {
#         "post_limit": post_limit,
#         "comment_limit": comment_limit
#     }
    
#     # Run the graph
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