import os
import sqlite3

from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
)

# Ensure the "public_photos" folder exists
if not os.path.exists("photos"):
    os.makedirs("photos")

# Define states for the conversation
DESCRIPTION, PHOTO, LOCATION = range(3)


def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Welcome to Deminer Bot! Send description of the landmine."
    )
    return DESCRIPTION


def description(update: Update, context: CallbackContext) -> int:
    context.user_data["description"] = update.message.text
    update.message.reply_text(f"Now, send a photo of the landmine.")
    return PHOTO


def handle_photo(update: Update, context: CallbackContext) -> int:
    context.user_data["photo"] = update.message.photo[-1].file_id
    update.message.reply_text("Now, share your live location.")
    return LOCATION


def handle_location(update: Update, context: CallbackContext) -> int:
    # Create a new connection and cursor
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()

    context.user_data["location"] = update.message.location

    # Save the information to the database
    save_user_info(update.message.chat_id, context.user_data, cursor, conn)

    # Close the connection
    conn.close()

    update.message.reply_text(
        f"Thanks for providing the information:\n"
        f'Description: {context.user_data["description"]}\n'
        f"Photo: [Attached]\n"
        f'Location: Latitude {context.user_data["location"].latitude}, Longitude {context.user_data["location"].longitude}\n\n'
        f"Your information has been saved.\n\n"
        f"Let's start over. Press /start to provide a new description."
    )

    return ConversationHandler.END


def save_user_info(chat_id, user_data, cursor, conn):
    # Check if the table exists, create it if not
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_info (
            chat_id INTEGER PRIMARY KEY,
            description TEXT,
            photo IMAGE,
            location_latitude REAL,
            location_longitude REAL
        )
    """
    )

    cursor.execute(
        """
        INSERT OR REPLACE INTO user_info (chat_id, description, photo, location_latitude, location_longitude)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            chat_id,
            user_data.get("description", None),
            user_data.get("photo", None),
            user_data["location"].latitude
            if "location" in user_data and user_data["location"]
            else None,
            user_data["location"].longitude
            if "location" in user_data and user_data["location"]
            else None,
        ),
    )
    conn.commit()


def restart(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Let's start over. Send /description to provide a new description."
    )
    return DESCRIPTION


def end(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Conversation ended. If you have more landmines to describe, feel free to start a new conversation with /start."
    )
    return ConversationHandler.END


def main() -> None:
    updater = Updater("TELEGRAM_BOT_TOKEN", use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, description)],
            PHOTO: [MessageHandler(Filters.photo, handle_photo)],
            LOCATION: [MessageHandler(Filters.location, handle_location)],
        },
        fallbacks=[CommandHandler("restart", restart), CommandHandler("end", end)],
    )

    dp.add_handler(conv_handler)

    updater.start_polling()

    updater.idle()


if __name__ == "__main__":
    main()
