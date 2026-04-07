from pydantic import BaseModel
from typing_extensions import TypedDict


# ==============================
# API REQUEST MODELS
# ==============================
class ChatRequest(BaseModel):
    user_id: str
    name: str = "Customer"
    message: str
    call_status: str = "ONGOING"


class DeleteMessageRequest(BaseModel):
    reply_id: str


# ==============================
# LANGGRAPH STATE
# ==============================
class State(TypedDict):
    conversation: list
    call_status: str
    language: str
    summary: str
    extracted_details: dict
    astrology_data: str
    user_id: str
