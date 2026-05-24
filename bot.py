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

# ================= FLASK =================

web = Flask(__name__)

@web.route("/")
def home():
    return "Bot aktif"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)

# ================= AYARLAR =================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

ADMIN_ID = 7311284778

# Google Sheets CSV linki
CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1gwgQnpOnu4DB-T5c-eXoMAsNoeGIQTOp0v99cc4uJfc/"
    "export?format=csv&gid=2103514594"
)

# ================= DATA =================

df = pd.DataFrame()

def load_data():

    global df

    try:

        yeni_df = pd.read_csv(
            CSV_URL,
            dtype=str,
            encoding="utf-8-sig"
        )

        yeni_df.columns = yeni_df.columns.str.strip()

        yeni_df = yeni_df.fillna("")

        # Tesisat kolonunu string yap
        yeni_df["Tesisat"] = (
            yeni_df["Tesisat"]
            .astype(str)
            .str.strip()
        )

        df = yeni_df

        print("DATA YÜKLENDİ:", len(df))

    except Exception as e:

        print("CSV HATASI:", e)

def auto_refresh():

    while True:

        try:

            load_data()

            print("DATA YENİLENDİ")

        except Exception as e:

            print("YENİLEME HATASI:", e)

        time.sleep(300)  # 5 dakika

def normalize(v):

    if v is None:
        return ""

    v = str(v).strip()

    if "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:
        v = v.replace(",", ".")

    return v

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
        f"T1: {normalize(r.get('T1', ''))}\n"
        f"T2: {normalize(r.get('T2', ''))}\n"
        f"T3: {normalize(r.get('T3', ''))}\n"
        f"RI: {normalize(r.get('RI', ''))}\n"
        f"RC: {normalize(r.get('RC', ''))}"
    )

# ================= STATE =================

photo_state = {}

last_request = {}

def is_admin(uid):
    return uid == ADMIN_ID

# ================= HANDLER =================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text or update.message.caption or ""

    photos = update.message.photo

    nums = re.findall(r"\d{6,12}", text)

    user_id = update.effective_user.id

    user_name = update.effective_user.first_name

    now = time.time()

    # SPAM ENGEL

    if user_id in last_request:

        if now - last_request[user_id] < 3:
            return

    last_request[user_id] = now

    admin = is_admin(user_id)

    # FOTO GELDİ

    if photos:

        photo_state[user_id] = now

        if not nums:

            await update.message.reply_text(
                "✅ Fotoğraf alındı."
            )

            return

    # TESİSAT YOK

    if not nums:
        return

    # FOTO KONTROL

    if not admin:

        if user_id not in photo_state:

            await update.message.reply_text(
                "❗ Önce fotoğraf göndermelisin."
            )

            return

        if now - photo_state[user_id] > 300:

            photo_state.pop(user_id, None)

            await update.message.reply_text(
                "⌛ Fotoğraf süresi doldu."
            )

            return

    # RENKLER

    colors = [
        "🔴",
        "🟠",
        "🟡",
        "🟢",
        "🔵",
        "🟣",
        "⚫",
        "⚪",
        "🟤"
    ]

    user_color = colors[user_id % len(colors)]

    # CEVAP

    msg = f"{user_color} <b>{user_name}</b>\n\n"

    i = 1

    for n in nums[:5]:

        endeks = get_endeks(n)

        msg += f"{i}. {endeks or '❌ Bulunamadı'}\n\n"

        i += 1

    await update.message.reply_text(
        msg,
        parse_mode="HTML"
    )

    # FOTO RESET

    if not admin:
        photo_state.pop(user_id, None)

# ================= MAIN =================

def main():

    print("BOT BAŞLADI")

    Thread(target=run_web, daemon=True).start()

    Thread(target=auto_refresh, daemon=True).start()

    load_data()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO,
            handler
        )
    )

    print("BOT AKTİF")

    # Eski mesajları da okusun
    app.run_polling(
        drop_pending_updates=False
    )

# ================= RUN =================

if __name__ == "__main__":
    main()
