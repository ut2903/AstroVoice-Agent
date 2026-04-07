# 🌌 AstroVoice-Agent

**AstroVoice-Agent** is a real-time, agentic voice AI middleware that bridges **ASR (Speech-to-Text)** and **TTS (Text-to-Speech)** systems, while orchestrating intelligent conversations using LLMs and asynchronous pipelines.

It is designed for **telephony-grade voice systems** where responses must be fast, stateful, and structured.

---

## 🧠 System Overview

```text
User Speech
   ↓
ASR (Speech → Text)
   ↓
AstroVoice-Agent (LLM + LangGraph)
   ↓
Async Intelligence Pipeline (Astrology)
   ↓
Response
   ↓
TTS (Text → Speech)
```

---

## ⚙️ Core Capabilities

* **Agentic orchestration** using LangGraph (stateful, conditional routing)
* **Voice-first responses** optimized for real-time conversations
* **Structured data extraction** (Name, DOB, TOB, POB)
* **Async pipeline execution** triggered only when required inputs are complete
* **Strict prompt-governed reasoning** (no hallucinated astrology)
* **State management via Redis** (conversation, session, extracted data, computed charts)
* **Message-level control** using `reply_id` for deletion

---

## 🏗️ Architecture

### Layers

| Layer          | Responsibility                             |
| -------------- | ------------------------------------------ |
| API Layer      | FastAPI endpoints, request handling        |
| Agent Layer    | LangGraph workflow, LLM execution          |
| State Layer    | Redis (sessions, memory, charts)           |
| Pipeline Layer | Astrology computation + profile generation |
| LLM Layer      | Azure OpenAI / OpenAI-compatible models    |

---

## 📁 Project Structure

```text
astrovoice-agent/
│
├── config.py      # Redis, API keys, constants
├── models.py      # Pydantic models + TypedDict state
├── astro.py       # Geocoding, Prokerala APIs, profile builder
├── graph.py       # LangGraph nodes, routing, compiled graph
├── main.py        # FastAPI app, endpoints, session handling
│
├── requirements.txt
└── README.md
```

---

## 🔄 Agent Workflow

```text
        ┌────────────┐
        │  LLM Call  │
        └─────┬──────┘
              │
     ┌────────▼────────┐
     │   Route Logic   │
     └─────┬─────┬────┘
           │     │
           │     ▼
           │  Summarize → END
           │
           ▼
   Astro Pipeline (async)
           │
           ▼
          END
```

---

## 🚀 Setup

### 1. Clone repository

```bash
git clone https://github.com/ut2903/AstroVoice-Agent.git
cd AstroVoice-Agent
```

---

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```


---

### 5. Run application

```bash
python main.py
```

Server runs on:

```
http://localhost:5000
```

---

## 📡 API

### POST `/chat`

**Request**

```json
{
  "user_id": "123",
  "name": "User",
  "message": "Hello"
}
```

**Response**

```json
{
  "Agent": "नमस्ते...",
  "call_status": "ONGOING",
  "language": "Hindi",
  "summary": "",
  "reply_id": "uuid"
}
```

---

### POST `/delete_message`

**Request**

```json
{
  "reply_id": "uuid"
}
```

**Behavior**

* Deletes the AI response
* Deletes preceding user message (if applicable)
* Maintains conversation consistency

---

## 🧠 Design Constraints

* Astrology interpretation is strictly based on pipeline-generated data
* No inference from DOB/TOB/POB without computed chart
* Responses are short and voice-friendly
* JSON output format is enforced for every turn
* Pipeline executes only once per user (cached in Redis)

---

## ⚡ Tech Stack

* FastAPI
* LangGraph
* Azure OpenAI / OpenAI-compatible LLM
* Redis
* External APIs (Geocoding + Astrology)

---
