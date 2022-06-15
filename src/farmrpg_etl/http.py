import os

import httpx

client = httpx.AsyncClient(
    base_url="https://farmrpg.com/",
    cookies={"HighwindFRPG": os.environ["AUTH_COOKIE"]},
    headers={
        "Referer": "https://farmrpg.com/",
        "User-Agent": "farmrpg-etl (contact coderanger)",
    },
)
