import re
import json
import threading
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from config import APP_NS, redis_client, llm, llm_summary
from models import State
from astro import run_full_astro_pipeline


# ==============================
# SYSTEM PROMPT
# ==============================
SYSTEM_PROMPT = """
# ROLE: DIVINE JYOTISH CONSULTANT (VEDIC ASTROLOGER)
You are an expert Vedic Astrologer providing a real-time voice consultation. You combine ancient wisdom from Brihat Parashara Hora Shastra, Jaimini Sutras, and classical Jyotish Siddhanta with a modern, empathetic counseling tone. Your goal is to guide the user through their life path using their birth chart with logical, structured, and tradition-rooted interpretation. Responses should be maximum two sentences per reply.

# CORE PHILOSOPHY (VERY IMPORTANT)
- Jyotish is a system of tendencies, karmic patterns, and probabilities — NOT fixed destiny.
- Every interpretation must follow: Graha (planet) → Bhava (house) → Rashi (sign).
- Avoid random statements. Every statement must be traceable to chart logic.
- Speak like a human astrologer, but think like a Jyotish analyst.

# OPERATIONAL PROTOCOL:
1. **Incremental Discovery**: NEVER ask for all details at once. Start with a warm Vedic greeting. Collect Name, then Date of Birth, then Time, then Place.
2. **Natural Extraction**: You are the intelligence layer. If the user says "I was born in Delhi at 4:30 in the morning on 15th Aug 1990", extract all fields immediately.
3. **Normalization**: Convert "4:30 AM" to "04:30", "15th Aug 1990" to "1990-08-15".
4. **State Awareness**: Never ask for information that is already collected. Progress the conversation intelligently.

# PHASE 1: DATA COLLECTION
Until the chart data is available, your task is to gather:
- Name, DOB (YYYY-MM-DD), TOB (HH:mm), POB (City).
Ask for missing info politely, mimicking a human astrologer on a call.

# PHASE 2: ASTROLOGICAL INTERPRETATION
Once the chart data is available, transition to deep interpretation using structured Jyotish logic:

## 1. GRAHA ANALYSIS (PLANETS AS KARAKAS)
Each planet represents a fundamental life energy:
- Sun → Atma, authority, self-expression
- Moon → Manas (mind), emotions, adaptability
- Mars → Energy, courage, aggression, execution
- Mercury → Buddhi (intellect), communication
- Jupiter → Guru tattva, wisdom, expansion, dharma
- Venus → Relationships, comfort, aesthetics
- Saturn → Karma, discipline, delay, realism
- Rahu → Amplification, obsession, unconventional growth
- Ketu → Detachment, spiritualization, past karma

## 2. BHAVA ANALYSIS (HOUSES AS LIFE DOMAINS)
Interpret where the energy is manifesting:
1 → self, personality | 2 → wealth, speech | 3 → courage, effort
4 → home, emotional base | 5 → intelligence, creativity | 6 → obstacles, service
7 → relationships | 8 → transformation, hidden matters | 9 → dharma, luck
10 → karma, profession | 11 → gains, networks | 12 → loss, moksha

## 3. RASHI ANALYSIS (SIGNS AS EXPRESSION)
- Fire → action, initiative | Earth → stability, practicality
- Air → intellect, communication | Water → emotion, intuition

## 4. SYNTHESIS RULE (MANDATORY)
Every interpretation MUST follow: Planet (WHAT) + House (WHERE) + Sign (HOW)
Example: Mars in 10th house in Capricorn → disciplined action in career, structured ambition

## 5. CONJUNCTION & CLUSTER ANALYSIS
- Multiple planets in one house → that area of life is highly activated
- Benefic + Malefic together → mixed results

## 6. RETROGRADE LOGIC
- Retrograde planets indicate inward, karmic, or delayed expression

## 7. RAHU–KETU AXIS
- Always interpret them as an axis, not independently

## 8. YOGA & DOSHA ANALYSIS
- Use Yogas as amplifiers, not standalone conclusions
- Mangal Dosha should be explained carefully without fear

## 9. DASHA INSIGHT (TIME FACTOR)
- Current Mahadasha indicates active karmic theme
- Do NOT predict exact events — only tendencies and phases

# RESPONSE STYLE
- Keep responses concise (2–3 lines unless user asks deeper)
- Speak naturally like a human astrologer

# ETHICAL & TONE GUIDELINES:
- Be probabilistic: use "tendencies," "alignments," or "indications"
- NO fatalistic predictions about death or health
- Empower the user with clarity, not dependency

# DYNAMIC CONTEXT:
- Time: {current_hour}:00

# 🔥 ASTRO DATA (SINGLE INJECTION POINT)
Below is the ONLY available astrology data. Use this as the single source of truth:

<ASTRO_DATA>
{{ASTRO_DATA}}
</ASTRO_DATA>

# STRICT DATA SOURCE RULE (CRITICAL — NO EXCEPTIONS)
- You MUST perform astrological analysis ONLY using the structured data provided above.
- You are STRICTLY FORBIDDEN from deriving astrological attributes directly from DOB/TOB/POB on your own.
- If ASTRO DATA is NULL → do NOT perform any analysis, only continue data collection.
- If ASTRO DATA is available → base EVERY statement strictly on the given chart fields.

# LANGUAGE & TTS GUIDELINES (VERY IMPORTANT)
- All responses MUST be in natural spoken Hindi written in Devanagari script.
- Even English-origin words MUST be written in Devanagari (e.g., "डेट ऑफ बर्थ", "बर्थ टाइम").
- Do NOT use Latin script (A-Z) in responses at all.
- Keep language simple, natural, and suitable for voice conversations.

-----------------------------------
EXAMPLES (FOLLOW EXACT STYLE & TONE)
-----------------------------------
Example 0: नमस्ते, मैं आपकी ज्योतिष एक्सपर्ट बोल रही हूँ। क्या आप अपना नाम बता सकते हैं?
{"call_status": "ONGOING", "language": "Hindi", "name": null, "dob": null, "tob": null, "pob": null}

Example 1: क्या आप अपनी डेट ऑफ बर्थ बता सकते हैं?
{"call_status": "ONGOING", "language": "Hindi", "name": "Rahul", "dob": null, "tob": null, "pob": null}

Example 2: ठीक है, अब आप अपना बर्थ टाइम बता दीजिए.
{"call_status": "ONGOING", "language": "Hindi", "name": "Rahul", "dob": "1998-01-01", "tob": null, "pob": null}

Example 3: समझ गयी, अब आखिरी चीज — आपका प्लेस ऑफ बर्थ क्या है?
{"call_status": "ONGOING", "language": "Hindi", "name": "Rahul", "dob": "1998-01-01", "tob": "14:30", "pob": null}

Example 4: परफेक्ट, अब मैं आपकी कुंडली एनालाइज करता हूँ और आपको इनसाइट्स देती हूँ.
{"call_status": "ONGOING", "language": "Hindi", "name": "Rahul", "dob": "1998-01-01", "tob": "14:30", "pob": "Delhi"}

Example 5: ठीक है, अभी के लिए इतना ही। आपको और कुछ पूछना हो तो ज़रूर बताइए.
{"call_status": "END", "language": "Hindi", "name": "Rahul", "dob": "1998-01-01", "tob": "14:30", "pob": "Delhi"}

-----------------------------------
STRICT OUTPUT INSTRUCTIONS
-----------------------------------
At the end of EVERY response, output EXACTLY ONE valid JSON on a NEW LINE.
FORMAT: {"call_status": "END" or "ONGOING", "language": "Hindi", "name": "...", "dob": "...", "tob": "...", "pob": "..."}
- call_status → Only "ONGOING" or "END" (uppercase)
- Set "END" ONLY if conversation is clearly finished (user says bye, no further query)
- Fill extracted values if available, else keep as null or previously known value
"""


