import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from datetime import datetime, timedelta

BOT_TOKEN = "7706614559:AAFLwSDRBjhk6F7XpVgNJmDlh7lh_6R0KXM"
ADMIN_ID = 7017391282
PREMIUM_FILE = "premium_users.json"

ASK_NUMBER, ASK_SCREENSHOT = range(2)

if os.path.exists(PREMIUM_FILE):
    with open(PREMIUM_FILE, "r") as f:
        premium_users = json.load(f)
else:
    premium_users = {}


def save_premium():
    with open(PREMIUM_FILE, "w") as f:
        json.dump(premium_users, f)


def is_premium(user_id: str):
    data = premium_users.get(user_id)
    if not data:
        return False
    expiry = datetime.strptime(data["expiry"], "%Y-%m-%d %H:%M")
    return datetime.now() < expiry


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if not is_premium(user_id):
        await update.message.reply_text(
            "❌ You are not a premium member or your plan has expired.\n\n💎 Buy Premium Plans:\n"
            "1 Month – $1000\n5 Months – $3000\n1 Year – $10000\n\n"
            "Contact serious only: @ethyr"
        )
        return ConversationHandler.END

    for msg in context.user_data.get("to_delete", []):
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg)
        except:
            pass
    context.user_data["to_delete"] = []

    welcome = await update.message.reply_text(
        f"👋 Hi {update.effective_user.first_name}, you are a Premium Member!\n\n"
        f"Use /mypremium to check your plan.\n\nPlease send your WhatsApp number to continue your unban request."
    )
    context.user_data["to_delete"].append(welcome.message_id)
    context.user_data["start_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return ASK_NUMBER


async def get_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['number'] = update.message.text
    msg = await update.message.reply_text("📸 Now please send a screenshot image related to your unban issue.")
    context.user_data["to_delete"].append(update.message.message_id)
    context.user_data["to_delete"].append(msg.message_id)
    return ASK_SCREENSHOT


async def get_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
        context.user_data['screenshot'] = photo_file_id

        keyboard = [
            [
                InlineKeyboardButton("✅ Done", callback_data="done"),
                InlineKeyboardButton("❌ Reject", callback_data="reject")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        caption = (
            f"📩 New Unban Request\n\n"
            f"👤 User: {update.effective_user.full_name} (@{update.effective_user.username})\n"
            f"📅 Date: {context.user_data['start_date']}\n"
            f"📱 Number: {context.user_data['number']}\n"
            f"🆔 User ID: {update.effective_user.id}"
        )

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file_id,
            caption=caption,
            reply_markup=reply_markup
        )

        note = await update.message.reply_text(
            "✅ Your unban request has been sent to admin.\n🕒 Time taken: 0–7 days.\n\nTo do another order, click /start again."
        )
        context.user_data["to_delete"].append(update.message.message_id)
        context.user_data["to_delete"].append(note.message_id)
        return ConversationHandler.END
    else:
        err = await update.message.reply_text("⚠️ Please send a valid screenshot image.")
        context.user_data["to_delete"].append(update.message.message_id)
        context.user_data["to_delete"].append(err.message_id)
        return ASK_SCREENSHOT


async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    caption = query.message.caption
    user_id = int(caption.split("User ID:")[1].strip())

    if query.data == "done":
        await context.bot.send_message(chat_id=user_id, text="✅ Your WhatsApp unban was completed successfully!")
        await query.edit_message_caption(caption=caption + "\n\n✅ Marked as Done by Admin.")
    else:
        await context.bot.send_message(chat_id=user_id, text="❌ Your unban request was rejected due to an error.")
        await query.edit_message_caption(caption=caption + "\n\n❌ Marked as Rejected by Admin.")


async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ You are not authorized.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /premium <user_id> <1month|5month|1year>")
        return

    user_id = context.args[0]
    duration = context.args[1].lower()

    if duration not in ["1month", "5month", "1year"]:
        await update.message.reply_text("❌ Invalid duration. Use: 1month, 5month, or 1year.")
        return

    now = datetime.now()
    if duration == "1month":
        expiry = now + timedelta(days=30)
    elif duration == "5month":
        expiry = now + timedelta(days=150)
    elif duration == "1year":
        expiry = now + timedelta(days=365)

    premium_users[user_id] = {
        "start": now.strftime("%Y-%m-%d %H:%M"),
        "plan": duration,
        "expiry": expiry.strftime("%Y-%m-%d %H:%M")
    }
    save_premium()

    await update.message.reply_text(f"✅ User {user_id} granted premium ({duration}).")
    try:
        msg = await context.bot.send_message(
            chat_id=int(user_id),
            text=f"🎉 You bought premium on {now.strftime('%Y-%m-%d %H:%M')}\nYour plan: {duration}\nExpires on: {expiry.strftime('%Y-%m-%d %H:%M')}\nUse /mypremium to check your plan."
        )
    except:
        pass


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ You are not authorized.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /cancel <user_id>")
        return

    user_id = context.args[0]
    if user_id in premium_users:
        del premium_users[user_id]
        save_premium()
        await update.message.reply_text(f"❌ Premium cancelled for user {user_id}")
        try:
            await context.bot.send_message(chat_id=int(user_id), text="🚫 Your premium access has been cancelled.")
        except:
            pass
    else:
        await update.message.reply_text("User is not in the premium list.")


async def mypremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in premium_users:
        await update.message.reply_text("❌ You are not a premium member.")
        return

    data = premium_users[user_id]
    expiry = datetime.strptime(data["expiry"], "%Y-%m-%d %H:%M")
    remaining = expiry - datetime.now()
    if remaining.total_seconds() < 0:
        await update.message.reply_text("⚠️ Your premium plan has expired.")
        return

    await update.message.reply_text(
        f"💎 Premium Plan Info:\n"
        f"🗓 Start: {data['start']}\n"
        f"📦 Plan: {data['plan']}\n"
        f"⏳ Expires: {data['expiry']}\n"
        f"🕒 Time left: {remaining.days} days"
    )


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = ' '.join(context.args)
    success = 0
    for user_id in premium_users:
        try:
            await context.bot.send_message(chat_id=int(user_id), text=f"📢 {message}")
            success += 1
        except:
            pass

    await update.message.reply_text(f"✅ Broadcast sent to {success} premium users.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💡 Available commands:\n/start – Start unban process\n/mypremium – View your premium info\n")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_number)],
            ASK_SCREENSHOT: [MessageHandler(filters.PHOTO, get_screenshot)],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(admin_buttons))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("mypremium", mypremium))
    app.add_handler(CommandHandler("help", help_command))

    print("🚀 Bot is running...")
    app.run_polling()


if __name__ == '__main__':
    main()
