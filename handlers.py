from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from keyboards import main_kb, cancel_kb, role_kb  # 👈 Импортируем обе клавиатуры
from states import OrderForm
from database import add_user, get_user, add_order, get_open_orders, assign_order, top_up_balance, get_user_transactions, get_my_orders, complete_order, update_user_role

router = Router()

# 1. Хендлер на /start
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    await add_user(user.id, user.username)

    await message.answer(
        f"Привет, {user.first_name}! 👋\nДобро пожаловать на биржу фриланса.",
        reply_markup=main_kb
    )


# 2. Хендлер на кнопку "👤 Мой профиль" (ОБНОВЛЕННЫЙ)
@router.message(Command("profile"))
@router.message(F.text == "👤 Мой профиль")
async def profile_handler(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user(user_id)
    # Получаем последние транзакции
    history = await get_user_transactions(user_id)

    if user_data:
        balance = user_data[2]
        role = user_data[3]

        # Формируем красивый список операций
        history_text = "\n".join([f"▫️ {op} : {amt}₽" for amt, op, date in history]) if history else "История пуста"

        text = (
            f"👤 <b>Твой профиль:</b>\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"💰 Баланс: <b>{balance} ₽</b>\n"
            f"🎭 Роль: {role}\n\n"
            f"📜 <b>История операций:</b>\n"
            f"{history_text}"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=role_kb)
    else:
        await message.answer("Ошибка! Такого пользователя нет в базе.")

# 3. Хендлер на "О сервисе"
@router.message(F.text == "ℹ️ О сервисе")
async def about_handler(message: types.Message):
    await message.answer("Это учебный бот-биржа. Здесь можно публиковать и выполнять заказы.")


# 4. Хендлер для Помощи
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("ℹ️ Это бот-биржа. Нажми /start, чтобы перезапустить меню.")


# --- ЛОГИКА ОТМЕНЫ (Новое!) ---
# Этот хендлер сработает, если нажать "❌ Отмена" в любой момент
@router.message(F.text == "❌ Отмена")
@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state is None:
        await message.answer("Нечего отменять.", reply_markup=main_kb)
        return

    await state.clear()
    await message.answer("🚫 Создание заказа отменено.", reply_markup=main_kb)


# --- СОЗДАНИЕ ЗАКАЗА ---

# 1. Начало диалога
@router.message(F.text == "📝 Создать заказ")
async def start_order_creation(message: types.Message, state: FSMContext):
    # 👇 Добавляем кнопку Отмена
    await message.answer("Введите краткое название заказа (например: 'Сделать логотип'):", reply_markup=cancel_kb)
    await state.set_state(OrderForm.waiting_for_title)


# 2. Ловим Название
@router.message(OrderForm.waiting_for_title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    # 👇 Добавляем кнопку Отмена
    await message.answer("Отлично! Теперь напишите подробное ТЗ (описание):", reply_markup=cancel_kb)
    await state.set_state(OrderForm.waiting_for_description)


# 3. Ловим Описание
@router.message(OrderForm.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    # 👇 Добавляем кнопку Отмена
    await message.answer("Укажите бюджет (только число, например: 5000):", reply_markup=cancel_kb)
    await state.set_state(OrderForm.waiting_for_price)


# 4. Ловим Цену и сохраняем
@router.message(OrderForm.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
    except ValueError:
        await message.answer("❌ Это не число! Введите цену цифрами (например: 1000).", reply_markup=cancel_kb)
        return

    data = await state.get_data()
    user_id = message.from_user.id

    # 👇 ВЫЗЫВАЕМ НОВУЮ УМНУЮ ФУНКЦИЮ
    success = await add_order(
        customer_id=user_id,
        title=data['title'],
        description=data['description'],
        price=price
    )

    if success:
        # Если денег хватило
        await message.answer(
            f"✅ Заказ <b>«{data['title']}»</b> опубликован!\n"
            f"❄️ Сумма <b>{price} ₽</b> заморожена на вашем счете.",
            reply_markup=main_kb,
            parse_mode="HTML"
        )
    else:
        # Если денег НЕ хватило
        await message.answer(
            f"❌ <b>Недостаточно средств!</b>\n"
            f"Для создания этого заказа нужно {price} ₽.\n"
            f"Пополните баланс через команду /money",
            reply_markup=main_kb,
            parse_mode="HTML"
        )

    await state.clear()


# --- ПРОСМОТР И ВЗЯТИЕ ЗАКАЗОВ ---

@router.message(F.text == "🔍 Найти заказ")
async def show_orders_handler(message: types.Message):
    orders = await get_open_orders()

    if not orders:
        await message.answer("😔 Пока нет доступных заказов.\nЗагляни позже!")
        return

    await message.answer(f"🔎 Найдено активных заказов: {len(orders)}")

    for order in orders:
        order_id = order[0]
        title = order[2]
        desc = order[3]
        price = order[4]

        card_text = (
            f"📦 <b>Заказ #{order_id}</b>\n"
            f"🛠 <b>{title}</b>\n"
            f"💰 Бюджет: <b>{price} ₽</b>\n\n"
            f"📝 <i>{desc}</i>"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Взять в работу", callback_data=f"take_order_{order_id}")]
        ])

        await message.answer(card_text, reply_markup=keyboard, parse_mode="HTML")


# Ловим нажатие на кнопку "Взять заказ"
@router.callback_query(F.data.startswith("take_order_"))
async def process_take_order(callback: CallbackQuery, bot: Bot):
    try:
        order_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка номера заказа!")
        return

    user_id = callback.from_user.id

    success = await assign_order(order_id, user_id)

    if success:
        await callback.answer("✅ Вы взяли заказ! Свяжитесь с заказчиком.", show_alert=True)
        try:
            await bot.edit_message_reply_markup(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=None
            )
        except Exception:
            pass
        await bot.send_message(user_id, f"Вы назначены исполнителем заказа #{order_id}. Удачи!")

    else:
        await callback.answer("❌ Заказ уже занят или удален!", show_alert=True)
        try:
            await bot.edit_message_reply_markup(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=None
            )
        except Exception:
            pass


@router.message(F.text == "📂 Мои заказы")
async def my_orders_handler(message: types.Message):
    user_id = message.from_user.id
    orders = await get_my_orders(user_id)

    if not orders:
        await message.answer("У вас пока нет заказов.")
        return

    await message.answer(f"Ваши заказы ({len(orders)} шт.):")

    for order in orders:
        order_id = order[0]
        title = order[2]
        price = order[4]
        status = order[5]
        executor = order[6]

        status_text = "🟢 Открыт" if status == 'open' else ("🟡 В работе" if status == 'in_progress' else "🔴 Закрыт")

        card_text = (
            f"📦 <b>Заказ #{order_id}</b>\n"
            f"🛠 {title}\n"
            f"💰 {price} ₽\n"
            f"Статус: {status_text}"
        )

        # Если заказ В РАБОТЕ — показываем кнопку "Принять работу"
        keyboard = None
        if status == 'in_progress':
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить выполнение", callback_data=f"confirm_{order_id}")]
            ])

        await message.answer(card_text, reply_markup=keyboard, parse_mode="HTML")


# --- ОБРАБОТКА КНОПКИ "ПОДТВЕРДИТЬ" ---
@router.callback_query(F.data.startswith("confirm_"))
async def process_confirm_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])

    # Вызываем функцию завершения
    result = await complete_order(order_id)

    if result:
        success, executor_id = result
        await callback.answer("✅ Заказ закрыт! Деньги отправлены исполнителю.", show_alert=True)

        # Обновляем сообщение (убираем кнопку)
        await bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=None
        )

        # Уведомляем фрилансера, что деньги пришли!
        await bot.send_message(executor_id, f"🎉 <b>УРА! Заказ #{order_id} принят!</b>\nВам начислена оплата.",
                               parse_mode="HTML")
    else:
        await callback.answer("Ошибка! Не удалось закрыть заказ.", show_alert=True)


