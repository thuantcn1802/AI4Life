import requests
import os
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

url = "https://api.groq.com/openai/v1/models"
headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

res = requests.get(url, headers=headers)

print("\nSTATUS:", res.status_code)
print("\nRAW RESPONSE:\n", res.text)
