import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)
import database as db

# Environment Variables irraa Fudhachuuf
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5558713786"))
VIP_CHANNEL_ID = int(os.getenv("VIP_CHANNEL_ID", "-1004305147982"))

# States for Registration Flow
NAME, PHONE, METHOD, TXID, SCREENSHOT = range(5)

# Payment Details
TELEBIRR_NO = "09XXXXXXXX (Gemechu Reta)"
MPESA_NO = "07XXXXXXXX (Gemechu Reta)"

logging.basicConfig(level=logging.INFO)

# STEP 1: /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🔥 **WELCOME TO PRICEACTION_SMC FX!**\n\n"
        "Welcome to our VIP Forex Master Class!\n\n"
        "**Learn:**\n"
        "• Price Action\n"
        "• Smart Money Concepts (SMC)\n"
        "• Risk Management\n"
        "• Trading Psychology\n"
        "• Live Trading Sessions\n\n"
        "To register for our VIP Master Class, click the button below."
    )
    keyboard = [[InlineKeyboardButton("📝 REGISTER NOW", callback_data="register")]]
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# STEP 2: Registration Flow
async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Please enter your **Full Name**:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['full_name'] = update.message.text
    await update.message.reply_text("Please enter your **Phone Number**:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("📱 Telebirr", callback_data="Telebirr")],
        [InlineKeyboardButton("📱 M-Pesa", callback_data="M-Pesa")]
    ]
    await update.message.reply_text("Select your preferred **Payment Method**:", reply_markup=InlineKeyboardMarkup(keyboard))
    return METHOD

# STEP 3: Payment Method Selection & Transaction ID
async def get_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data
    context.user_data['payment_method'] = method

    pay_info = TELEBIRR_NO if method == "Telebirr" else MPESA_NO
    text = (
        f"💰 **Payment Method Selected: {method}**\n\n"
        f"Please send the registration fee to:\n`{pay_info}`\n\n"
        f"After completing the transaction, please enter your **Transaction ID** below:"
    )
    await query.message.reply_text(text, parse_mode="Markdown")
    return TXID

async def get_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['txid'] = update.message.text
    await update.message.reply_text("Please upload the **Screenshot** of your payment receipt:")
    return SCREENSHOT

# STEP 4: Screenshot Upload & Sending to Admin
async def get_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo_id = update.message.photo[-1].file_id
    
    full_name = context.user_data['full_name']
    phone = context.user_data['phone']
    method = context.user_data['payment_method']
    txid = context.user_data['txid']

    # Database keessatti galmeessuu
    await db.add_student(user.id, full_name, user.username or "No Username", phone, method, txid)

    # Barataaf notification erguu
    await update.message.reply_text(
        "⏳ **Payment Pending Verification**\n\n"
        "Your details and payment receipt have been submitted.\n"
        "Our system and admin are reviewing your transaction. Once verified, you will receive your VIP link automatically!"
    )

    # Admin Dashboard-f erguu
    admin_keyboard = [
        [
            InlineKeyboardButton("🟢 Approve", callback_data=f"approve_{user.id}"),
            InlineKeyboardButton("🔴 Reject", callback_data=f"reject_{user.id}")
        ]
    ]
    admin_caption = (
        f"📌 **NEW REGISTRATION VERIFICATION**\n\n"
        f"👤 **Name:** {full_name}\n"
        f"📱 **Phone:** {phone}\n"
        f"🔗 **Username:** @{user.username}\n"
        f"💳 **Method:** {method}\n"
        f"🧾 **Transaction ID:** `{txid}`\n\n"
        f"Status: *PENDING VERIFICATION*"
    )
    
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=admin_caption,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(admin_keyboard)
    )
    return ConversationHandler.END

# STEP 5: Admin Approval Action & Automatic VIP Link Creation
async def handle_admin_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    action = data[0]
    student_id = int(data[1])

    if action == "approve":
        await db.update_status(student_id, "CONFIRMED")
        
        # Linkii Automatic kan nama 1 qofaf hojjetu uumuu
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=VIP_CHANNEL_ID,
            member_limit=1
        )

        success_msg = (
            "🎉 **PAYMENT SUCCESSFUL!**\n\n"
            "Congratulations!\n"
            "Your payment has been verified successfully.\n"
            "Welcome to PriceAction_SMC VIP Master Class!\n\n"
            "✅ Registration Completed\n"
            "✅ Payment Verified\n"
            "🚀 **VIP Access Ready**\n\n"
            f"Join VIP Channel: {invite_link.invite_link}\n\n"
            "💡 *Learn. Analyze. Trade.*"
        )
        await context.bot.send_message(chat_id=student_id, text=success_msg, parse_mode="Markdown")
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **STATUS: CONFIRMED & ACCESS GRANTED**")

    elif action == "reject":
        await db.update_status(student_id, "REJECTED")
        reject_msg = (
            "❌ **PAYMENT REJECTED**\n\n"
            "We could not verify your payment transaction ID or receipt.\n"
            "Please double-check your payment and contact support/admin if you believe this is an error."
        )
        await context.bot.send_message(chat_id=student_id, text=reject_msg, parse_mode="Markdown")
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ **STATUS: REJECTED**")

# ADMIN DASHBOARD COMMAND (/admin)
async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    total, confirmed, pending, rejected, telebirr, mpesa = await db.get_stats()

    dashboard_text = (
        "📊 **ADMIN DASHBOARD**\n\n"
        f"👥 **Total Registered:** {total}\n"
        f"✅ **Confirmed Payments:** {confirmed}\n"
        f"⏳ **Pending Payments:** {pending}\n"
        f"❌ **Rejected Payments:** {rejected}\n\n"
        f"📱 **Telebirr Payments:** {telebirr}\n"
        f"📱 **M-Pesa Payments:** {mpesa}\n"
    )
    await update.message.reply_text(dashboard_text, parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration process canceled.")
    return ConversationHandler.END

async def post_init(application):
    await db.init_db()

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_registration, pattern="^register\$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            METHOD: [CallbackQueryHandler(get_method)],
            TXID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_txid)],
            SCREENSHOT: [MessageHandler(filters.PHOTO, get_screenshot)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_dashboard))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_admin_approval, pattern="^(approve|reject)_"))

    print("Bot is live...")
    app.run_polling()

if __name__ == "__main__":
    main()
