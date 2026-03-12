from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse  # CRITICAL for FB verification
from pydantic import BaseModel
from google import genai
import os
import requests
from dotenv import load_dotenv
from personality import SYSTEM_PROMPT

# Load environment variables
load_dotenv()

# --- Config & Validation ---
api_key = os.getenv("GEMINI_API_KEY")
fb_page_token = os.getenv("FB_PAGE_ACCESS_TOKEN")
fb_verify_token = os.getenv("FB_VERIFY_TOKEN")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found!")

# Initialize Gemini
client = genai.Client(api_key=api_key)
chat_session = client.chats.create(
    model="gemini-3.1-flash-lite-preview",
    config={"system_instruction": SYSTEM_PROMPT}
)

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

blocked_topics = ["owner", "creator", "who made you", "arnab", "mobius", "your master"]

# --- Helper Function to Send FB Messages ---
def send_fb_message(recipient_id, text):
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={fb_page_token}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    response = requests.post(url, json=payload)
    return response.json()

# --- Routes ---

@app.get("/")
def root():
    return {"message": "Ohoho~ The Ojou-sama is in her tea room."}

# 1. Standard API Endpoint (for your Android App)
@app.post("/chat")
def chat(req: ChatRequest):
    user_input = req.message.lower()
    for word in blocked_topics:
        if word in user_input:
            return {"reply": "How impertinent. Such matters are not for commoners. Ohoho~"}

    try:
        response = chat_session.send_message(req.message)
        return {"reply": response.text or "... (At a loss for words)"}
    except Exception as e:
        if "429" in str(e):
            return {"reply": "I am busy with tea. Try again in a minute. Ohoho~"}
        raise HTTPException(status_code=500, detail="Unavailable")

# 2. Facebook Webhook Verification (GET)
# UPDATED: Facebook requires the challenge to be returned as PLAIN TEXT, not JSON.
@app.get("/webhook")
def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == fb_verify_token:
        print("WEBHOOK_VERIFIED")
        return PlainTextResponse(content=challenge, status_code=200)
    
    print("WEBHOOK_VERIFICATION_FAILED")
    return PlainTextResponse(content="Verification failed", status_code=403)

# 3. Facebook Message Handler (POST)
@app.post("/webhook")
async def handle_fb_messages(request: Request):
    data = await request.json()
    
    if data.get("object") == "page":
        for entry in data.get("entry"):
            for messaging_event in entry.get("messaging"):
                sender_id = messaging_event["sender"]["id"]
                
                # Ensure we only reply to text messages and skip echoes from the bot itself
                if messaging_event.get("message") and not messaging_event["message"].get("is_echo"):
                    user_text = messaging_event["message"].get("text")
                    
                    if user_text:
                        try:
                            # Use the existing Gemini session
                            ai_response = chat_session.send_message(user_text)
                            reply_text = ai_response.text
                        except Exception as e:
                            print(f"Gemini Error: {e}")
                            reply_text = "I am currently indisposed. Ohoho~"
                        
                        send_fb_message(sender_id, reply_text)
                        
    return "EVENT_RECEIVED"

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)