# handlers.py

@router.callback_query(F.data.startswith("set_role_"))
async def process_role_change(callback: types.CallbackQuery):
    # Вытаскиваем роль из callback_data (customer или freelancer)
    new_role = callback.data.split("_")[2]

    # Обновляем в базе
    await update_user_role(callback.from_user.id, new_role)

    # Красивый текст для уведомления
    role_name = "Заказчик 💼" if new_role == "customer" else "Фрилансер 🛠"

    await callback.answer(f"Вы сменили роль на: {role_name}", show_alert=True)

    # Обновляем сообщение профиля, чтобы сразу увидеть изменения
    # (Вызываем тот же текст, что и в profile_handler, либо просто пишем "Обновлено")
    await callback.message.edit_text(
        f"✅ Роль успешно изменена на <b>{role_name}</b>.\nОбновите профиль, чтобы увидеть изменения.",
        parse_mode="HTML")


# --- ЧИТ-КОД НА ДЕНЬГИ (Для тестов) ---
@router.message(Command("money"))
async def cmd_money(message: types.Message):
    # Разбираем команду: /money 5000
    try:
        amount = float(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("⚠️ Пиши так: /money 5000")
        return

    user_id = message.from_user.id

    # Вызываем нашу ACID-функцию
    await top_up_balance(user_id, amount)

    await message.answer(f"💳 Баланс пополнен на {amount} ₽!")