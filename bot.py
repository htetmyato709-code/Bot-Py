import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ChatMemberHandler,
    MessageHandler,
    filters,
)
from supabase import create_client, Client

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurations
BOT_TOKEN = "8773562389:AAFvGbiAiovbkujz60lvlT6oJ9ngrnNEqtI"
ADMIN_ID = 8305397892
SUPABASE_URL = "https://jhcnqwzezvjldhigxpze.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpoY25xd3plenZqbGRoaWd4cHplIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ5NDQ0ODUsImV4cCI6MjEwMDUyMDQ4NX0.pwq1ps7MfvQIiZGuvs9TLimYRSq_9O5ebaMrKqd6oZk"

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

is_posting = False


async def auto_save_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Group ထဲမှာ စာတစ်ခွန်းရိုက်လိုက်ရင် သို့မဟုတ် Bot ပါလာရင် Database ထဲ Auto သိမ်းမည်"""
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        try:
            supabase.table("groups").upsert(
                {"group_id": chat.id, "title": chat.title}
            ).execute()
            logger.info(f"Saved Group: {chat.title} ({chat.id})")
        except Exception as e:
            logger.error(f"Error saving group: {e}")


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/post မိန့်ခွန်းဖြင့် Admin က စာ/ပုံ/Video စသည်တို့ကို Group များသို့ Auto Share ပေးမည်။"""
    global is_posting

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ သင်သည် Admin မဟုတ်ပါသဖြင့် ဤ Command ကို သုံးခွင့်မရှိပါ။")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "⚠️ ကျေးဇူးပြု၍ သင် Share ချင်သော စာ/ပုံ/Video ကို /post ဟု Reply ပြန်၍ ပို့ပေးပါ။"
        )
        return

    if is_posting:
        await update.message.reply_text("⚠️ လက်ရှိမှာ Post Share နေဆဲ ဖြစ်ပါတယ်။ ခဏစောင့်ပါ သို့မဟုတ် /stop ဖြင့် ရပ်ပါ။")
        return

    is_posting = True
    target_message = update.message.reply_to_message

    try:
        response = supabase.table("groups").select("group_id, title").execute()
        groups = response.data
    except Exception as e:
        await update.message.reply_text(f"❌ Supabase Error: {e}")
        is_posting = False
        return

    if not groups:
        await update.message.reply_text("❌ Database ထဲတွင် Bot ဝင်ထားသော Group မရှိသေးပါ။")
        is_posting = False
        return

    await update.message.reply_text(f"🚀 Group ပေါင်း {len(groups)} ခုသို့ Post စတင် Share နေပါပြီ...")

    success_count = 0
    fail_count = 0

    for group in groups:
        if not is_posting:
            await update.message.reply_text("🛑 Post Share ခြင်းကို Admin မှ ရပ်တန့်လိုက်ပါသည်။")
            break

        group_id = group["group_id"]
        group_title = group.get("title", "Unknown")

        try:
            await target_message.copy(chat_id=group_id)
            success_count += 1
            await asyncio.sleep(2)  # 2 Seconds delay between posts
        except Exception as e:
            fail_count += 1
            logger.error(f"Failed to send to {group_title}: {e}")

    is_posting = False
    await update.message.reply_text(
        f"✅ **Post Share ခြင်း ပြီးစီးပါပြီ!**\n\n"
        f"🟢 အောင်မြင်သော Group: {success_count}\n"
        f"🔴 မအောင်မြင်သော Group: {fail_count}"
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_posting
    if update.effective_user.id != ADMIN_ID:
        return
    is_posting = False
    await update.message.reply_text("⏳ Post Share ခြင်းကို ရပ်တန့်လိုက်ပါသည်။")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("stop", stop_command))

    # Group ထဲမှာ မည်သည့် စာမဆို ပို့လိုက်တာနဲ့ Group ID ကို Auto သိမ်းမယ့် Handler
    app.add_handler(
        MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, auto_save_group)
    )

    print("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()                          
