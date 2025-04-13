from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import requests
import threading
import time
import os

app = FastAPI()

ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
IG_USER_ID = os.environ.get("IG_USER_ID")
BASE_URL = "https://graph.facebook.com/v19.0"

bot_running = False
bot_thread = None
current_config = {
    "media_id": None,
    "keyword": "link",
    "reply_msg": "Hey! I’ve sent you the product link in your DM.",
    "dm_msg": "Here’s your product link: https://yourstore.com/product"
}

class BotConfig(BaseModel):
    media_id: str
    keyword: str
    reply_msg: str
    dm_msg: str

@app.get("/reels")
def get_user_reels():
    url = f"{BASE_URL}/{IG_USER_ID}/media?fields=id,caption,media_type&access_token={ACCESS_TOKEN}"
    response = requests.get(url)
    if response.status_code == 200:
        reels = [item for item in response.json().get("data", []) if item['media_type'] == 'VIDEO']
        return reels
    raise HTTPException(status_code=400, detail="Failed to fetch reels")

@app.post("/set_config")
def set_bot_config(config: BotConfig):
    global current_config
    current_config = config.dict()
    return {"message": "Config updated"}

@app.post("/start_bot")
def start_bot():
    global bot_running, bot_thread
    if bot_running:
        return {"message": "Bot already running"}
    bot_running = True
    bot_thread = threading.Thread(target=bot_loop, daemon=True)
    bot_thread.start()
    return {"message": "Bot started"}

@app.post("/stop_bot")
def stop_bot():
    global bot_running
    bot_running = False
    return {"message": "Bot stopped"}

@app.delete("/delete_reel/{media_id}")
def delete_reel(media_id: str):
    url = f"{BASE_URL}/{media_id}?access_token={ACCESS_TOKEN}"
    response = requests.delete(url)
    if response.status_code == 200:
        return {"message": "Reel deleted"}
    raise HTTPException(status_code=400, detail="Failed to delete reel")

def bot_loop():
    global bot_running
    seen_comments = set()
    while bot_running:
        media_id = current_config["media_id"]
        keyword = current_config["keyword"].lower()
        reply_msg = current_config["reply_msg"]

        url = f"{BASE_URL}/{media_id}/comments?access_token={ACCESS_TOKEN}"
        response = requests.get(url)
        if response.status_code == 200:
            comments = response.json().get("data", [])
            for comment in comments:
                if comment['id'] not in seen_comments and keyword in comment['text'].lower():
                    seen_comments.add(comment['id'])

                    reply_url = f"{BASE_URL}/{comment['id']}/replies"
                    reply_data = {"message": reply_msg, "access_token": ACCESS_TOKEN}
                    requests.post(reply_url, data=reply_data)

                    print(f"Would send DM to user who commented: {current_config['dm_msg']}")
        
        time.sleep(60)
