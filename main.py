from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
import os
from dotenv import load_dotenv
from personality import SYSTEM_PROMPT

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file!")

# Initialize the Gemini Client
client = genai.Client(api_key=api_key)

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

# Use the latest Gemini 3.1 Flash-Lite for speed and high limits
chat_session = client.chats.create(
    model="gemini-3.1-flash-lite-preview",
    config={
        "system_instruction": SYSTEM_PROMPT
    }
)

blocked_topics = [
    "owner", "creator", "who made you", 
    "who owns you", "arnab", "mobius", "your master"
]

@app.get("/")
def root():
    return {"message": "Ohoho~ The Ojou-sama is in her tea room."}

@app.post("/chat")
def chat(req: ChatRequest):  # Removed 'async' to prevent UI freezing
    user_input = req.message.lower()

    # Security filter
    for word in blocked_topics:
        if word in user_input:
            return {
                "reply": "How impertinent. Such matters are not for commoners to inquire about. Ohoho~"
            }

    try:
        # Send message to the session
        response = chat_session.send_message(req.message)
        
        if not response.text:
            return {"reply": "... (The Ojou-sama is at a loss for words.)"}
            
        return {"reply": response.text}

    except Exception as e:
        error_str = str(e)
        print(f"DEBUG Error: {error_str}") # Check your terminal for this!
        
        # Specific handling for Rate Limits (429)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            return {
                "reply": "I am currently far too busy with my tea ceremony to entertain your prattle. Do try again in a minute. Ohoho~"
            }
            
        raise HTTPException(status_code=500, detail="The Ojou-sama is currently unavailable.")

if __name__ == "__main__":
    import uvicorn
    # Use the port assigned by the host, or default to 8080 locally
    port = int(os.environ.get("PORT", 8080))
    # '0.0.0.0' allows the server to be accessible externally
    uvicorn.run(app, host="0.0.0.0", port=port)