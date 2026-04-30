from flask import Flask, jsonify
from threading import Thread
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8625107557:AAFJRaDmLgtjaoVtbSLF5u_NIBRo87gyUdY"

DB_FILE = "files.json"

# load / save
def load_files():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_files(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

FILES = load_files()
# ===== API SERVER =====
api = Flask(__name__)
@api.route("/")
def home():
    return "API is running"
@api.route("/files")
def get_files():
    return jsonify(FILES)

import os

def run_api():
    port = int(os.environ.get("PORT", 10000))
    api.run(host="0.0.0.0", port=port)
# run API in background
Thread(target=run_api).start()

# temp storage
UPLOAD_CONTEXT = {}

# 🔥 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        key = context.args[0]

        if key in FILES:
            await update.message.reply_document(FILES[key])
            return
        else:
            await update.message.reply_text("❌ File not found")
            return

    keyboard = [[InlineKeyboardButton(
        "📚 Open Resources",
        web_app=WebAppInfo(url="https://rakib-s-personal-resources.vercel.app")
    )]]

    await update.message.reply_text("📥 Click below", reply_markup=InlineKeyboardMarkup(keyboard))


# 🔥 ADMIN COMMAND
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sem = context.args[0]
        category = context.args[1]

        UPLOAD_CONTEXT[update.effective_user.id] = {
            "sem": sem,
            "cat": category
        }

        await update.message.reply_text("📤 Now send your PDF")

    except:
        await update.message.reply_text("Use like: /upload 3 prev")


# 🔥 FILE HANDLE
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in UPLOAD_CONTEXT:
        await update.message.reply_text("❌ Use /upload first")
        return

    file = update.message.document
    file_id = file.file_id

    file_name = file.file_name.lower()

    # subject extract
    subject = file_name.split(" ")[0]

    sem = UPLOAD_CONTEXT[user_id]["sem"]
    cat = UPLOAD_CONTEXT[user_id]["cat"]

    key = f"sem{sem}_{cat}_{subject}"

    FILES[key] = file_id
    save_files(FILES)

    
    await update.message.reply_text(f"✅ Saved!\nKEY: {key}")

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        key = context.args[0]

        if key in FILES:
            del FILES[key]
            save_files(FILES)
            await update.message.reply_text(f"🗑 Deleted: {key}")
        else:
            await update.message.reply_text("❌ Key not found")

    except:
        await update.message.reply_text("Use: /delete key")

async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sem = context.args[0]
        cat = context.args[1]

        found = False

        for key, file_id in FILES.items():
            if key.startswith(f"sem{sem}_{cat}"):
                await update.message.reply_document(file_id)
                found = True

        if not found:
            await update.message.reply_text("❌ No files found")

    except:
        await update.message.reply_text("Use: /all 3 prev")


# RUN
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("upload", upload))
app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
app.add_handler(CommandHandler("delete", delete_file))
app.add_handler(CommandHandler("all", send_all))

app.run_polling()