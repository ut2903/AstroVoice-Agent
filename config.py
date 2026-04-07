import redis
import urllib3
from langchain_openai import AzureChatOpenAI, ChatOpenAI

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================
# CONSTANTS
# ==============================
PROKERALA_CLIENT_ID = ""      # Set via env or replace before running
PROKERALA_CLIENT_SECRET = ""

GEOCODE_URL = "https://nominatim.openstreetmap.org/search"
APP_NS = "AstroAI_Test"

# ==============================
# REDIS
# ==============================
REDIS_HOST = ""               # e.g. "localhost"
REDIS_PASSWORD = ""

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=6379,
    password=REDIS_PASSWORD,
    decode_responses=True
)

# ==============================
# LLM — Main (Azure GPT-4o)
# ==============================
AZURE_OPENAI_API_KEY = ""
AZURE_OPENAI_ENDPOINT = ""

llm = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    openai_api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    openai_api_version="2024-12-01-preview",
    max_tokens=150
)

# ==============================
# LLM — Summary (Sarvam / local)
# ==============================
SARVAM_API_BASE = ":8000/v1"

llm_summary = ChatOpenAI(
    model="/data/models/sarvam-m",
    max_tokens=600,
    openai_api_key="",  # if required
    openai_api_base=SARVAM_API_BASE,
    timeout=60,
    max_retries=2,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}}
)

# ==============================
# OPTIONAL: Soft warnings
# ==============================
if not AZURE_OPENAI_API_KEY:
    print("⚠️ Azure OpenAI API key not set")

if not REDIS_HOST:
    print("⚠️ Redis host not set")
