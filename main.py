import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand  # 👈 Не забудь импорт
from config import BOT_TOKEN
from database import create_tables
from handlers import router

logging.basicConfig(level=logging.INFO)


# Функция настройки меню
async def setup_bot_commands(bot: Bot):
    bot_commands = [
        BotCommand(command="/start", description="🚀 Начать"),
        BotCommand(command="/profile", description="👤 Мой профиль"),
        BotCommand(command="/help", description="ℹ️ Помощь"),
    ]
    await bot.set_my_commands(bot_commands)


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    await create_tables()

    # 👇 Настраиваем меню ОДИН РАЗ при запуске
    await setup_bot_commands(bot)

    print("🚀 Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")