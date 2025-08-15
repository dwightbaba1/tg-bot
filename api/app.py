import os, logging
from fastapi import FastAPI, Request, Header, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Senin dosyaların:
from database import DatabaseManager
from bot_handlers import BotHandlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "")

# --- PTB app + handler'lar ---
db_manager = DatabaseManager()
db_manager.init_database()

bot_handlers = BotHandlers(db_manager)

application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", bot_handlers.start_command))
application.add_handler(CommandHandler("help", bot_handlers.help_command))
application.add_handler(CommandHandler("register", bot_handlers.register_command))
application.add_handler(CommandHandler("solved", bot_handlers.solved_command))
application.add_handler(CommandHandler("lb", bot_handlers.daily_leaderboard_command))
application.add_handler(CommandHandler("top", bot_handlers.lifetime_leaderboard_command))
application.add_handler(CommandHandler("stats", bot_handlers.stats_command))
application.add_handler(CommandHandler("reset_daily", bot_handlers.reset_daily_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                                       bot_handlers.handle_message))

app = FastAPI()

@app.on_event("startup")
async def _startup():
    await application.initialize()
    await application.start()
    logger.info("Bot ready (webhook mode)")

@app.on_event("shutdown")
async def _shutdown():
    await application.stop()
    await application.shutdown()

@app.get("/")
async def health():
    return {"ok": True}

@app.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None)
):
    if SECRET_TOKEN and x_telegram_bot_api_secret_token != SECRET_TOKEN:
        return Response(status_code=403)

    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}
