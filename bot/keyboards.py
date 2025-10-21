from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup,KeyboardButton

confirm_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        ]
    ]
)

CheckIn_keyboard= ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отметиться")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )