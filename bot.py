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

# ===== API SERVER =====
from flask_cors import CORS

api = Flask(__name__)
CORS(api)


@api.route("/")
def home():
    return "API is running"

@api.route("/files")
def get_files():
    return jsonify({
        "sem3/final/prev/chem-2301": "https://drive.google.com/file/d/1ze6nMlXcKqK-X7WcwlGeYInOB17Lx6Z9/preview"
    })
    
def run_api():
    port = int(os.environ.get("PORT", 10000))
    api.run(host="0.0.0.0", port=port)

def start_services():
    t = Thread(target=run_api)
    t.daemon = True
    t.start()

# ===== TEMP STORAGE =====
UPLOAD_CONTEXT = {}

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # 🔥 DEBUG LINE (এইটাই add করবা)
    print("START COMMAND:", context.args)

    if context.args:
        key = context.args[0]

        found = False

        for item in collection.find():
            k = item["key"]
            file_id = item["file_id"]

            if k.strip().lower().startswith(key.strip().lower()):
                await update.message.reply_document(file_id)
                found = True

        if not found:
            await update.message.reply_text("❌ No files found")

        return

    keyboard = [[InlineKeyboardButton(
        "📚 Open Resources",
        web_app=WebAppInfo(url="https://rakib-s-personal-resources.vercel.app")
    )]]

    await update.message.reply_text("📥 Click below", reply_markup=InlineKeyboardMarkup(keyboard))
# ===== UPLOAD =====
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    UPLOAD_CONTEXT[user_id] = {}

    if len(args) >= 1:
        UPLOAD_CONTEXT[user_id]["sem"] = args[0]

    if len(args) >= 2:
        UPLOAD_CONTEXT[user_id]["type"] = args[1].lower()

    if len(args) >= 3:
        UPLOAD_CONTEXT[user_id]["cat"] = args[2].lower()

    data = UPLOAD_CONTEXT[user_id]

    if "sem" not in data:
        await update.message.reply_text("Enter Semester (1-8):")
        return

    if "type" not in data:
        await update.message.reply_text("Enter Type (mid/final):")
        return

    if "cat" not in data:
        await update.message.reply_text("Enter Category (slides/prev/notes):")
        return

    if "subject" not in data:
        await update.message.reply_text("Enter Subject (cse-2321):")
        return


# ===== HANDLE FILE =====
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # ❌ যদি আগে /upload না দেওয়া হয়
    if user_id not in UPLOAD_CONTEXT:
        await update.message.reply_text("❌ Use /upload first")
        return

    data = UPLOAD_CONTEXT[user_id]

    # ❌ যদি সব step complete না হয়
    if not all(k in data for k in ["sem", "type", "cat", "subject"]):
        await update.message.reply_text("❌ Complete all steps first")
        return

    # 📄 file info
    file = update.message.document
    file_id = file.file_id

    # 📂 path build
    sem = data["sem"]
    type_ = data["type"].strip().lower()
    cat = data["cat"].strip().lower()
    subject = data["subject"].strip().lower()

    key = f"sem{sem}/{type_}/{cat}/{subject}"

    # 💾 save
    save_file(key, file_id)

    # ✅ success message
    await update.message.reply_text(
        f"✅ Saved!\n📂 Path: {key}"
    )

    # 🔄 reset context (important)
    del UPLOAD_CONTEXT[user_id]
# ===== DELETE =====
async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        key = context.args[0]

        delete_file_db(key)
        await update.message.reply_text(f"🗑 Deleted: {key}")

    except:
        await update.message.reply_text("Use: /delete key")

# ===== SEND ALL =====
async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sem = context.args[0].strip().lower()
        cat = context.args[1].strip().lower()

        found = False

        for item in collection.find():
            key = item["key"]
            file_id = item["file_id"]

            if key.strip().lower().startswith(f"sem{sem}/{cat}"):
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
app.add_handler(MessageHandler(filters.Document, handle_file))
app.add_handler(CommandHandler("delete", delete_file))
app.add_handler(CommandHandler("all", send_all))

if __name__ == "__main__":
    start_services()
    app.run_polling()
