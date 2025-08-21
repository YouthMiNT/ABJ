import logging
import re
import os
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# --- CONFIGURATION ---
BOT_TOKEN = os.environ['BOT_TOKEN']
ADMIN_ID = os.environ['ADMIN_ID']
CHANNEL_ID = os.environ['CHANNEL_ID']
USER_DATA_CHANNEL_ID = os.environ['USER_DATA_CHANNEL_ID']


# --- PAYMENT INFORMATION ---
PAYMENT_INSTRUCTIONS = (
    "The one-time access fee is *99 ETB*.\n\n"
    "Please make your payment to one of the following accounts:\n\n"
    "🏦 *CBE Account:*\n`1000417007192`\n*Name:* `ABDULMEJID SEHAB`\n\n"
    "📱 *Telebirr:*\n`0927429565`\n*Name:* `ABDULMEJID SEHAB`\n\n"
    "Then, upload a clear screenshot of the receipt below."
)

# --- BOT TEXTS (Updated) ---
CONTACT_TEXT = (
    "📞 *Contact Support*\n\n"
    "If you have any issues, please contact the admin directly:\n\n"
    "👤 *Telegram:* @Mejido\n"
    "📱 *Phone:* `0927429565`"
)



HELP_TEXT = (
    "🤝 *How to Get Access*\n\n"
    "*ABJ Tutorial Bot* is your gateway to essential study materials for Jimma University students.\n\n"
    "1️⃣ Press *'Start Payment'* on the main menu.\n"
    "2️⃣ Follow the prompts to enter your name and sex.\n"
    "3️⃣ Make the payment of *99 ETB* as per the instructions.\n"
    "4️⃣ Upload a clear payment screenshot.\n\n"
    "Once your submission is approved, you will receive a link to join the channel. "
    "Learn smart, stay ahead, and succeed with ABJ Tutorial!"
)
# ---------------------

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define states for the conversation
GET_NAME, GET_SEX, GET_PHOTO = range(3)

