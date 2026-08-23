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

# =========================================================
# FLASK
# =========================================================

web = Flask(__name__)


@web.route("/")
def home():
    return "Bot aktif"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    web.run(
        host="0.0.0.0",
        port=port
    )


# =========================================================
# AYARLAR
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

ADMIN_ID = 7311284778


# =========================================================
# GOOGLE SHEETS
# =========================================================

SPREADSHEET_ID = (
    "1gwgQnpOnu4DB-T5c-eXoMAsNoeGIQTOp0v99cc4uJfc"
)


# Google Sheets içerisindeki 6 sayfanın GID'leri

SHEET_GIDS = [
    "2103514594",
    "1165500074",
    "1464069935",
    "1766165080",
    "1438103280",
    "2112208933"
]


# =========================================================
# GRUPLAR
# =========================================================

# Fotoğraf zorunlu gruplar

ALLOWED_GROUP_IDS = [
    -1003159684647,
    -1003222476077,
    -1003174102297,
    -1003215786503,
    -4902679499,
    -1003980973190,
    -1003935191465,
    -5200096579,
    -5398794373,
    -5209111578,
    -5258624671,
    -5476158885,
    -5574415057,
    -5225883700,
    -5353316981,
    -5477787093
]


# Sınırsız / serbest grup

FREE_GROUP_IDS = [
    -1003989682635
]


# =========================================================
# DATA
# =========================================================

df = pd.DataFrame()


def load_data():

    global df

    print("")
    print("========================================")
    print("GOOGLE SHEETS VERİLERİ YÜKLENİYOR")
    print("========================================")

    dfs = []

    for gid in SHEET_GIDS:

        try:

            csv_url = (
                f"https://docs.google.com/spreadsheets/d/"
                f"{SPREADSHEET_ID}/"
                f"export?format=csv&gid={gid}"
            )

            print("")
            print(f"📄 SAYFA OKUNUYOR: {gid}")

            sheet_df = pd.read_csv(
                csv_url,
                dtype=str,
                encoding="utf-8-sig"
            )

            # Kolon isimlerini temizle

            sheet_df.columns = (
                sheet_df.columns
                .astype(str)
                .str.strip()
            )

            # Boş hücreleri boş metne çevir

            sheet_df = sheet_df.fillna("")


            # Tesisat kolonunu temizle

            if "Tesisat" in sheet_df.columns:

                sheet_df["Tesisat"] = (
                    sheet_df["Tesisat"]
                    .astype(str)
                    .str.strip()
                )


            # DataFrame'i listeye ekle

            dfs.append(sheet_df)

            print(
                f"✅ SAYFA YÜKLENDİ | "
                f"GID: {gid} | "
                f"Kayıt: {len(sheet_df)}"
            )


        except Exception as e:

            print(
                f"❌ SAYFA OKUNAMADI | "
                f"GID: {gid}"
            )

            print(
                f"HATA: {e}"
            )


    # Hiçbir sayfa okunamadıysa
    # mevcut veriyi silme

    if not dfs:

        print("")
        print("❌ HİÇBİR GOOGLE SHEETS SAYFASI YÜKLENEMEDİ")
        print("")

        return


    try:

        # =================================================
        # TÜM SAYFALARI BİRLEŞTİR
        # =================================================

        yeni_df = pd.concat(
            dfs,
            ignore_index=True
        )


        # =================================================
        # TESİSAT TEMİZLİĞİ
        # =================================================

        if "Tesisat" in yeni_df.columns:

            yeni_df["Tesisat"] = (
                yeni_df["Tesisat"]
                .astype(str)
                .str.strip()
            )


            # Boş tesisatları kaldır

            yeni_df = yeni_df[
                yeni_df["Tesisat"] != ""
            ]


            # Aynı tesisat birden fazla
            # sayfada varsa ilkini kullan

            yeni_df = yeni_df.drop_duplicates(
                subset=["Tesisat"],
                keep="first"
            )


        # Global dataframe'i güncelle

        df = yeni_df


        print("")
        print("========================================")
        print("✅ TÜM SAYFALAR BİRLEŞTİRİLDİ")
        print(f"📊 TOPLAM KAYIT: {len(df)}")
        print("========================================")
        print("")


    except Exception as e:

        print("")
        print("❌ VERİ BİRLEŞTİRME HATASI:")
        print(e)
        print("")


# =========================================================
# OTOMATİK VERİ YENİLEME
# =========================================================

def auto_refresh():

    while True:

        try:

            print("")
            print("🔄 VERİLER YENİLENİYOR...")

            load_data()


        except Exception as e:

            print(
                "❌ YENİLEME HATASI:",
                e
            )


        # 300 saniye = 5 dakika

        time.sleep(300)


# =========================================================
# NORMALIZE
# =========================================================

def normalize(v):

    if v is None:
        return ""

    v = str(v).strip()


    # Örnek:
    # 1.234,56 → 1234.56

    if "," in v and "." in v:

        v = (
            v
            .replace(".", "")
            .replace(",", ".")
        )


    # Örnek:
    # 1234,56 → 1234.56

    elif "," in v:

        v = v.replace(",", ".")


    return v


# =========================================================
# TESİSAT / ENDEKS BUL
# =========================================================

