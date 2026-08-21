import os
import sqlite3
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DB_FILE = "orthodox.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# =========================
# DATABASE
# =========================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_user(user_id, username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO users (user_id, username)
        VALUES (?, ?)
    """, (user_id, username))

    conn.commit()
    conn.close()


def add_knowledge(question, answer):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO knowledge (question, answer)
        VALUES (?, ?)
    """, (question, answer))

    conn.commit()
    conn.close()


def search_answer(question):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    words = question.lower().split()

    cur.execute("SELECT question, answer FROM knowledge")
    rows = cur.fetchall()

    conn.close()

    best_answer = None
    best_score = 0

    for saved_question, answer in rows:
        saved_words = saved_question.lower().split()

        score = 0

        for word in words:
            if len(word) >= 2 and word in saved_words:
                score += 1

        if score > best_score:
            best_score = score
            best_answer = answer

    return best_answer


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    save_user(
        user.id,
        user.username or ""
    )

    text = (
        "✝️ እንኳን ወደ Orthodox Christian Bot በደህና መጡ!\n\n"
        "📖 ስለ ክርስትና፣ መጽሐፍ ቅዱስ፣ "
        "ቅዱሳን እና የኦርቶዶክስ ትምህርት ጥያቄ መጠየቅ ትችላላችሁ።\n\n"
        "❓ ጥያቄህን በቀጥታ ጻፍ።"
    )

    await update.message.reply_text(text)


# =========================
# HELP
# =========================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 የBot አጠቃቀም\n\n"
        "/start - መጀመሪያ\n"
        "/help - እገዛ\n\n"
        "❓ ማንኛውንም የክርስትና ጥያቄ በቀጥታ ጻፍ።"
    )

    await update.message.reply_text(text)


# =========================
# ADMIN ADD KNOWLEDGE
# =========================

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ይህን command Admin ብቻ መጠቀም ይችላል።")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ አጠቃቀም:\n\n"
            "/add ጥያቄ | መልስ\n\n"
            "ለምሳሌ:\n"
            "/add ኦርቶዶክስ ምንድነው? | "
            "የኢትዮጵያ ኦርቶዶክስ ተዋሕዶ ቤተክርስቲያን..."
        )
        return

    full_text = " ".join(context.args)

    if "|" not in full_text:
        await update.message.reply_text(
            "❌ ጥያቄና መልሱን በ | ለይ።"
        )
        return

    question, answer = full_text.split("|", 1)

    question = question.strip()
    answer = answer.strip()

    if not question or not answer:
        await update.message.reply_text(
            "❌ ጥያቄና መልስ ሁለቱም መሞላት አለባቸው።"
        )
        return

    add_knowledge(question, answer)

    await update.message.reply_text(
        "✅ መረጃው በDatabase ተጨምሯል።"
    )


# =========================
# USER QUESTIONS
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message or not update.message.text:
        return

    user = update.effective_user

    save_user(
        user.id,
        user.username or ""
    )

    question = update.message.text.strip()

    answer = search_answer(question)

    if answer:
        await update.message.reply_text(
            "📖 መልስ፦\n\n" + answer
        )

    else:
        await update.message.reply_text(
            "🤔 ይቅርታ፣ ለዚህ ጥያቄ አሁን በDatabase ውስጥ መልስ የለኝም።\n\n"
            "🙏 በኋላ እንደገና ሞክር።"
        )

        # Notify admin
        if ADMIN_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=(
                        "❓ አዲስ ያልተመለሰ ጥያቄ\n\n"
                        f"👤 User: @{user.username or 'NoUsername'}\n"
                        f"🆔 ID: {user.id}\n\n"
                        f"❓ {question}"
                    )
                )
            except Exception:
                pass


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN environment variable is missing!"
        )

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_command))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("✝️ Orthodox Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
