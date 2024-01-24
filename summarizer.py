import requests
import os

def summarize(url):
    token = os.environ["SUMMARIZER_API_KEY"]
    base_url = 'https://kagi.com/api/v0/summarize'
    params = {
        "url": f"{url}",
        "summary_type": "summary",
        "engine": "agnes"
    }
    headers = {'Authorization': f'Bot {token}'}

    response = requests.get(base_url, headers=headers, params=params)
    response = response.json()
    return response['data']['output']
