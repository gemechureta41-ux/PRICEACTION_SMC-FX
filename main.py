import os
import logging
import sqlite3
import asyncio
from aiohttp import web

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

NAME, PHONE, PAYMENT_METHOD, TRANSACTION_ID, SCREENSHOT = range(5)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()
VIP_CHANNEL_LINK = os.getenv("VIP_CHANNEL_LINK", "https://t.me/+p8VcsdP-k2FmMjk0").strip()

VIP_PRICE = os.getenv("VIP_PRICE", "3599 ETB")
TELEBIRR_NO = os.getenv("TELEBIRR_NO", "0917091612")
MPESA_NO = os.getenv("MPESA_NO", "0717120607")
ACCOUNT_NAME = os.getenv("ACCOUNT_NAME", "Gemechu Reta")
DATABASE_PATH = os.getenv("DATABASE_PATH", "payments.sqlite3")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in Render Environment.")

if not ADMIN_CHAT_ID.lstrip("-").isdigit():
    raise RuntimeError("ADMIN_CHAT_ID must be a numeric Telegram ID.")

if not VIP_CHANNEL_LINK:
    raise RuntimeError("VIP_CHANNEL_LINK is missing in Render Environment.")

ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)


def db_connect():
    return sqlite3.connect(DATABASE_PATH, timeout=30)


