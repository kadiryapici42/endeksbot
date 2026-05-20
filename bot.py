import pandas as pd
import re
import time
import os
import threading

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

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

MUAF_GROUP_IDS = [-1003989682635]

NOT_FOUND_MSG = "❗️ Tesisat numarası bulunamadı."

# ================== MEMORY ==================

df = pd.DataFrame()
photo_timers = {}
tesisat_counts = {}

user_colors = ["🔴","🟢","🔵","🟡","🟣","🟠"]

def color(uid):
    return user_colors[uid % len(user_colors)]

# ================== EXCEL ==================

def load_excel():
    global df
    try:
        if not os.path.exists(EXCEL_FILE):
            print("Excel yok")
            df = pd.DataFrame()
            return

        data = pd.read_excel(EXCEL_FILE)
        data.columns = [c.strip() for c in data.columns]

        if "Tesisat" in data.columns:
            data["Tesisat"] = data["Tesisat"].astype(str).str.strip()

        df = data
        print("📊 Excel güncellendi")

    except Exception as e:
        print("Excel hata:", e)
        df = pd.DataFrame()

# ================== HELP ==================

def safe(v):
    return "" if pd.isna(v) else v

def get_endeks(t):
    global df
    if df.empty:
        return None

    r = df[df["Tesisat"] == str(t)]
    if r.empty:
        return None

    x = r.iloc[0]

    return (
        f"<b>{t}</b>\n"
        f"T1: {safe(x.get('T1'))}\n"
        f"T2: {safe(x.get('T2'))}\n"
        f"T3: {safe(x.get('T3'))}\n"
        f"RI: {safe(x.get('RI'))}\n"
        f"RC: {safe(x.get('RC'))}"
    )

def is_admin(uid):
    return uid == ADMIN_ID

# ================== HANDLER ==================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat
    if chat.type in ("group", "supergroup") and chat.id not in ALLOWED_GROUP_IDS:
        return

    is_muaf = chat.id in MUAF_GROUP_IDS

    user = update.effective_user
    uid = user.id
    name = user.first_name
    col = color(uid)

    text = update.message.text or update.message.caption or ""
    photos = update.message.photo

    nums = re.findall(r"\b\d+\b", text)

    if not nums and not photos:
        return

    now = time.time()

    if uid in photo_timers and now - photo_timers[uid] > 120:
        photo_timers.pop(uid, None)
        tesisat_counts.pop(uid, None)

    # ================= ADMIN =================

    if is_admin(uid):
        msg = f"{col} <b>{name}</b>\n\n"

        for i, n in enumerate(nums[:10], 1):
            msg += f"{i}. {get_endeks(n) or NOT_FOUND_MSG}\n\n"

        await update.message.reply_text(msg, parse_mode="HTML")
        return

    # ================= MUAF =================

    if is_muaf and nums:
        msg = f"{col} <b>{name}</b>\n\n"

        for i, n in enumerate(nums[:5], 1):
            msg += f"{i}. {get_endeks(n) or NOT_FOUND_MSG}\n\n"

        await update.message.reply_text(msg, parse_mode="HTML")
        return

    # ================= PHOTO + TESİSAT =================

    if photos and nums:
        msg = f"{col} <b>{name}</b>\n\n"

        for i, n in enumerate(nums[:5], 1):
            msg += f"{i}. {get_endeks(n) or NOT_FOUND_MSG}\n\n"

        photo_timers[uid] = now
        tesisat_counts[uid] = len(nums)

        await update.message.reply_text(msg, parse_mode="HTML")
        return

    # ================= ONLY TESISAT =================

    if nums and not photos:

        if uid not in photo_timers:
            await update.message.reply_text("❗️ Önce fotoğraf gönder")
            return

        msg = f"{col} <b>{name}</b>\n\n"

        for i, n in enumerate(nums[:10], 1):
            msg += f"{i}. {get_endeks(n) or NOT_FOUND_MSG}\n\n"

        await update.message.reply_text(msg, parse_mode="HTML")
        return

    # ================= ONLY PHOTO =================

    if photos:
        photo_timers[uid] = now
        tesisat_counts[uid] = 0

# ================== BACKGROUND LOOP (SAFE) ==================

def excel_loop():
    while True:
        load_excel()
        time.sleep(60)

# ================== MAIN ==================

def main():

    load_excel()

    threading.Thread(target=excel_loop, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle))

    print("🤖 Bot aktif...")
    app.run_polling()

if __name__ == "__main__":
    main()
