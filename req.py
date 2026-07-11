import requests

url = "https://ynlameyuhvmesozcuanh.supabase.co/rest/v1/api_keys"


API_KEY = "sb_publishable_TTKVxJBQndH8tqtnyru1Uw_CVwgVzxE"

headers = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}"
}

params = {
    "api_key": "eq.A7B2C-H6B8D-L9B4X",
    "select": "*"
}

r = requests.get(url, headers=headers, params=params)

print(r.json())