import requests

API_URL = "https://jsonplaceholder.typicode.com/posts"


def fetch_posts(limit: int = 10) -> list[dict]:
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    posts = resp.json()
    return posts[:limit]


def format_post(post: dict) -> str:
    return f"Title: {post['title']}\n\n{post['body']}"