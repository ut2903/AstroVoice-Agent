import redis
import urllib3
from langchain_openai import AzureChatOpenAI, ChatOpenAI

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================
# CONSTANTS
# ==============================
PROKERALA_CLIENT_ID = ""
PROKERALA_CLIENT_SECRET = ""
GEOCODE_URL = "https://nominatim.openstreetmap.org/search"
APP_NS = "AstroAI_Test"

# ==============================
# REDIS
# ==============================
redis_client = redis.Redis(
    host="",
    port=6379,
    password="",
    decode_responses=True
)

# ==============================
# LLM — Main (Azure GPT-4o)
# ==============================
llm = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    openai_api_key="",
    azure_endpoint="",
    openai_api_version="2024-12-01-preview",
    max_tokens=150
)

# ==============================
# LLM — Summary (Sarvam)
# ==============================
llm_summary = ChatOpenAI(
    model="/data/models/sarvam-m",
    max_tokens=600,
    openai_api_key="",
    openai_api_base=":8000/v1",
    timeout=60,
    max_retries=2,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}}
)
