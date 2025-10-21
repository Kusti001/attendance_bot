from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

class GeneratorMiddleware(BaseMiddleware):
    def __init__(self, generator):
        self.generator = generator

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        data["generator"] = self.generator
        return await handler(event, data)
