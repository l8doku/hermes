import logging
from bot.config import load_config
import bot.lookup
import bot.kanize
from typing import Optional

from telegram import Chat, ChatMember, ChatMemberUpdated, Update, MessageEntity
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import re


# Load configuration
config = load_config()


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)


def welcome_new_member(update: Update, context):
    """Welcome new users and send rules"""
    for new_member in update.message.new_chat_members:
        # Skip if the new member is the bot itself
        if new_member.id == context.bot.id:
            continue

        welcome_msg = f"ようこそ {new_member.mention_markdown_v2()}さん！\n"

        update.message.reply_text(welcome_msg, parse_mode="MarkdownV2")


def extract_status_change(
    chat_member_update: ChatMemberUpdated,
) -> Optional[tuple[bool, bool]]:
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get(
        "is_member", (None, None)
    )

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

    return was_member, is_member


async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tracks the chats the bot is in."""
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result

    # Let's check who is responsible for the change
    cause_name = update.effective_user.full_name

    # Handle chat types differently:
    chat = update.effective_chat
    if chat.type == Chat.PRIVATE:
        if not was_member and is_member:
            # This may not be really needed in practice because most clients will automatically
            # send a /start command after the user unblocks the bot, and start_private_chat()
            # will add the user to "user_ids".
            # We're including this here for the sake of the example.
            logger.info("%s unblocked the bot", cause_name)
            context.bot_data.setdefault("user_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info("%s blocked the bot", cause_name)
            context.bot_data.setdefault("user_ids", set()).discard(chat.id)
    elif chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if not was_member and is_member:
            logger.info("%s added the bot to the group %s", cause_name, chat.title)
            context.bot_data.setdefault("group_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info("%s removed the bot from the group %s", cause_name, chat.title)
            context.bot_data.setdefault("group_ids", set()).discard(chat.id)
    elif not was_member and is_member:
        logger.info("%s added the bot to the channel %s", cause_name, chat.title)
        context.bot_data.setdefault("channel_ids", set()).add(chat.id)
    elif was_member and not is_member:
        logger.info("%s removed the bot from the channel %s", cause_name, chat.title)
        context.bot_data.setdefault("channel_ids", set()).discard(chat.id)


# async def jp_ru_dict_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Looks up a word in a jp-ru dictionary"""
#     word = update.message.text.replace("/jisho", "").strip()
#     logger.info(f"Looking up the word {word}")
#     text = bot.lookup.lookup(word)
#     logger.info(f"Got result {text}")
#     if text:
#         await update.effective_message.reply_text(text)
#     else:
#         await update.effective_message.reply_text(f"Ничего не нашёл по запросу {word}")


def extract_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    # Private chat: accept any message
    if update.message.chat.type == "private":
        text = update.message.text
        return re.sub(r"^/jisho\s*", "", text).strip()

    # Group chat: only process commands/mentions
    if not (
        update.message.entities
        and any(
            e.type == MessageEntity.BOT_COMMAND or e.type == MessageEntity.MENTION
            for e in update.message.entities
        )
    ):
        return None

    # Handle replies in group chats
    if update.message.reply_to_message:
        logger.info(f"I see a reply")
        # Check for text quotes (new Telegram feature)
        if update.message.quote:
            return update.message.quote.text.strip()
        return update.message.reply_to_message.text.strip()

    # Handle direct mentions/commands in group
    text = update.message.text
    text = re.sub(r"^/jisho\s*", "", text)  # Remove command
    text = re.sub(
        r"@" + context.bot.username + r"\s*", "", text, flags=re.IGNORECASE
    )  # Remove mention
    return text.strip()


def extract_quoted_query(query: str) -> tuple[str, bool]:
    """
    Returns:
        - (extracted_query, was_quoted)  
        If quoted, returns (text_inside_quotes, True).  
        If not quoted, returns (original_text, False).  
    """
    stripped = query.strip()
    if len(stripped) >= 2 and stripped[0] == '"' and stripped[-1] == '"':
        # Remove quotes and return inner text
        return stripped[1:-1], True
    return query, False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = extract_query(update, context)
    if not user_query:
        return

    logger.info(f"Found query - {user_query}")
    logger.info(f"Checking for quotes")
    clean_query, is_quoted = extract_quoted_query(user_query)

    if not is_quoted:
        logger.info("Not quoted, checking romaji")

        kana = bot.kanize.toKana(clean_query)
        if kana is not None:
            logger.info(f"Found romaji, looking up {kana}")
            lookup_query = kana
        else:
            logger.info(f"Couldn't parse romaji, looking up {clean_query}")
            lookup_query = clean_query
    else:
        logger.info("Quoted input, skippng romaji check")
        lookup_query = clean_query

    result = bot.lookup.lookup(lookup_query)
    logger.info(f"Got result {result}")
    await update.message.reply_text(result)


async def greet_chat_members(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Greets new users in chats and announces when someone leaves"""
    result = extract_status_change(update.chat_member)
    if result is None:
        return

    was_member, is_member = result
    member_name = update.chat_member.new_chat_member.user.mention_html()

    if not was_member and is_member:
        await update.effective_chat.send_message(
            f"ようこそ {member_name}さん！",
            parse_mode=ParseMode.HTML,
        )


async def start_private_chat(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Greets the user and records that they started a chat with the bot if it's a private chat.
    Since no `my_chat_member` update is issued when a user starts a private chat with the bot
    for the first time, we have to track it explicitly here.
    """
    user_name = update.effective_user.full_name
    chat = update.effective_chat
    if chat.type != Chat.PRIVATE or chat.id in context.bot_data.get("user_ids", set()):
        return

    logger.info("%s started a private chat with the bot", user_name)
    context.bot_data.setdefault("user_ids", set()).add(chat.id)

    await update.effective_message.reply_text(f"Welcome {user_name}.")


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(config["token"]).build()

    # Keep track of which chats the bot is in
    application.add_handler(
        ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER)
    )

    application.add_handler(CommandHandler("jisho", handle_message))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Handle members joining/leaving chats.
    application.add_handler(
        ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER)
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
