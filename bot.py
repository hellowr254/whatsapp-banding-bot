import os
import smtplib
import asyncio
from datetime import datetime
from email.mime.text import MIMEText
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import nest_asyncio

# ========== KONFIGURASI ==========
EMAIL_KAMU = os.getenv("EMAIL_KAMU")
PASSWORD_APLIKASI = os.getenv("PASSWORD_APLIKASI")
PENERIMA = os.getenv("PENERIMA", "support@whatsapp.com")
EMAIL_ADMIN = os.getenv("EMAIL_ADMIN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "8041562620").split(",")]
ALLOWED_USERS = set(ADMIN_IDS)
LOG_FILE = "bot_log.txt"
# =================================


# ======== FUNGSI TAMBAHAN ========
def buat_pesan_banding(nomor):
    return f"""
مرحباً فريق دعم واتساب،
أود الإبلاغ عن مشكلة في رقم واتساب الخاص بي {nomor}. عند محاولة التسجيل، تظهر لي رسالة "تسجيل الدخول غير متاح حالياً".

أتمنى أن يساعدني واتساب لأتمكن من استخدام رقمي {nomor} مجدداً دون هذه المشكلة. شكراً لاهتمامكم ومساعدتكم.
"""

def tulis_log(teks):
    waktu = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{waktu} {teks}\n")

def hanya_admin(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Kamu bukan admin, akses ditolak.")
            return
        return await func(update, context)
    return wrapper

def cek_izin(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_USERS:
            await update.message.reply_text(
                "🚫 Akses ditolak.\n\n"
                "Kamu belum memiliki izin menggunakan bot ini.\n"
                "Silakan hubungi admin untuk mendapatkan akses.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👤 Hubungi Admin", callback_data="hub_admin")]
                ]),
            )
            tulis_log(f"USER {user_id} coba akses tanpa izin.")
            return
        return await func(update, context)
    return wrapper


# ======== COMMAND HANDLER ========
@cek_izin
async def banding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Gunakan format:\n/banding +628XXXXXXXXXX")
        return

    nomor = context.args[0]
    teks_email = buat_pesan_banding(nomor)

    async def kirim_email():
        msg = MIMEText(teks_email)
        msg["Subject"] = f"My Number Can't Get Through {nomor}"
        msg["From"] = EMAIL_KAMU
        msg["To"] = PENERIMA

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
            server.starttls()
            server.login(EMAIL_KAMU, PASSWORD_APLIKASI)
            server.send_message(msg)
            server.quit()

            await update.message.reply_text(f"✅ Email banding untuk {nomor} sudah dikirim bos! 🚀")
            tulis_log(f"USER {user_id} kirim banding untuk {nomor} ✅")

            # Kirim laporan ke admin
            laporan = MIMEText(
                f"User {user_id} baru saja mengirim banding untuk nomor {nomor}.\n"
                f"Pesan telah dikirim ke support@whatsapp.com."
            )
            laporan["Subject"] = f"[Laporan Bot] User {user_id} kirim banding"
            laporan["From"] = EMAIL_KAMU
            laporan["To"] = EMAIL_ADMIN

            server = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
            server.starttls()
            server.login(EMAIL_KAMU, PASSWORD_APLIKASI)
            server.send_message(laporan)
            server.quit()

            tulis_log(f"Laporan email ke admin terkirim untuk nomor {nomor}")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Gagal mengirim email:\n{e}")
            tulis_log(f"ERROR kirim email {nomor}: {e}")

    asyncio.create_task(kirim_email())


# ======== MENU START ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in ALLOWED_USERS:
        keyboard = [
            [
                InlineKeyboardButton("🟢 Kirim Banding", callback_data="banding_menu"),
                InlineKeyboardButton("👤 Hubungi Admin", callback_data="hub_admin"),
            ]
        ]
        await update.message.reply_text(
            "LANGSUNG GAS 🚀\n\nPilih menu di bawah ini:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        tulis_log(f"USER {user_id} buka menu start (authorized)")
    else:
        keyboard = [[InlineKeyboardButton("👤 Hubungi Admin", callback_data="hub_admin")]]
        await update.message.reply_text(
            "🚫 Kamu belum punya akses.\nSilakan hubungi admin untuk izin.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        tulis_log(f"USER {user_id} buka menu start (unauthorized)")


# ======== HANDLER UNTUK TOMBOL ========
async def tombol_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "banding_menu":
        await query.message.reply_text("Gunakan format:\n/banding +6281234567890")
        tulis_log(f"USER {user_id} klik tombol 'Kirim Banding'")

    elif query.data == "hub_admin":
        await query.message.reply_text("@elbonss")
        tulis_log(f"USER {user_id} klik tombol 'Hubungi Admin'")


# ======== ADMIN COMMANDS ========
@hanya_admin
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Gunakan format: /adduser <id_telegram>")
        return
    try:
        user_id = int(context.args[0])
        ALLOWED_USERS.add(user_id)
        await update.message.reply_text(f"✅ User {user_id} berhasil ditambahkan ke whitelist.")
        tulis_log(f"[ADMIN] Tambah user {user_id}")
    except ValueError:
        await update.message.reply_text("⚠️ ID harus berupa angka.")


@hanya_admin
async def del_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Gunakan format: /deluser <id_telegram>")
        return
    try:
        user_id = int(context.args[0])
        if user_id in ADMIN_IDS:
            await update.message.reply_text("⚠️ Tidak bisa menghapus admin.")
            return
        if user_id in ALLOWED_USERS:
            ALLOWED_USERS.remove(user_id)
            await update.message.reply_text(f"🗑️ User {user_id} dihapus dari whitelist.")
            tulis_log(f"[ADMIN] Hapus user {user_id}")
        else:
            await update.message.reply_text("❗ User tidak ditemukan di whitelist.")
    except ValueError:
        await update.message.reply_text("⚠️ ID harus berupa angka.")


@hanya_admin
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    daftar = "\n".join(str(uid) for uid in ALLOWED_USERS)
    await update.message.reply_text(f"👥 Pengguna terdaftar:\n\n{daftar}")
    tulis_log("[ADMIN] Lihat daftar user")


# ======== MAIN PROGRAM ========
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("banding", banding))
    app.add_handler(CommandHandler("adduser", add_user))
    app.add_handler(CommandHandler("deluser", del_user))
    app.add_handler(CommandHandler("listusers", list_users))
    app.add_handler(CallbackQueryHandler(tombol_handler))

    print("🤖 Bot Banding WhatsApp Aktif")
    tulis_log("=== BOT DIMULAI ===")
    await app.run_polling(close_loop=False)


if __name__ == "__main__":
    nest_asyncio.apply()
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())