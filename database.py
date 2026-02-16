import aiosqlite

DB_NAME = 'freelance.db'


# 👇 ВАЖНО: Функция называется create_tables (как в твоем main.py)
async def create_tables():
    async with aiosqlite.connect(DB_NAME) as db:
        # 1. Создаем таблицу пользователей
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0,
            role TEXT DEFAULT 'freelancer'
        )''')

        # 2. Создаем таблицу заказов (ВОТ ЭТОГО У ТЕБЯ НЕ БЫЛО)
        await db.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            title TEXT,
            description TEXT,
            price REAL,
            status TEXT DEFAULT 'open',
            executor_id INTEGER DEFAULT NULL
        )''')
        await db.commit()

        # 3. Таблица транзакций (НОВОЕ!)
        # Кто, сколько, тип операции (пополнение, списание, оплата заказа)
        await db.execute('''CREATE TABLE IF NOT EXISTS transactions (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER,
                   amount REAL,
                   operation_type TEXT, 
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY(user_id) REFERENCES users(user_id)
               )''')
        await db.commit()

async def add_user(user_id, username):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()


async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()


async def add_order(customer_id, title, description, price):
    async with aiosqlite.connect(DB_NAME) as db:
        # 1. Сначала проверяем баланс
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (customer_id,)) as cursor:
            row = await cursor.fetchone()
            current_balance = row[0] if row else 0

        # Если денег меньше, чем цена заказа — ОТКАЗ
        if current_balance < price:
            return False

            # 2. Если деньги есть — начинаем ТРАНЗАКЦИЮ (Все или ничего)

        # А) Списываем (замораживаем) деньги
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, customer_id))

        # Б) Создаем сам заказ
        await db.execute(
            "INSERT INTO orders (customer_id, title, description, price) VALUES (?, ?, ?, ?)",
            (customer_id, title, description, price)
        )

        # В) Пишем в историю операций ("hold" - заморозка)
        await db.execute(
            "INSERT INTO transactions (user_id, amount, operation_type) VALUES (?, ?, ?)",
            (customer_id, -price, 'hold_order')
        )

        await db.commit()  # Сохраняем изменения
        return True


async def get_open_orders():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM orders WHERE status = 'open'") as cursor:
            return await cursor.fetchall()


async def assign_order(order_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT status FROM orders WHERE id = ?", (order_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] != 'open':
                return False

        await db.execute(
            "UPDATE orders SET status = 'in_progress', executor_id = ? WHERE id = ?",
            (user_id, order_id)
        )
        await db.commit()
        return True


# --- ФИНАНСОВЫЙ БЛОК (В конец файла) ---

async def top_up_balance(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        # Начинаем транзакцию (ACID)
        # 1. Меняем баланс
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))

        # 2. Пишем в историю
        await db.execute("INSERT INTO transactions (user_id, amount, operation_type) VALUES (?, ?, ?)",
                         (user_id, amount, 'deposit'))

        await db.commit()  # Сохраняем ТОЛЬКО если оба шага прошли успешно
        return True


async def get_user_transactions(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                "SELECT amount, operation_type, created_at FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
                (user_id,)) as cursor:
            return await cursor.fetchall()


# --- ЗАВЕРШЕНИЕ СДЕЛКИ (В конец database.py) ---

# 1. Показать заказы, которые создал ЭТОТ заказчик
async def get_my_orders(customer_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM orders WHERE customer_id = ?", (customer_id,)) as cursor:
            return await cursor.fetchall()


# 2. Самая главная функция: ПРИНЯТЬ РАБОТУ И ВЫПЛАТИТЬ ДЕНЬГИ
async def complete_order(order_id):
    async with aiosqlite.connect(DB_NAME) as db:
        # А) Узнаем цену и кто исполнитель
        async with db.execute("SELECT price, executor_id, status FROM orders WHERE id = ?", (order_id,)) as cursor:
            row = await cursor.fetchone()
            if not row: return False
            price, executor_id, status = row

        # Если заказ уже закрыт или у него нет исполнителя — стоп
        if status != 'in_progress' or not executor_id:
            return False

        # Б) ТРАНЗАКЦИЯ: Начисляем деньги фрилансеру
        # Деньги берутся "из воздуха" (потому что мы их уже списали у заказчика при создании)
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (price, executor_id))

        # В) Меняем статус заказа на 'closed'
        await db.execute("UPDATE orders SET status = 'closed' WHERE id = ?", (order_id,))

        # Г) Пишем в историю фрилансера
        await db.execute(
            "INSERT INTO transactions (user_id, amount, operation_type) VALUES (?, ?, ?)",
            (executor_id, price, 'payment_received')
        )

        await db.commit()
        return True, executor_id  # Возвращаем ID фрилансера, чтобы отправить ему уведомление


async def update_user_role(user_id, new_role):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET role = ? WHERE user_id = ?", (new_role, user_id))
        await db.commit()