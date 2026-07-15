import requests

API_KEY ="AQ.Ab8RN6Lu2rVFwJ9nWjGwWqhM9IizpR18bPBQBPTi_ly8cfN3og"

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

payload = {
    "contents": [
        {
            "parts": [
                {"text": "Say hello"}
            ]
        }
    ]
}

response = requests.post(url, json=payload)

print(response.status_code)
print(response.text)