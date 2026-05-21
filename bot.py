import os
import re
import time
import logging
import pandas as pd

from threading import Thread
from flask import Flask

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# =====================================================
# FLASK
# =====================================================

web = Flask(__name__)

@web.route("/")
def home():
    return "BOT AKTIF"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)

# =====================================================
# AYARLAR
# =====================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1gwgQnpOnu4DB-T5c-eXoMAsNoeGIQTOp0v99cc4uJfc/"
    "export?format=csv&gid=0"
)

# =====================================================
# DATA
# =====================================================

df = pd.DataFrame()


def load_data():
    global df

    try:
        df = pd.read_csv(CSV_URL, dtype=str, encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
        df = df.fillna("")

        logger.info(f"Sheets yüklendi: {len(df)} kayıt")

    except Exception as e:
        logger.error(f"Sheets yükleme hatası: {e}")
        df = pd.DataFrame()


def get_endeks(num):

    if df.empty:
        return None

    row = df[df["Tesisat"] == str(num)]

    if row.empty:
        return None

    r = row.iloc[0]

    return (
        f"<blockquote>"
        f"<b>📌 TESİSAT:</b> <code>{num}</code>\n"
        f"<b>🔴 T1:</b> {r.get('T1', '')}\n"
        f"<b>🟠 T2:</b> {r.get('T2', '')}\n"
        f"<b>🟢 T3:</b> {r.get('T3', '')}\n"
        f"<b>🔵 RI:</b> {r.get('RI', '')}\n"
        f"<b>🟣 RC:</b> {r.get('RC', '')}"
        f"</blockquote>"
    )

# =====================================================
# ADMIN
# =====================================================


def is_admin(user_id):
    return user_id == ADMIN_ID

# =====================================================
# GLOBAL STATE
# =====================================================

photo_state = {}
last_request = {}

PHOTO_TIMEOUT = 300
SPAM_TIMEOUT = 3

# =====================================================
# HANDLER
# =====================================================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        if not update.message:
            return

        user = update.effective_user

        if not user:
            return

        user_id = user.id

        now = time.time()

        text = update.message.text or update.message.caption or ""

        photos = update.message.photo

        admin = is_admin(user_id)

        # =================================================
        # SPAM KORUMA
        # =================================================

        if user_id in last_request:

            if now - last_request[user_id] < SPAM_TIMEOUT:
                return

        last_request[user_id] = now

        # =================================================
        # FOTO GELDİ
        # =================================================

        if photos:

            photo_state[user_id] = now

            await update.message.reply_text(
                "✅ Fotoğraf alındı. Şimdi tesisat numarasını gönderebilirsin."
            )

            return

        # =================================================
        # TESİSAT NUMARASI BUL
        # =================================================

        nums = re.findall(r"\b\d+\b", text)

        if not nums:
            return

        # =================================================
        # FOTOĞRAF KONTROL
        # =================================================

        if not admin:

            if user_id not in photo_state:

                await update.message.reply_text(
                    "❗ Önce sayaç fotoğrafı göndermelisin."
                )

                return

            # FOTOĞRAF SÜRESİ
            if now - photo_state[user_id] > PHOTO_TIMEOUT:

                photo_state.pop(user_id, None)

                await update.message.reply_text(
                    "⌛ Fotoğraf süresi doldu. Tekrar fotoğraf gönder."
                )

                return

        # =================================================
        # CEVAP OLUŞTUR
        # =================================================

        msg = "<b>📋 ENDEKS SONUÇLARI</b>\n\n"

        i = 1

        for n in nums[:5]:

            endeks = get_endeks(n)

            if endeks:
                msg += f"{i}. {endeks}\n\n"
            else:
                msg += (
                    f"{i}. <b>{n}</b> ❌ Bulunamadı\n\n"
                )

            i += 1

        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.HTML
        )

        # =================================================
        # TEK KULLANIMLIK FOTO
        # =================================================

        if not admin:
            photo_state.pop(user_id, None)

    except Exception as e:

        logger.error(f"Handler hata: {e}")

        try:
            await update.message.reply_text(
                "❌ Bir hata oluştu. Tekrar deneyin."
            )
        except:
            pass

# =====================================================
# START
# =====================================================

def start():

    Thread(target=run_web, daemon=True).start()

    logger.info("Flask başlatıldı")

    load_data()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO,
            handler
        )
    )

    logger.info("Bot polling başlatılıyor")

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    logger.info("BOT STARTED")

    start()