def get_endeks(num):

    if df.empty:

        return None


    if "Tesisat" not in df.columns:

        return None


    row = df[
        df["Tesisat"] == str(num)
    ]


    if row.empty:

        return None


    r = row.iloc[0]


    return (
        f"<b>{num}</b>\n"
        f"<b>T1:</b> {normalize(r.get('T1', ''))}\n"
        f"<b>T2:</b> {normalize(r.get('T2', ''))}\n"
        f"<b>T3:</b> {normalize(r.get('T3', ''))}\n"
        f"<b>RI:</b> {normalize(r.get('RI', ''))}\n"
        f"<b>RC:</b> {normalize(r.get('RC', ''))}"
    )


# =========================================================
# STATE
# =========================================================

photo_state = {}

last_request = {}


def is_admin(uid):

    return uid == ADMIN_ID


# =========================================================
# TELEGRAM HANDLER
# =========================================================

async def handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:

        return


    # =====================================================
    # MESAJ BİLGİLERİ
    # =====================================================

    text = (
        update.message.text
        or update.message.caption
        or ""
    )


    photos = update.message.photo


    # 6-12 haneli tesisat numaralarını bul

    nums = re.findall(
        r"\d{6,12}",
        text
    )


    user_id = (
        update.effective_user.id
    )


    user_name = (
        update.effective_user.first_name
    )


    chat_id = (
        update.effective_chat.id
    )


    # =====================================================
    # GRUP ID GÖSTER
    # =====================================================

    print(
        f"GRUP ADI: "
        f"{update.effective_chat.title} | "
        f"CHAT ID: {chat_id}"
    )


    # =====================================================
    # /id KOMUTU
    # =====================================================

    if text == "/id":

        await update.message.reply_text(
            f"Bu grubun ID'si:\n"
            f"<code>{chat_id}</code>",
            parse_mode="HTML"
        )

        return


    # =====================================================
    # ZAMAN
    # =====================================================

    now = time.time()


    admin = is_admin(
        user_id
    )


    # =====================================================
    # GRUP KONTROL
    # =====================================================

    allowed = (
        chat_id in ALLOWED_GROUP_IDS
    )


    free_group = (
        chat_id in FREE_GROUP_IDS
    )


    # Admin her yerde çalışabilir

    if (
        not allowed
        and not free_group
        and not admin
    ):

        return


    # =====================================================
    # SPAM ENGEL
    # =====================================================

    if (
        not free_group
        and not admin
    ):

        if user_id in last_request:

            if (
                now
                - last_request[user_id]
                < 3
            ):

                return


        last_request[user_id] = now


    # =====================================================
    # FOTOĞRAF GELDİ
    # =====================================================

    if photos:

        photo_state[user_id] = now


        # Sadece fotoğraf gönderildiyse

        if not nums:

            await update.message.reply_text(
                "✅ Fotoğraf alındı."
            )

            return


    # =====================================================
    # TESİSAT NUMARASI YOK
    # =====================================================

    if not nums:

        return


    # =====================================================
    # FOTOĞRAF KONTROL
    # =====================================================

    if (
        not admin
        and not free_group
    ):

        # Fotoğraf gönderilmemiş

        if user_id not in photo_state:

            await update.message.reply_text(
                "❗ Önce fotoğraf göndermelisin."
            )

            return


        # Fotoğrafın süresi 5 dakika

        if (
            now
            - photo_state[user_id]
            > 300
        ):

            photo_state.pop(
                user_id,
                None
            )


            await update.message.reply_text(
                "⌛ Fotoğraf süresi doldu."
            )

            return


    # =====================================================
    # KULLANICI RENKLERİ
    # =====================================================

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


    user_color = (
        colors[
            user_id % len(colors)
        ]
    )


    # =====================================================
    # CEVAP
    # =====================================================

    msg = (
        f"{user_color} "
        f"<b>{user_name}</b>\n"
        f"━━━━━━━━━━━━━━\n\n"
    )


    # Serbest grupta sınırsız
    # Normal gruplarda maksimum 5

    limit = (
        len(nums)
        if free_group
        else 5
    )


    i = 1


    for n in nums[:limit]:

        endeks = get_endeks(n)


        msg += (
            f"🔢 <b>{i}. Tesisat</b>\n"
            f"{endeks or '❌ Bulunamadı'}\n\n"
        )


        i += 1


    # =====================================================
    # TELEGRAM'A CEVAP GÖNDER
    # =====================================================

    await update.message.reply_text(
        msg,
        parse_mode="HTML"
    )


    # =====================================================
    # FOTOĞRAF STATE RESET
    # =====================================================

    if (
        not admin
        and not free_group
    ):

        photo_state.pop(
            user_id,
            None
        )


# =========================================================
# MAIN
# =========================================================

def main():

    print("")
    print("========================================")
    print("🚀 BOT BAŞLADI")
    print("========================================")
    print("")


    # Flask

    Thread(
        target=run_web,
        daemon=True
    ).start()


    # Google Sheets otomatik yenileme

    Thread(
        target=auto_refresh,
        daemon=True
    ).start()


    # İlk veri yükleme

    load_data()


    # Telegram bot

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO,
            handler
        )
    )


    print("")
    print("========================================")
    print("🤖 BOT AKTİF")
    print("========================================")
    print("")


    app.run_polling(
        drop_pending_updates=False
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
