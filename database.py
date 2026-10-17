import aiosqlite

DB_NAME = "database.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                full_name TEXT,
                username TEXT,
                phone TEXT,
                payment_method TEXT,
                transaction_id TEXT,
                status TEXT DEFAULT 'PENDING'
            )
        """)
        await db.commit()

async def add_student(telegram_id, full_name, username, phone, payment_method, transaction_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR REPLACE INTO students (telegram_id, full_name, username, phone, payment_method, transaction_id, status)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
        """, (telegram_id, full_name, username, phone, payment_method, transaction_id))
        await db.commit()

async def update_status(telegram_id, status):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE students SET status = ? WHERE telegram_id = ?", (status, telegram_id))
        await db.commit()

async def get_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM students") as cursor:
            total = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM students WHERE status='CONFIRMED'") as cursor:
            confirmed = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM students WHERE status='PENDING'") as cursor:
            pending = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM students WHERE status='REJECTED'") as cursor:
            rejected = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM students WHERE payment_method='Telebirr'") as cursor:
            telebirr = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM students WHERE payment_method='M-Pesa'") as cursor:
            mpesa = (await cursor.fetchone())[0]
        return total, confirmed, pending, rejected, telebirr, mpesa
