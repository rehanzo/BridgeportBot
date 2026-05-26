import os

import requests

import db

KAGI_TOKEN = os.environ["KAGI_TOKEN"]
KAGI_TOKEN_V0 = os.environ["KAGI_TOKEN_V0"]


def summarize(url: str) -> str:
    response = requests.get(
        "https://kagi.com/api/v0/summarize",
        headers={"Authorization": f"Bot {KAGI_TOKEN_V0}"},
        params={"url": url, "summary_type": "summary", "engine": "agnes"},
    )
    return response.json()["data"]["output"]


def search(query: str) -> str:
    response = requests.post(
        "https://kagi.com/api/v0/fastgpt",
        headers={"Authorization": f"Bot {KAGI_TOKEN_V0}"},
        json={"query": query},
    )
    data = response.json()["data"]

    references = ""
    for i, ref in enumerate(data["references"], start=1):
        references += f"\n{i} - {ref['title']}: {ref['url']}"
    db.save("references", references, "refs.sqlite3")

    return data["output"]


def search_v1(query: str) -> str:
    response = requests.post(
        "https://kagi.com/api/v1/search",
        headers={"Authorization": f"Bearer {KAGI_TOKEN}"},
        json={"query": query, "format": "markdown"},
        timeout=10,
    )
    return response.text
