import os
from functools import lru_cache
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

@lru_cache(maxsize=1)
def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if url is None:
        raise RuntimeError("Environment variable SUPABASE_URL is not set.")
    if key is None:
        raise RuntimeError("Environment variable SUPABASE_SERVICE_ROLE_KEY is not set.")
    return create_client(url, key)
