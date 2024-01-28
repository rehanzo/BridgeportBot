import requests
import os
import db

KAGI_TOKEN = os.environ["KAGI_TOKEN"] 
def summarize(url):
    base_url = 'https://kagi.com/api/v0/summarize'
    params = {
        "url": f"{url}",
        "summary_type": "summary",
        "engine": "agnes"
    }
    headers = {'Authorization': f'Bot {KAGI_TOKEN}'}

    response = requests.get(base_url, headers=headers, params=params)
    response = response.json()
    return response['data']['output']

def search(query):
    base_url = 'https://kagi.com/api/v0/fastgpt'
    data = {
        "query": f"{query}",
    }
    headers = {'Authorization': f'Bot {KAGI_TOKEN}'}

    response = requests.post(base_url, headers=headers, json=data)
    response = response.json()

    output = response["data"]["output"]
    references = response["data"]["references"]

    # Format the string as required
    references_save = "" 
    for i, ref in enumerate(references, start=1):
        references_save += f"\n{i} - {ref['title']}: {ref['url']}"

    db.save("references", references_save, "refs.sqlite3")


    return output
