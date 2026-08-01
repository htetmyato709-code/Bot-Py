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
SUPABASE_URL = "https://jewxoyffdjobpfwpvvon.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impld3hveWZmZGpvYnBmd3B2dm9uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODUzNjY4MDQsImV4cCI6MjEwMDk0MjgwNH0.6r0FfKUYHFVUW5utBl0x2Drvxo7VjtionjvIVzJISEQ"

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Global flag to manage broadcasting state
is_posting = False


async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot ကို Group ထဲ ထည့်လိုက်ရင် သို့မဟုတ် ထုတ်လိုက်ရင် Supabase မှာ Database အလိုအလျောက် Update လုပ်ပေးမည်။"""
    result = update.my_chat_member
    if not result:
        return

    chat_id = result.chat.id
    chat_title = result.chat.title
    new_status = result.new_chat_member.status

    # Bot ကို Group ထဲ Admin သို့မဟုတ် Member အဖြစ် ထည့်လိုက်လျှင် Database တွင် သိမ်းမည်
    if new_status in ["administrator", "member"]:
        try:
            supabase.table("groups").upsert(
                {"group_id": chat_id, "title": chat_title}
            ).execute()
            logger.info(f"Added/Updated Group: {chat_title} ({chat_id})")
        except Exception as e:
            logger.error(f"Error adding group to Supabase: {e}")

    # Bot ကို Group ထဲမှ ထုတ်လိုက်လျှင် Database မှ ပြန်ဖျက်မည်
    elif new_status in ["left", "kicked"]:
        try:
            supabase.table("groups").delete().eq("group_id", chat_id).execute()
            logger.info(f"Removed Group: {chat_title} ({chat_id})")
        except Exception as e:
            logger.error(f"Error removing group from Supabase: {e}")


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/post မိန့်ခွန်းဖြင့် Admin က စာ/ပုံ/Video စသည်တို့ကို Group များသို့ Auto Share ပေးမည်။"""
    global is_posting

    # Admin ဟုတ်မဟုတ် စစ်ဆေးခြင်း
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ သင်သည် Admin မဟုတ်ပါသဖြင့် ဤ Command ကို သုံးခွင့်မရှိပါ။")
        return

    # Reply လုပ်ထားသော Message မရှိလျှင် အကြောင်းကြားမည်
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

    # Supabase မှ Group List များ ဆွဲယူခြင်း
    try:
        response = supabase.table("groups").select("group_id, title").execute()
        groups = response.data
    except Exception as e:
        await update.message.reply_text(f"❌ Supabase မှ Group Data ယူရာတွင် အမှားအယွင်းရှိပါသည်: {e}")
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
            # Group သို့ Post ကို Copy ကူး၍ ပို့ပေးမည် (Forwarded tag မပါပါ)
            await target_message.copy(chat_id=group_id)
            success_count += 1
            logger.info(f"Successfully sent to {group_title} ({group_id})")

            # 🛑 Telegram Rate Limit အကန့်အသတ်ကျော်ပြီး Block မထိစေရန် ၁ ပို့နှင့် ၁ ပို့ကြား ၂ စက္ကန့် နားပေးမည်
            await asyncio.sleep(2)

        except Exception as e:
            fail_count += 1
            logger.error(f"Failed to send to {group_title} ({group_id}): {e}")

    is_posting = False
    await update.message.reply_text(
        f"✅ **Post Share ခြင်း ပြီးစီးပါပြီ!**\n\n"
        f"🟢 အောင်မြင်သော Group: {success_count}\n"
        f"🔴 မအောင်မြင်သော Group: {fail_count}"
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stop မိန့်ခွန်းဖြင့် Post Share နေခြင်းကို ချက်ချင်းရပ်မည်။"""
    global is_posting

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ သင်သည် Admin မဟုတ်ပါ။")
        return

    if not is_posting:
        await update.message.reply_text("ℹ️ လက်ရှိတွင် မည်သည့် Post မျှ Share မနေပါ။")
        return

    is_posting = False
    await update.message.reply_text("⏳ Post Share ခြင်းကို ရပ်တန့်ရန် လုပ်ဆောင်နေပါသည်။...")


def main():
    """Bot ကို စတင် Run မည့် Main Function"""
    app = Application.builder().token(BOT_TOKEN).build()

    # Track Bot joining/leaving groups
    app.add_handler(ChatMemberHandler(track_groups, ChatMemberHandler.MY_CHAT_MEMBER))

    # Commands Handlers
    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("stop", stop_command))

    print("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
