from pymongo import MongoClient
from flask import Flask, jsonify
from threading import Thread
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8625107557:AAFJRaDmLgtjaoVtbSLF5u_NIBRo87gyUdY"

# ===== MongoDB =====
MONGO_URL = os.environ.get("MONGO_URL")

client = MongoClient(MONGO_URL)
db = client["telegram_bot"]
collection = db["files"]

def load_files():
    data = {}
    for item in collection.find():
        data[item["key"]] = item["file_id"]
    return data

def save_file(key, file_id):
    collection.update_one(
        {"key": key},
        {"$set": {"file_id": file_id}},
        upsert=True
    )

def delete_file_db(key):
    collection.delete_one({"key": key})

FILES = load_files()

# ===== API SERVER =====
api = Flask(__name__)

@api.route("/")
def home():
    return "API is running"

@api.route("/files")
def get_files():
    return jsonify(FILES)

def run_api():
    port = int(os.environ.get("PORT", 10000))
    api.run(host="0.0.0.0", port=port)

Thread(target=run_api).start()

# ===== TEMP STORAGE =====
UPLOAD_CONTEXT = {}

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        key = context.args[0]

        if key in FILES:
            await update.message.reply_document(FILES[key])
        else:
            await update.message.reply_text("❌ File not found")
        return

    keyboard = [[InlineKeyboardButton(
        "📚 Open Resources",
        web_app=WebAppInfo(url="https://rakib-s-personal-resources.vercel.app")
    )]]

    await update.message.reply_text("📥 Click below", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== UPLOAD =====
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sem = context.args[0]
        type_ = context.args[1].lower()
        cat = context.args[2].lower()
        subject = context.args[3].lower()

        UPLOAD_CONTEXT[update.effective_user.id] = {
            "sem": sem,
            "type": type_,
            "cat": cat,
            "subject": subject
        }

        await update.message.reply_text(
            f"📤 Uploading to:\nsem{sem}/{type_}/{cat}/{subject}"
        )

    except:
        await update.message.reply_text(
            "Use: /upload 3 mid slides cse-2321"
        )
# ===== HANDLE FILE =====
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in UPLOAD_CONTEXT:
        await update.message.reply_text("❌ Use /upload first")
        return

    file = update.message.document
    file_id = file.file_id

    sem = UPLOAD_CONTEXT[user_id]["sem"]
    type_ = UPLOAD_CONTEXT[user_id]["type"]
    cat = UPLOAD_CONTEXT[user_id]["cat"]
    subject = UPLOAD_CONTEXT[user_id]["subject"]

    key = f"sem{sem}/{type_}/{cat}/{subject}"

    FILES[key] = file_id
    save_file(key, file_id)

    await update.message.reply_text(f"✅ Saved!\nKEY: {key}")
# ===== DELETE =====
async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        key = context.args[0]

        if key in FILES:
            del FILES[key]
            delete_file_db(key)
            await update.message.reply_text(f"🗑 Deleted: {key}")
        else:
            await update.message.reply_text("❌ Key not found")

    except:
        await update.message.reply_text("Use: /delete key")

# ===== SEND ALL =====
async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sem = context.args[0]
        cat = context.args[1]

        found = False

        for key, file_id in FILES.items():
           if key.startswith(f"sem{sem}/{cat}"):
                await update.message.reply_document(file_id)
                found = True

        if not found:
            await update.message.reply_text("❌ No files found")

    except:
        await update.message.reply_text("Use: /all 3 prev")

# ===== RUN =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("upload", upload))
app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
app.add_handler(CommandHandler("delete", delete_file))
app.add_handler(CommandHandler("all", send_all))

app.run_polling()
