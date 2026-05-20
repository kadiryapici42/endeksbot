import pandas as pd
import re
import time
import os
import asyncio
from flask import Flask
from threading import Thread

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== AYARLAR ==================

BOT_TOKEN = "8134035994:AAGbDKtDPADu0P59DthBkGDx7FZeIuewAKQ"
EXCEL_FILE = "tesisatlar.xlsx"

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

# ================== MEMORY ==================

photo_timers = {}
tesisat_counts = {}

user_colors = ["🔴","🟢","🔵","🟡","🟣","🟠"]

def get_user_color(user_id):
    return user_colors[user_id % len(user_colors)]

# ================== EXCEL ==================

def load_excel():
    try:
        if not os.path.exists(EXCEL_FILE):
            print("Excel bulunamadı:", EXCEL_FILE)
            return pd.DataFrame()

        df = pd.read_excel(EXCEL_FILE)
        df.columns = [c.strip() for c in df.columns]

        if "Tesisat" in df.columns:
            df["Tesisat"] = df["Tesisat"].astype(str).str.strip()

        return df

    except Exception as e:
        print("Excel hata:", e)
        return pd.DataFrame()

df = load_excel()

# ================== BACKGROUND UPDATE ==================

async def periodic_update():
    global df
    while True:
        df = load_excel()
        print("📊 Excel güncellendi")
        await asyncio.sleep(60)

# ================== HELPERS ==================

def safe(val):
    return "" if pd.isna(val) else val

def get_endeks(num):
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

# ================== MESSAGE HANDLER ==================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat
    chat_id = chat.id
    chat_type = chat.type

    if chat_type in ("group", "supergroup") and chat_id not in ALLOWED_GROUP_IDS:
        return

    is_muaf_group = chat_id in MUAF_GROUP_IDS

    user = update.effective_user
    user_id = user.id
    name = user.first_name
    color = get_user_color(user_id)

    text = update.message.text or update.message.caption or ""
    photos = update.message.photo

    tesisatlar = re.findall(r"\b\d+\b", text)

    if not tesisatlar and not photos:
        return

    # ================= ADMIN =================

    if is_admin(user_id):

        cevap = f"{color} <b>{name}</b>\n━━━━━━━━━━━━━━━\n\n"

        if len(tesisatlar) == 1:
            endeks = get_endeks(tesisatlar[0])
            cevap += f"{endeks if endeks else NOT_FOUND_MSG}\n"
        else:
            sıra = 1
            for num in tesisatlar:
                endeks = get_endeks(num)
                cevap += f"🔢 <b>{sıra}. Tesisat</b>\n{endeks or NOT_FOUND_MSG}\n\n"
                sıra += 1

        await update.message.reply_text(
            cevap,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    now = time.time()

    if user_id in photo_timers and now - photo_timers[user_id] > 120:
        photo_timers.pop(user_id, None)
        tesisat_counts.pop(user_id, None)

    # ================= MUAF GRUP =================

    if is_muaf_group and tesisatlar:

        tesisatlar = tesisatlar[:5]

        cevap = f"{color} <b>{name}</b>\n━━━━━━━━━━━━━━━\n\n"

        sıra = 1
        for num in tesisatlar:
            endeks = get_endeks(num)
            cevap += f"🔢 <b>{sıra}. Tesisat</b>\n{endeks or NOT_FOUND_MSG}\n\n"
            sıra += 1

        await update.message.reply_text(
            cevap,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # ================= FOTO + TESİSAT =================

    if photos and tesisatlar:

        tesisatlar = tesisatlar[:5]

        cevap = f"{color} <b>{name}</b>\n━━━━━━━━━━━━━━━\n\n"

        sıra = 1
        for num in tesisatlar:
            endeks = get_endeks(num)
            cevap += f"🔢 <b>{sıra}. Tesisat</b>\n{endeks or NOT_FOUND_MSG}\n\n"
            sıra += 1

        await update.message.reply_text(
            cevap,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

        photo_timers[user_id] = now
        tesisat_counts[user_id] = len(tesisatlar)
        return

    # ================= SADECE TESİSAT =================

    if tesisatlar and not photos:

        if user_id not in photo_timers:
            await update.message.reply_text("❗️ Önce fotoğraf göndermelisin.")
            return

        cevap = f"{color} <b>{name}</b>\n━━━━━━━━━━━━━━━\n\n"

        sıra = 1
        for num in tesisatlar:
            endeks = get_endeks(num)
            cevap += f"🔢 <b>{sıra}. Tesisat</b>\n{endeks or NOT_FOUND_MSG}\n\n"
            sıra += 1

        await update.message.reply_text(
            cevap,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    if photos:
        photo_timers[user_id] = now
        tesisat_counts[user_id] = 0
        return


# ================== BOT ==================

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(
    MessageHandler(filters.TEXT | filters.PHOTO, handle_message)
)

print("🤖 Bot aktif...")

# background task
asyncio.create_task(periodic_update())

# ================== FLASK ==================

app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot çalışıyor."

def run():
    app_flask.run(host="0.0.0.0", port=10000)

Thread(target=run).start()

# ================== START ==================

app.run_polling()
