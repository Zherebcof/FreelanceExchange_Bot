from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# 1. Главное меню (Твоя версия с плейсхолдером)
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔍 Найти заказ"),
            KeyboardButton(text="📝 Создать заказ")
        ],
        [
            KeyboardButton(text="👤 Мой профиль"),
            KeyboardButton(text="ℹ️ О сервисе")
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню..."
)

# 2. Клавиатура выбора роли (Исправленная)
role_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            # Добавили "set_" в начало callback_data
            InlineKeyboardButton(text="Я Заказчик 💼", callback_data="set_role_customer"),
            InlineKeyboardButton(text="Я Фрилансер 🛠", callback_data="set_role_freelancer")
        ]
    ]
)

# 3. Кнопка "Отмена" (Новая, для выхода из диалога)
cancel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Нажмите для отмены..."
)

# keyboards.py (обнови main_kb)
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Найти заказ"), KeyboardButton(text="📝 Создать заказ")],
        [KeyboardButton(text="📂 Мои заказы"), KeyboardButton(text="👤 Мой профиль")], # 👈 Добавили кнопку
        [KeyboardButton(text="ℹ️ О сервисе")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню..."
)