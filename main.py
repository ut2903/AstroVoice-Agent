import json
import uvicorn
from uuid import uuid4

from fastapi import FastAPI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from config import APP_NS, redis_client
from models import ChatRequest, DeleteMessageRequest
from graph import graph_app, get_system_message, clean_agent_response

app = FastAPI()


# ==============================
# HELPERS
# ==============================
def msg_to_json(m):
    return {"type": m.__class__.__name__, "content": m.content}


def json_to_msg(m):
    mapping = {
        "SystemMessage": SystemMessage,
        "HumanMessage": HumanMessage,
        "AIMessage": AIMessage
    }
    return mapping[m["type"]](content=m["content"])


def redis_key_conversation(user_id, session_id):
    return f"{APP_NS}:conv:{user_id}:{session_id}"


# ==============================
# ENDPOINTS
# ==============================
@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    sid_key = f"{APP_NS}:sid:{req.user_id}"
    session_id = redis_client.get(sid_key) or str(uuid4())
    redis_client.setex(sid_key, 1800, session_id)

    conv_key = f"{APP_NS}:conv:{req.user_id}:{session_id}"
    astro_key = f"{APP_NS}:chart:{req.user_id}"
    details_key = f"{APP_NS}:details:{req.user_id}"

    conv_json = redis_client.get(conv_key)
    conversation = (
        [json_to_msg(m) for m in json.loads(conv_json)]
        if conv_json
        else [get_system_message(req.name)]
    )
    conversation.append(HumanMessage(content=req.message))

    astro_data = redis_client.get(astro_key)
    print("🔍 FETCH ASTRO DATA:", astro_key, "->", "FOUND" if astro_data else "MISSING")

    state = {
        "conversation": conversation,
        "call_status": "ONGOING",
        "user_id": req.user_id,
        "astrology_data": astro_data,
        "extracted_details": json.loads(
            redis_client.get(details_key) or '{"name":null,"dob":null,"tob":null,"pob":null}'
        )
    }

    result = graph_app.invoke(state)

    astro_data_latest = redis_client.get(astro_key)
    if astro_data_latest and not state.get("astrology_data"):
        print("ASTRO DATA NOW AVAILABLE -> injecting in next turn")

    redis_client.setex(conv_key, 1800, json.dumps([msg_to_json(m) for m in result["conversation"]]))
    redis_client.setex(details_key, 86400, json.dumps(result["extracted_details"]))

    last_msg = next(m.content for m in reversed(result["conversation"]) if isinstance(m, AIMessage))

    reply_id = str(uuid4())
    redis_client.setex(
        f"{APP_NS}:reply:{reply_id}",
        1800,
        json.dumps({
            "user_id": req.user_id,
            "session_id": session_id,
            "msg_index": len(result["conversation"]) - 1
        })
    )
    print(f"Stored reply_id -> index mapping: {reply_id} -> {len(result['conversation']) - 1}")

    return {
        "Agent": clean_agent_response(last_msg),
        "call_status": result["call_status"],
        "language": result.get("language", "Hindi"),
        "summary": result.get("summary", ""),
        "reply_id": reply_id
    }


@app.post("/delete_message")
async def delete_message(req: DeleteMessageRequest):
    key = f"{APP_NS}:reply:{req.reply_id}"
    info_json = redis_client.get(key)

    if not info_json:
        return {"error": "Invalid or expired reply_id"}

    info = json.loads(info_json)
    user_id = info["user_id"]
    session_id = info["session_id"]
    msg_index = info["msg_index"]

    conv_key = redis_key_conversation(user_id, session_id)
    conv_json = redis_client.get(conv_key)

    if not conv_json:
        return {"error": "Conversation not found"}

    conversation = [json_to_msg(m) for m in json.loads(conv_json)]

    if not (0 <= msg_index < len(conversation)):
        return {"error": "Invalid message index"}

    if not isinstance(conversation[msg_index], AIMessage):
        return {"error": "Target message is not an AI message"}

    print(f"\nDeleting AI message at index: {msg_index}")

    deleted = {"agent_message": conversation[msg_index].content}

    delete_human = msg_index - 1 >= 0 and isinstance(conversation[msg_index - 1], HumanMessage)
    if delete_human:
        deleted["user_message"] = conversation[msg_index - 1].content

    del conversation[msg_index]
    if delete_human:
        del conversation[msg_index - 1]

    redis_client.setex(conv_key, 1800, json.dumps([msg_to_json(m) for m in conversation]))
    redis_client.delete(key)

    print("Deletion complete")

    return {"status": "success", "deleted": deleted, "reply_id": req.reply_id}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
