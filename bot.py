import os
import time
import re
import threading
import pandas as pd
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ================== AYARLAR ==================

BOT_TOKEN = "8134035994:AAGbDKtDPADu0P59DthBkGDx7FZeIuewAKQ"

CSV_URL = "https://docs.google.com/spreadsheets/d/1gwgQnpOnu4DB-T5c-eXoMAsNoeGIQTOp0v99cc4uJfc/export?format=csv&gid=0"

ADMIN_ID = 7311284778

ALLOWED_GROUP_IDS = [
    -1003159684647,
    -1003222476077,
    -1003174102297,
    -1003215786503,
    -4902679499,
    -1003980973190,
    -1003989682635,
    -1003935191465
]

MUAF_GROUP_IDS = [
    -1003989682635
]

NOT_FOUND_MSG = "❗️ Tesisat numarası bulunamadı."

# ================== FLASK (RENDER PORT FIX) ==================

app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "Bot çalışıyor"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

# ================== MEMORY ==================

photo_timers = {}
user_colors = ["🔴", "🟢", "🔵", "🟡", "🟣", "🟠"]

def get_user_color(user_id):
    return user_colors[user_id % len(user_colors)]

# ================== DATA ==================

df = pd.DataFrame()

def load_data():
    global df
    try:
        df = pd.read_csv(
            CSV_URL,
            dtype=str,
            encoding="utf-8-sig",
            sep=None,
            engine="python"
        )

        df.columns = df.columns.str.strip()
        df = df.fillna("").astype(str)

        for col in df.columns:
            df[col] = df[col].str.strip()

        if "Tesisat" in df.columns:
            df["Tesisat"] = (
                df["Tesisat"]
                .str.replace(".0", "", regex=False)
                .str.replace(" ", "", regex=False)
            )

        print("✅ Google Sheets verisi güncellendi")
        print("SATIR:", len(df))

    except Exception as e:
        print("❌ Veri hatası:", e)
        df = pd.DataFrame()

async def update_data(context: ContextTypes.DEFAULT_TYPE):
    load_data()

# ================== HELPERS ==================

def safe(val):
    return "" if pd.isna(val) else val

def get_endeks(num):
    if df.empty:
        return None

    row = df[df["Tesisat"] == num]
    if row.empty:
        return None

    data = row.iloc[0]

    return (
        f"<b>{num}</b>\n"
        f"<b>T1:</b> {safe(data.get('T1'))}\n"
        f"<b>T2:</b> {safe(data.get('T2'))}\n"
        f"<b>T3:</b> {safe(data.get('T3'))}\n"
        f"<b>RI:</b> {safe(data.get('RI'))}\n"
        f"<b>RC:</b> {safe(data.get('RC'))}"
    )

def is_admin(user_id):
    return user_id == ADMIN_ID

# ================== HANDLER ==================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type

    if chat_type in ("group", "supergroup"):
        if chat_id not in ALLOWED_GROUP_IDS:
            return

    is_muaf_group = chat_id in MUAF_GROUP_IDS

    user = update.effective_user
    user_id = user.id
    name = user.first_name
    color = get_user_color(user_id)

    text = update.message.text or update.message.caption or ""
    photos = update.message.photo

    tesisatlar = re.findall(r"\b\d+\b", text)
    now = time.time()

    if user_id in photo_timers:
        if now - photo_timers[user_id] > 120:
            photo_timers.pop(user_id, None)

    # ================= ADMIN =================

    if is_admin(user_id):

        cevap = f"{color} <b>{name}</b>\n━━━━━━━━━━━━━━━\n\n"
        sıra = 1

        for num in tesisatlar[:5]:
            endeks = get_endeks(num)

            cevap += (
                f"🔢 <b>{sıra}. Tesisat</b>\n"
                f"{endeks if endeks else NOT_FOUND_MSG}\n\n"
            )
            sıra += 1

        await update.message.reply_text(
            cevap,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # ================= MUAF =================

    if is_muaf_group and tesisatlar:

        cevap = f"{color} <b>{name}</b>\n━━━━━━━━━━━━━━━\n\n"
        sıra = 1

        for num in tesisatlar[:5]:
            endeks = get_endeks(num)

            cevap += (
                f"🔢 <b>{sıra}. Tesisat</b>\n"
                f"{endeks if endeks else NOT_FOUND_MSG}\n\n"
            )
            sıra += 1

        await update.message.reply_text(
            cevap,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # ================= FOTO + TESİSAT =================

    if photos and tesisatlar:

        photo_timers[user_id] = now

        cevap = f"{color} <b>{name}</b>\n━━━━━━━━━━━━━━━\n\n"
        sıra = 1

        for num in tesisatlar[:5]:
            endeks = get_endeks(num)

            cevap += (
                f"🔢 <b>{sıra}. Tesisat</b>\n"
                f"{endeks if endeks else NOT_FOUND_MSG}\n\n"
            )
            sıra += 1

        await update.message.reply_text(
            cevap,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # ================= SADECE FOTO =================

    if photos:
        photo_timers[user_id] = now
        return

    # ================= SADECE TESİSAT =================

    if tesisatlar and not photos:

        if user_id not in photo_timers:
            await update.message.reply_text("❗️ Önce fotoğraf göndermelisin.")
            return

        cevap = f"{color} <b>{name}</b>\n━━━━━━━━━━━━━━━\n\n"
        sıra = 1

        for num in tesisatlar[:5]:
            endeks = get_endeks(num)

            cevap += (
                f"🔢 <b>{sıra}. Tesisat</b>\n"
                f"{endeks if endeks else NOT_FOUND_MSG}\n\n"
            )
            sıra += 1

        await update.message.reply_text(
            cevap,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

# ================== BOT ==================

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

app.job_queue.run_repeating(update_data, interval=120, first=1)

load_data()

print("BOT BAŞLADI")

app.run_polling(drop_pending_updates=True)
