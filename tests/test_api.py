from tjm_labs_grounding_agent.api_client import (
    format_post
)


def test_format_post():
    post = {"title": "Hello World", "body": "This is the body."}
    assert format_post(post) == "Title: Hello World\n\nThis is the body."