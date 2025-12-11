# supabase_client.py
import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://YOUR_PROJECT.supabase.co")
SUPABASE_SERVICE_ROLE = os.environ.get("SUPABASE_SERVICE_ROLE", "YOUR_SERVICE_ROLE_KEY")

if not SUPABASE_URL or "YOUR_PROJECT" in SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL not set correctly in environment")

if not SUPABASE_SERVICE_ROLE or "YOUR_SERVICE_ROLE_KEY" in SUPABASE_SERVICE_ROLE:
    raise RuntimeError("SUPABASE_SERVICE_ROLE not set correctly in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
