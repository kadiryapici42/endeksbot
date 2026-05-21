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

MUAF_GROUP_IDS = [-1003989682635]

NOT_FOUND_MSG = "❗️ Tesisat numarası bulunamadı."

# ================== FLASK (RENDER FIX) ==================

web = Flask(__name__)

@web.route("/")
def home():
    return "Bot aktif"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)

def start():
    Thread(target=run_web, daemon=True).start()
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    print("BOT BAŞLADI")
    start()

# ================== MEMORY ==================

photo_timers = {}
user_colors = ["🔴", "🟢", "🔵", "🟡", "🟣", "🟠"]

def color(uid):
    return user_colors[uid % len(user_colors)]

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

        for c in df.columns:
            df[c] = df[c].str.strip()

        if "Tesisat" in df.columns:
            df["Tesisat"] = df["Tesisat"].str.replace(".0", "", regex=False)

        print("✅ Sheets güncellendi | Satır:", len(df))

    except Exception as e:
        print("❌ Sheets hata:", e)
        df = pd.DataFrame()

# ================== HELPERS ==================

def get_endeks(num):
    if df.empty:
        return None

    row = df[df["Tesisat"] == num]
    if row.empty:
        return None

    d = row.iloc[0]

    return (
        f"<b>{num}</b>\n"
        f"T1: {d.get('T1','')}\n"
        f"T2: {d.get('T2','')}\n"
        f"T3: {d.get('T3','')}\n"
        f"RI: {d.get('RI','')}\n"
        f"RC: {d.get('RC','')}"
    )

def is_admin(uid):
    return uid == ADMIN_ID

# ================== BOT HANDLER ==================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    chat_id = update.effective_chat.id

    if update.effective_chat.type in ("group", "supergroup"):
        if chat_id not in ALLOWED_GROUP_IDS:
            return

    is_muaf = chat_id in MUAF_GROUP_IDS

    user = update.effective_user
    uid = user.id
    name = user.first_name
    c = color(uid)

    text = update.message.text or update.message.caption or ""
    photos = update.message.photo

    nums = re.findall(r"\b\d+\b", text)
    now = time.time()

    # ================= FOTO GELDİ (SADECE FOTO) =================

    if photos and not nums:
        photo_timers[uid] = now
        return

    # foto + tesisat GELDİ
    if photos and nums:
        photo_timers[uid] = now

    # ================= ADMIN =================

    if is_admin(uid):

        msg = f"{c} <b>{name}</b>\n\n"
        i = 1

        for n in nums[:5]:
            msg += f"{i}. {get_endeks(n) or NOT_FOUND_MSG}\n\n"
            i += 1

        await update.message.reply_text(msg, parse_mode="HTML")
        return

    # ================= MUAF =================

    if is_muaf and nums:

        msg = f"{c} <b>{name}</b>\n\n"
        i = 1

        for n in nums[:5]:
            msg += f"{i}. {get_endeks(n) or NOT_FOUND_MSG}\n\n"
            i += 1

        await update.message.reply_text(msg, parse_mode="HTML")
        return

    # ================= TESİSAT =================

    if nums:

        if uid not in photo_timers:
            await update.message.reply_text("❗️ Önce fotoğraf göndermelisin.")
            return

        msg = f"{c} <b>{name}</b>\n\n"
        i = 1

        for n in nums[:5]:
            msg += f"{i}. {get_endeks(n) or NOT_FOUND_MSG}\n\n"
            i += 1

        await update.message.reply_text(msg, parse_mode="HTML")

# ================== MAIN ==================

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle))

load_data()

print("🤖 BOT BAŞLADI")

app.run_polling(drop_pending_updates=True)
