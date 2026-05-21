import os
import time
import re
import pandas as pd
from threading import Thread
from flask import Flask

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

# ================== FLASK ==================

web = Flask(__name__)

@web.route("/")
def home():
    return "OK"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)

# ================== AYARLAR ==================

BOT_TOKEN = "8134035994:AAGbDKtDPADu0P59DthBkGDx7FZeIuewAKQ"
ADMIN_ID = 7311284778

CSV_URL = "https://docs.google.com/spreadsheets/d/1gwgQnpOnu4DB-T5c-eXoMAsNoeGIQTOp0v99cc4uJfc/export?format=csv&gid=0"

# ================== DATA ==================

df = pd.DataFrame()

def load_data():
    global df
    try:
        df = pd.read_csv(CSV_URL, dtype=str, encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
        df = df.fillna("")
        print("✅ Sheets yüklendi:", len(df))
    except Exception as e:
        print("❌ Sheets hata:", e)
        df = pd.DataFrame()

def get_endeks(num):
    if df.empty:
        return None

    row = df[df["Tesisat"] == str(num)]
    if row.empty:
        return None

    r = row.iloc[0]

    return (
        f"<b>{num}</b>\n"
        f"T1: {r.get('T1','')}\n"
        f"T2: {r.get('T2','')}\n"
        f"T3: {r.get('T3','')}\n"
        f"RI: {r.get('RI','')}\n"
        f"RC: {r.get('RC','')}"
    )

# ================== ADMIN ==================

def is_admin(uid):
    return uid == ADMIN_ID

# ================== BOT ==================

photo_state = {}

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text or update.message.caption or ""
    photos = update.message.photo

    nums = re.findall(r"\b\d+\b", text)

    user_id = update.effective_user.id
    now = time.time()

    admin = is_admin(user_id)

    # FOTO GELDİ
    if photos:
        photo_state[user_id] = now

    # TESİSAT YOKSA ÇIK
    if not nums:
        return

    # ================= FOTO KONTROL =================
    # 🔥 ADMIN MUAF
    if not admin and user_id not in photo_state:
        await update.message.reply_text("❗️ Önce fotoğraf göndermelisin.")
        return

    # ================= CEVAP =================

    msg = ""
    i = 1

    for n in nums[:5]:
        endeks = get_endeks(n)
        msg += f"{i}. {endeks or '❗️ Bulunamadı'}\n\n"
        i += 1

    await update.message.reply_text(msg, parse_mode="HTML")

# ================== START ==================

def start():
    Thread(target=run_web, daemon=True).start()
    print("FLASK STARTED")

    load_data()
    print("DATA LOADED")

    app.run_polling(drop_pending_updates=True)

# ================== MAIN ==================

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handler))

if __name__ == "__main__":
    print("BOT STARTED")
    start()
