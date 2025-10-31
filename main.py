import asyncio
from threading import Thread
from generator.code_generator import CodeGenerator
from config.config import CODE_INTERVAL
from bot.bot import main as bot_main
from display.display import display_code
from db.models import init_db


async def start_bot(generator):
    await init_db()
    await bot_main(generator)


def start_bot_thread(generator):
    asyncio.run(start_bot(generator))


def main():
    # создаём генератор
    generator = CodeGenerator(CODE_INTERVAL)

    # запускаем бота в отдельном потоке
    Thread(target=start_bot_thread, args=(generator,), daemon=True).start()

    # запускаем Tkinter в главном потоке
    display_code(generator)


if __name__ == "__main__":
    main()