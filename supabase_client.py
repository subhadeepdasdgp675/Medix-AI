import os
from dotenv import load_dotenv

# Load .env from parent workspace directory with override=True
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
load_dotenv(".env", override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ggtiadergsqblwpemdhi.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

supabase = None
try:
    from supabase import create_client, Client
    if SUPABASE_URL and SUPABASE_KEY and SUPABASE_KEY != "your_supabase_service_role_key_here":
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"Connected to Supabase project successfully! (URL: {SUPABASE_URL})")
    else:
        print(f"Notice: Supabase KEY is empty or placeholder (Key prefix: {SUPABASE_KEY[:10] if SUPABASE_KEY else 'NONE'})")
        print("Supabase URL loaded. Add your active API keys in .env to enable database operations.")
except Exception as e:
    print(f"Notice: Supabase client initialization error: {e}")

def get_supabase():
    return supabase