# --- Dynamic Keyboard Layouts ---
def get_admin_keyboard(context: ContextTypes.DEFAULT_TYPE) -> ReplyKeyboardMarkup:
    is_manual = context.bot_data.get('is_manual_mode', True)
    toggle_text = "⚙️ Switch to Auto-Approve" if is_manual else "⚙️ Switch to Manual Approve"
    keyboard = [[toggle_text], ["✅ Approved Users", "❌ Rejected Users"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

user_keyboard = [[ "Help", " Start Payment"], [" Contact"]]
submission_keyboard = [["❌ Cancel"]]

# --- Main /start & Menu Button Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if str(user.id) == ADMIN_ID:
        await update.message.reply_markdown( f"*Welcome Admin*,{user.first_name}", reply_markup=get_admin_keyboard(context))
    else:
        start_message = (
            f"Hello, * {user.first_name}  * Welcome to the *ABJ Tutorial Bot* – your study companion on Telegram!\n\n"
            "Empowering Tomorrow, Today.\n\n"
            
        )
        await update.message.reply_markdown(start_message, reply_markup=ReplyKeyboardMarkup(user_keyboard, resize_keyboard=True))

async def show_demo(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_markdown(DEMO_TEXT)
async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_markdown(HELP_TEXT)
async def show_contact(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_markdown(CONTACT_TEXT)

# --- Admin Panel Functions ---
async def toggle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) != ADMIN_ID: return
    is_manual = context.bot_data.get('is_manual_mode', True)
    context.bot_data['is_manual_mode'] = not is_manual
    mode_text = "✅ *Manual Approve Activated.*\nNew submissions will require your immediate action." if context.bot_data['is_manual_mode'] else "✅ *Auto-Approve Activated.*\nNew submissions will be collected for you to approve in-channel."
    await update.message.reply_markdown(mode_text, reply_markup=get_admin_keyboard(context))

async def show_approved_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) != ADMIN_ID: return
    approved = context.bot_data.get('approved_users', [])
    if not approved: return await update.message.reply_text("There are no approved users in the history yet.")
    await update.message.reply_markdown(f"*--- History: {len(approved)} Approved User(s) ---*")
    for user_data in approved:
        await context.bot.send_photo(ADMIN_ID, user_data['photo_id'], caption=f"✅ Name: {user_data['full_name']}\n🔗 Username: {user_data['username']}")

async def show_rejected_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) != ADMIN_ID: return
    rejected = context.bot_data.get('rejected_users', [])
    if not rejected: return await update.message.reply_text("There are no rejected users in the history yet.")
    await update.message.reply_markdown(f"*--- History: {len(rejected)} Rejected User(s) ---*")
    for user_data in rejected:
        await context.bot.send_photo(ADMIN_ID, user_data['photo_id'], caption=f"❌ Name: {user_data['full_name']}\n🔗 Username: {user_data['username']}")

# --- User Payment Conversation ---
async def start_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    if any(user['user_id'] == int(user_id) for user in context.bot_data.get('approved_users', [])):
        await update.message.reply_text("You are already a member of our channel!")
        return ConversationHandler.END
    if user_id in context.bot_data.get('pending_submissions', {}):
        await update.message.reply_text("You already have a payment submission under review. Please wait for the admin to respond.")
        return ConversationHandler.END
    await update.message.reply_markdown("📝 *Payment*\n\nPlease enter your *Full Name* ", reply_markup=ReplyKeyboardMarkup(submission_keyboard, resize_keyboard=True))
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text
    if not re.fullmatch(r'[A-Za-z\s]+', name):
        await update.message.reply_text("That doesn't look like a valid name. Please use letters and spaces only.")
        return GET_NAME
    context.user_data['full_name'] = name
    keyboard = [[InlineKeyboardButton("🚹 Male", callback_data="Male"), InlineKeyboardButton("🚺 Female", callback_data="Female")]]
    await update.message.reply_text("✅ Great! Now, please select your sex.", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_SEX

async def get_sex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['sex'] = query.data
    await query.edit_message_text(PAYMENT_INSTRUCTIONS, parse_mode='Markdown')
    return GET_PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_id_str = str(user.id)
    submission_data = {'user_id': user.id, 'full_name': context.user_data.get('full_name', 'N/A'), 'sex': context.user_data.get('sex', 'N/A'),
                       'tg_name': user.full_name, 'username': f"@{user.username}" if user.username else "Not set", 'photo_id': update.message.photo[-1].file_id}
    context.bot_data.setdefault('pending_submissions', {})[user_id_str] = submission_data

    caption = (
        f"👤 *Full Name :* {submission_data['full_name']}\n"
        f"🏷️ *Telegram Name:* {submission_data['tg_name']}\n"
        f"🔗 *Username:* {submission_data['username']}"
    )

    is_manual = context.bot_data.get('is_manual_mode', True)
    if is_manual:
        keyboard = [[InlineKeyboardButton("✅ Approve (One-Time Link)", callback_data=f"approve_manual_{user.id}"), 
                     InlineKeyboardButton("❌ Reject", callback_data=f"reject_manual_{user.id}")]]
        await context.bot.send_photo(ADMIN_ID, submission_data['photo_id'], caption=f"🚨 *Manual Review Request* 🚨\n\n{caption}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        keyboard = [[InlineKeyboardButton("Approve ✅", callback_data=f"approve_auto_{user.id}"), 
                     InlineKeyboardButton("Reject ❌", callback_data=f"reject_auto_{user.id}")]]
        await context.bot.send_photo(ADMIN_ID, submission_data['photo_id'], caption=f"📬 *Auto-Approval Submission*\n\n{caption}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        join_button = [[InlineKeyboardButton("➡️ Request to Join Channel", url=REQUEST_TO_JOIN_LINK)]]
        await context.bot.send_message(user.id, "Please click the button below to send your join request to the channel.", reply_markup=InlineKeyboardMarkup(join_button))
    

async def cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Payment process cancelled.", reply_markup=ReplyKeyboardMarkup(user_keyboard, resize_keyboard=True))
    context.user_data.clear()
    return ConversationHandler.END

# --- Universal Button Handler ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    try:
        action, mode, user_id_str = query.data.split("_", 2)
        user_id = int(user_id_str)
    except ValueError: 
        logger.error(f"Error splitting callback_data: {query.data}")
        return

    user_data = context.bot_data.get('pending_submissions', {}).pop(user_id_str, None)
    if not user_data: 
        await query.edit_message_text("--- ⚠️ Action already taken ---")
        return

    # --- NEW: Function to log user data to the specified channel ---
    async def log_user_to_channel(approved_user_data):
        try:
            user_sequence = context.bot_data.get('user_sequence_number', 0) + 1
            context.bot_data['user_sequence_number'] = user_sequence
            
            user_log_message = (
                f"*{user_sequence}. Full Name:* `{approved_user_data['full_name']}`\n"
                f"*Sex:* `{approved_user_data['sex']}`\n\n"
                f"*TG Profile:*\n"
                f"  *Name:* `{approved_user_data['tg_name']}`\n"
                f"  *Username:* {approved_user_data['username']}"
            )
            await context.bot.send_message(
                chat_id=USER_DATA_CHANNEL_ID,
                text=user_log_message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send user data to log channel: {e}")
            await context.bot.send_message(ADMIN_ID, f"⚠️ ERROR: Could not send approved user data for {approved_user_data['full_name']} to the log channel. Check bot permissions.")
    # --- END of new function ---

    if action == "approve":
        context.bot_data.setdefault('approved_users', []).append(user_data)
        await log_user_to_channel(user_data) # Log the user data
        
        if mode == "manual":
            try:
                invite_link = await context.bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
                join_button = [[InlineKeyboardButton("➡️ Join Channel Now", url=invite_link.invite_link)]]
                await context.bot.send_message(user_id, "✅ *Payment Approved!* Click the button below to join.", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(join_button))
            except Exception: 
                await context.bot.send_message(ADMIN_ID, "⚠️ ERROR: Link creation failed. Is the bot an admin in the channel?")
        elif mode == "auto":
            await context.bot.send_message(user_id, "✅ *Request Confirmed!* The admin has approved your join request.")
            
    elif action == "reject":
        context.bot_data.setdefault('rejected_users', []).append(user_data)
        if mode == "manual":
            await context.bot.send_message(user_id, "❌ Your payment could not be verified.")
        elif mode == "auto":
            await context.bot.send_message(user_id, "❌ Your join request was denied by the admin.")

    await query.delete_message()


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('Start Payment$'), start_payment)],
        states={
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_SEX: [CallbackQueryHandler(get_sex)],
            GET_PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
        },
        fallbacks=[MessageHandler(filters.Regex('^❌ Cancel$'), cancel_payment)],
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex('Help$'), show_help))
    application.add_handler(MessageHandler(filters.Regex('Contact$'), show_contact))
    
    # Admin handlers
    application.add_handler(MessageHandler(filters.Regex(r'^(⚙️ Switch to Auto-Approve|⚙️ Switch to Manual Approve)$'), toggle_mode))
    application.add_handler(MessageHandler(filters.Regex('^✅ Approved Users$'), show_approved_users))
    application.add_handler(MessageHandler(filters.Regex('^❌ Rejected Users$'), show_rejected_users))
    
    # Conversation handler
    application.add_handler(conv_handler)
    
    # Callback handler for approval/rejection buttons
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()