def init_db():
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                username TEXT NOT NULL,
                phone TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING'
            )
        """)


def save_payment(user_id, details):
    with db_connect() as conn:
        conn.execute("""
            INSERT INTO payments
            (user_id, full_name, username, phone,
             payment_method, transaction_id, status)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
            ON CONFLICT(user_id) DO UPDATE SET
                full_name=excluded.full_name,
                username=excluded.username,
                phone=excluded.phone,
                payment_method=excluded.payment_method,
                transaction_id=excluded.transaction_id,
                status='PENDING'
        """, (
            user_id,
            details["full_name"],
            details["username"],
            details["phone"],
            details["payment_method"],
            details["transaction_id"],
        ))


def get_payment(user_id):
    with db_connect() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM payments WHERE user_id = ?",
            (user_id,),
        ).fetchone()


def set_status(user_id, status):
    with db_connect() as conn:
        conn.execute(
            "UPDATE payments SET status = ? WHERE user_id = ?",
            (status, user_id),
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "WELCOME TO PRICEACTION_SMC FX!\n"
        "Welcome to our VIP Forex Master Class!\n\n"
        f"Price: {VIP_PRICE}\n\n"
        "Learn:\n"
        "• Price Action\n"
        "• Smart Money Concepts (SMC)\n"
        "• Risk Management\n"
        "• Trading Psychology\n"
        "• Live Trading Sessions\n\n"
        "To register, click the button below."
    )

    keyboard = [[
        InlineKeyboardButton("REGISTER NOW", callback_data="register")
    ]]

    if update.effective_message:
        await update.effective_message.reply_text(
            welcome,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    return ConversationHandler.END


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    await query.message.reply_text("Please enter your full name:")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = (update.message.text or "").strip()

    if len(name) < 2:
        await update.message.reply_text("Enter your full name:")
        return NAME

    context.user_data["full_name"] = name
    username = update.effective_user.username
    context.user_data["username"] = f"@{username}" if username else "No username"

    await update.message.reply_text("Please enter your phone number:")
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = (update.message.text or "").strip()

    if len(phone) < 7:
        await update.message.reply_text("Phone number is too short. Please enter it again:")
        return PHONE

    context.user_data["phone"] = phone
    keyboard = [
        [InlineKeyboardButton("Telebirr", callback_data="pay_Telebirr")],
        [InlineKeyboardButton("M-Pesa", callback_data="pay_M-Pesa")],
    ]

    await update.message.reply_text("Please select your payment method:", reply_markup=InlineKeyboardMarkup(keyboard))
    return PAYMENT_METHOD


async def select_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    method = query.data.removeprefix("pay_")
    if method not in ("Telebirr", "M-Pesa"):
        await query.message.reply_text("Invalid payment method. Send /start to try again.")
        return ConversationHandler.END

    context.user_data["payment_method"] = method
    number = TELEBIRR_NO if method == "Telebirr" else MPESA_NO

    await query.message.reply_text(
        f"Payment method: {method}\n\n"
        f"Amount: {VIP_PRICE}\n"
        f"Account name: {ACCOUNT_NAME}\n"
        f"Account number: {number}\n\n"
        "After paying, send your transaction ID."
    )
    return TRANSACTION_ID


async def get_transaction_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    transaction_id = (update.message.text or "").strip()

    if len(transaction_id) < 3:
        await update.message.reply_text("Please enter a valid transaction ID:")
        return TRANSACTION_ID

    context.user_data["transaction_id"] = transaction_id
    await update.message.reply_text("Now send your payment screenshot as a photo.")
    return SCREENSHOT


async def get_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Please send the screenshot as a photo, not as a document.")
        return SCREENSHOT

    user_id = update.effective_user.id
    details = {
        "full_name": context.user_data["full_name"],
        "username": context.user_data["username"],
        "phone": context.user_data["phone"],
        "payment_method": context.user_data["payment_method"],
        "transaction_id": context.user_data["transaction_id"],
    }

    try:
        save_payment(user_id, details)
    except Exception:
        logger.exception("Database save failed")
        await update.message.reply_text("Could not save your request. Please try again later.")
        return ConversationHandler.END

    caption = (
        "NEW PAYMENT — PENDING VERIFICATION\n\n"
        f"Name: {details['full_name']}\n"
        f"Telegram: {details['username']}\n"
        f"User ID: {user_id}\n"
        f"Phone: {details['phone']}\n"
        f"Method: {details['payment_method']}\n"
        f"Amount: {VIP_PRICE}\n"
        f"Transaction ID: {details['transaction_id']}\n\n"
        "Verify the payment in your account before approving."
    )

    keyboard = [[
        InlineKeyboardButton("Approve", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("Reject", callback_data=f"reject_{user_id}"),
    ]]

    try:
        await context.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=update.message.photo[-1].file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception:
        logger.exception("Could not notify admin")
        await update.message.reply_text("Your request was saved, but admin notification failed. Please contact support.")
        return ConversationHandler.END

    await update.message.reply_text(
        "PAYMENT PENDING\n\n"
        "Your payment is waiting for admin verification. "
        "If approved, your VIP invite link will be sent here."
    )
    return ConversationHandler.END


async def invalid_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your screenshot as a photo.")
    return SCREENSHOT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Registration cancelled. Send /start to begin again.")
    return ConversationHandler.END


async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != ADMIN_CHAT_ID:
        await query.answer("You are not authorized to do this.", show_alert=True)
        return

    await query.answer()
    action, raw_user_id = query.data.split("_", 1)
    user_id = int(raw_user_id)

    payment = get_payment(user_id)
    if payment is None:
        await query.message.reply_text("Payment record not found.")
        return

    if payment["status"] != "PENDING":
        await query.answer("This payment has already been processed.", show_alert=True)
        return

    if action == "approve":
        set_status(user_id, "CONFIRMED")
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "PAYMENT APPROVED!\n\n"
                    "Your payment has been verified.\n"
                    "Welcome to PriceAction_SMC VIP Master Class!\n\n"
                    f"VIP invite link: {VIP_CHANNEL_LINK}\n\n"
                    "Learn. Analyze. Trade."
                ),
                disable_web_page_preview=True,
            )
            status = "APPROVED — invite link sent"
        except Exception:
            logger.exception("Could not message user %s", user_id)
            status = "APPROVED — user message failed. Ask the user to start the bot."

    elif action == "reject":
        set_status(user_id, "REJECTED")
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "PAYMENT NOT APPROVED\n\n"
                    "Your payment could not be verified. "
                    "Please check your transaction details or contact admin."
                ),
            )
        except Exception:
            logger.exception("Could not message user %s", user_id)
        status = "REJECTED"
    else:
        return

    old_caption = query.message.caption or ""
    await query.edit_message_caption(
        caption=f"{old_caption}\n\nSTATUS: {status}",
        reply_markup=None,
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled bot error", exc_info=context.error)


async def handle_web(request):
    return web.Response(text="Bot is running smoothly!")

async def start_web_server():
    app_web = web.Application()
    app_web.router.add_get("/", handle_web)
    runner = web.AppRunner(app_web)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Fake web server started on port {port}")


async def main():
    init_db()

    app = Application.builder().token(TOKEN).build()

    registration = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_registration, pattern=r"^register$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            PAYMENT_METHOD: [CallbackQueryHandler(select_payment, pattern=r"^pay_(Telebirr|M-Pesa)$")],
            TRANSACTION_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_transaction_id)],
            SCREENSHOT: [
                MessageHandler(filters.PHOTO, get_screenshot),
                MessageHandler(filters.ALL & ~filters.COMMAND, invalid_screenshot),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(registration)
    app.add_handler(CallbackQueryHandler(admin_decision, pattern=r"^(approve|reject)_\d+$"))
    app.add_error_handler(error_handler)

    await start_web_server()

    logger.info("Bot is starting polling...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    stop_signal = asyncio.Event()
    await stop_signal.wait()


if __name__ == "__main__":
    asyncio.run(main())
