import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from supabase import create_client, Client

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8773562389:AAFvGbiAiovbkujz60lvlT6oJ9ngrnNEqtI"
ADMIN_ID = 8305397892
SUPABASE_URL = "https://jhcnqwzezvjldhigxpze.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpoY25xd3plenZqbGRoaWd4cHzeIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ5NDQ0ODUsImV4cCI6MjEwMDUyMDQ4NX0.pwq1ps7MfvQIiZGuvs9TLimYRSq_9O5ebaMrKqd6oZk"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
is_posting = False


async def auto_save_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Group ထဲတွင် စာရိုက်ပါက Auto သိမ်းမည်"""
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        try:
            supabase.table("groups").upsert(
                {"group_id": chat.id, "title": chat.title}
            ).execute()
            logger.info(f"Saved Group: {chat.title} ({chat.id})")
        except Exception as e:
            logger.error(f"Error saving group: {e}")


async def add_group_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin က Group ID ကို ကိုယ်တိုင် ထည့်သွင်းနိုင်သည့် Command"""
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("⚠️ ကျေးဇူးပြု၍ `/addgp -100xxxxxxx` ပုံစံဖြင့် Group ID ကို ထည့်ပေးပါ။ (Note: Telegram Group ID များသည် -100 ဖြင့် စလေ့ရှိပါသည်။)")
        return

    try:
        group_id = int(context.args[0])
        supabase.table("groups").upsert(
            {"group_id": group_id, "title": "Manual Added Group"}
        ).execute()
        await update.message.reply_text(f"✅ Group ID `{group_id}` ကို Database ထဲ သို့ အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_posting

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ သင်သည် Admin မဟုတ်ပါ။")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Share ချင်သော Post ကို Reply ပြန်၍ /post ဟု ပို့ပေးပါ။")
        return

    if is_posting:
        await update.message.reply_text("⚠️ Post Share နေဆဲ ဖြစ်ပါသည်။ ခဏစောင့်ပါ။")
        return

    is_posting = True
    target_message = update.message.reply_to_message

    try:
        response = supabase.table("groups").select("group_id, title").execute()
        groups = response.data
    except Exception as e:
        await update.message.reply_text(f"❌ Database Error: {e}")
        is_posting = False
        return

    if not groups:
        await update.message.reply_text("❌ Database ထဲတွင် Group မရှိသေးပါ။ Group ထဲတွင် စာတစ်ခွန်းသွားရိုက်ပါ သို့မဟုတ် `/addgp [ID]` ဖြင့် ထည့်ပါ။")
        is_posting = False
        return

    await update.message.reply_text(f"🚀 Group ပေါင်း {len(groups)} ခုသို့ စတင် Share နေပါပြီ...")

    success_count = 0
    fail_count = 0

    for group in groups:
        if not is_posting:
            await update.message.reply_text("🛑 Post Share ခြင်းကို ရပ်လိုက်ပါပြီ။")
            break

        group_id = group["group_id"]
        try:
            await target_message.copy(chat_id=group_id)
            success_count += 1
            await asyncio.sleep(2)
        except Exception as e:
            fail_count += 1
            logger.error(f"Failed to send to {group_id}: {e}")

    is_posting = False
    await update.message.reply_text(
        f"✅ **Post Share ပြီးစီးပါပြီ!**\n\n🟢 အောင်မြင်: {success_count}\n🔴 မအောင်မြင်: {fail_count}"
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_posting
    if update.effective_user.id == ADMIN_ID:
        is_posting = False
        await update.message.reply_text("⏳ Post Share ခြင်းကို ရပ်လိုက်ပါပြီ။")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("addgp", add_group_manual))

    # Listen to group messages
    app.add_handler(
        MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, auto_save_group)
    )

    print("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
