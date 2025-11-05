from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config.config import BOT_TOKEN
from .handlers import router
from .middleware import GeneratorMiddleware

async def main(generator):
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Добавляем middleware для передачи генератора
    dp.message.middleware(GeneratorMiddleware(generator))
    dp.callback_query.middleware(GeneratorMiddleware(generator))
    
    dp.include_router(router)
    await dp.start_polling(bot, handle_signals=False)
