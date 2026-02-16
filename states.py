from aiogram.fsm.state import State, StatesGroup

class OrderForm(StatesGroup):
    waiting_for_title = State()       # Ждем название заказа
    waiting_for_description = State() # Ждем описание
    waiting_for_price = State()       # Ждем цену