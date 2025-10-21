import asyncio
from threading import Thread
from generator.code_generator import CodeGenerator
from config.config import CODE_INTERVAL
from bot.bot import main as bot_main
from display.display import display_code
from db.models import init_db

async def main():
    # создание бд
    await init_db()
    
    # создаём единый объект генератора
    generator = CodeGenerator(CODE_INTERVAL)

    # запускаем Tkinter в отдельном потоке
    Thread(target=display_code, args=(generator,), daemon=True).start()

    # запускаем бота
    await bot_main(generator)

if __name__ == "__main__":
    asyncio.run(main())