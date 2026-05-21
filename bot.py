import os
import time
import re
import pandas as pd

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

# ================== AYARLAR ==================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN bulunamadı!")

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
        print("DATA LOADED:", len(df))
    except Exception as e:
        print("CSV ERROR:", e)
        df = pd.DataFrame()

def get_endeks(num):
    if df.empty:
        return None

    if "Tesisat" not in df.columns:
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

# ================== STATE ==================

photo_state = {}
last_request = {}

def is_admin(uid):
    return uid == ADMIN_ID

# ================== HANDLER ==================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text or update.message.caption or ""
    photos = update.message.photo

    nums = re.findall(r"\d{6,12}", text)

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    now = time.time()

    # SPAM KORUMA
    if user_id in last_request:
        if now - last_request[user_id] < 3:
            return

    last_request[user_id] = now

    admin = is_admin(user_id)

    # FOTO GELDİ
    if photos:
        photo_state[user_id] = now

        if not nums:
            await update.message.reply_text("Fotoğraf alındı.")
            return

    if not nums:
        return

    # FOTO ZORUNLULUK (ADMIN HARİÇ)
    if not admin:
        if user_id not in photo_state:
            await update.message.reply_text("Önce fotoğraf göndermelisin.")
            return

        if now - photo_state[user_id] > 300:
            photo_state.pop(user_id, None)
            await update.message.reply_text("Fotoğraf süresi doldu.")
            return

    # RENK
    colors = ["🔴","🟠","🟡","🟢","🔵","🟣","⚫","⚪","🟤"]
    user_color = colors[user_id % len(colors)]

    # CEVAP
    msg = f"{user_color} <b>{user_name}</b>\n\n"

    i = 1
    for n in nums[:5]:
        endeks = get_endeks(n)
        msg += f"{i}. {endeks or 'Bulunamadı'}\n\n"
        i += 1

    await update.message.reply_text(msg, parse_mode="HTML")

    if not admin:
        photo_state.pop(user_id, None)

# ================== MAIN ==================

def main():

    print("BOT STARTED")

    load_data()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO,
            handler
        )
    )

    app.run_polling(
        drop_pending_updates=True
    )

# ================== RUN ==================

if __name__ == "__main__":
    main()
