from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# Клавиатура подтверждения регистрации
confirm_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        ]
    ]
)

# Основная клавиатура для студентов
student_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Отметиться")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Админская клавиатура
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Отметиться")],
        [KeyboardButton(text="📁 Экспорт"), KeyboardButton(text="📊 Статистика"),KeyboardButton(text="👥 Пользователи")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)