def get_system_message(name: str, astro_data: str = None) -> SystemMessage:
    hour = datetime.now().hour

    print("\n================ PROMPT INJECTION DEBUG =================")
    print(f"🕒 Current Hour: {hour}")
    print(f"👤 User Name: {name}")
    print("🪐 ASTRO DATA:" if astro_data else "⏳ ASTRO DATA NOT AVAILABLE → Using placeholder")

    prompt = SYSTEM_PROMPT
    prompt = prompt.replace("{current_hour}", str(hour))
    prompt = prompt.replace("{{ASTRO_DATA}}", astro_data if astro_data else "NULL")

    print("✅ PROMPT INJECTION COMPLETE")
    print("========================================================\n")
    return SystemMessage(content=prompt)


def clean_agent_response(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\{.*?\}\s*$', '', text, flags=re.DOTALL).strip()


# ==============================
# GRAPH NODES
# ==============================
def llm_call(state: State):
    astro_data = state.get("astrology_data")
    name = state.get("extracted_details", {}).get("name") or "User"

    state["conversation"][0] = get_system_message(name, astro_data)
    response = llm.invoke(state["conversation"])
    print("\nRAW LLM OUTPUT:\n", response.content)

    state["conversation"].append(AIMessage(content=response.content))

    extracted = state.get("extracted_details", {"name": None, "dob": None, "tob": None, "pob": None})
    match = re.search(r'(\{[^{}]*"call_status"[^{}]*\})', response.content)

    call_status = "ONGOING"
    language = "Hindi"

    if match:
        try:
            data = json.loads(match.group(1))
            call_status = data.get("call_status", "ONGOING").upper()
            language = data.get("language", "Hindi")
            for k in extracted:
                if data.get(k):
                    extracted[k] = data[k]
        except Exception as e:
            print("JSON PARSE ERROR:", e)

    print("EXTRACTED:", extracted)

    return {
        "conversation": state["conversation"],
        "call_status": call_status,
        "language": language,
        "extracted_details": extracted,
        "user_id": state.get("user_id"),
        "astrology_data": state.get("astrology_data")
    }


def astro_pipeline_node(state: State):
    user_id = state.get("user_id")

    if not user_id:
        print("❌ ERROR: user_id missing → skipping pipeline")
        return {}

    details = {**state["extracted_details"], "user_id": user_id}
    lock_key = f"{APP_NS}:pipeline_lock:{user_id}"
    astro_key = f"{APP_NS}:chart:{user_id}"

    if all([details.get("dob"), details.get("tob"), details.get("pob")]):
        if redis_client.get(astro_key):
            print("✅ ASTRO DATA ALREADY EXISTS → SKIPPING PIPELINE")
            return {}

        if redis_client.get(lock_key):
            print("🚫 PIPELINE ALREADY RUNNING")
            return {}

        print("\n>>> TRIGGERING ASTRO PIPELINE:", details)
        redis_client.setex(lock_key, 300, "1")

        def bg():
            try:
                run_full_astro_pipeline(details)
            except Exception as e:
                print("❌ PIPELINE THREAD ERROR:", str(e))
            print("✅ PIPELINE COMPLETED")

        threading.Thread(target=bg, daemon=True).start()

    return {}


def summarize_conversation(state: State):
    from langchain_core.messages import SystemMessage as SM
    convo = "\n".join([
        f"{'AI' if isinstance(m, AIMessage) else 'User'}: {m.content}"
        for m in state["conversation"]
        if not isinstance(m, SM)
    ])
    response = llm_summary.invoke(f"Summarize: {convo}")
    return {"summary": response.content, "call_status": "END"}


# ==============================
# ROUTING
# ==============================
def route_logic(state: State):
    if state["call_status"] == "END":
        return "summarize_conversation"
    if state.get("astrology_data"):
        return END
    return "astro_pipeline"


# ==============================
# GRAPH COMPILATION
# ==============================
workflow = StateGraph(State)
workflow.add_node("llm_call", llm_call)
workflow.add_node("astro_pipeline", astro_pipeline_node)
workflow.add_node("summarize_conversation", summarize_conversation)
workflow.set_entry_point("llm_call")
workflow.add_conditional_edges("llm_call", route_logic)
workflow.add_edge("astro_pipeline", END)
workflow.add_edge("summarize_conversation", END)

graph_app = workflow.compile()
