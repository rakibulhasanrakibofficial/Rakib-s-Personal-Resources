from pymongo import MongoClient
from flask import Flask, jsonify
from threading import Thread
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8625107557:AAFJRaDmLgtjaoVtbSLF5u_NIBRo87gyUdY"

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
    "type": exam_type,
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
type_ = UPLOAD_CONTEXT[user_id]["type"]
cat = UPLOAD_CONTEXT[user_id]["cat"]

key = f"sem{sem}_{type_}_{cat}_{subject}"

    FILES[key] = file_id
    save_file(key, file_id)

    
    await update.message.reply_text(f"✅ Saved!\nKEY: {key}")

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
