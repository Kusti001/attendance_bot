import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, select

from config.config import DB_URL, MOSCOW_TZ
# Создаём асинхронный движок для SQLite
engine = create_async_engine("sqlite+aiosqlite:///bot.db", echo=False)

Base = declarative_base()

# Асинхронная сессия
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Модель User
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    full_name = Column(String, unique=True)
    group = Column(String)

    # Связь "один ко многим" — один пользователь может иметь много посещений
    attendances = relationship("Attendance", back_populates="user")

    def __repr__(self):
        return f"<{self.full_name} - {self.group}>"

# Модель Attendance
class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=lambda: datetime.now(MOSCOW_TZ))
    user_id = Column(Integer, ForeignKey("users.id"))  # Ключ связи с таблицей users

    # Обратная связь "многие к одному"
    user = relationship("User", back_populates="attendances")

    def __repr__(self):
        return f"<Attendance {self.user.full_name} at {self.date}>"

# Асинхронный менеджер для работы с пользователями
class UserManager:
    async def post(self, telegram_id: int, full_name: str, group: str):
        async with async_session() as session:
            async with session.begin():
                user = User(telegram_id=telegram_id, full_name=full_name, group=group)
                session.add(user)
                try:
                    await session.commit()
                    print(f"[OK] {user} - зарегистрирован(а)")
                except Exception as e:
                    await session.rollback()
                    print("[ERR]", e)

    async def get(self, telegram_id: int):
        async with async_session() as session:
            result = await session.execute(
                select(User).filter_by(telegram_id=telegram_id)
            )
            return result.scalars().first()

    async def check_tg_id(self, telegram_id: int):
        async with async_session() as session:
            result = await session.execute(
                select(User).filter_by(telegram_id=telegram_id)
            )
            return not(result.scalars().first() is None)

    async def check_full_name(self, full_name: str):
        async with async_session() as session:
            result = await session.execute(
                select(User).filter_by(full_name=full_name)
            )
            return not(result.scalars().first() is None)

    async def delete(self, telegram_id: int):
        async with async_session() as session:
            async with session.begin():
                user = await self.get(telegram_id)
                if not user:
                    print("[ERR] Пользователя с таким tg_id не существует")
                    return
                try:
                    await session.delete(user)
                    await session.commit()
                    print(f"[OK] Пользователь {user} удален")
                except Exception as e:
                    await session.rollback()
                    print("[ERR]", e)

class AttendanceManager:
    async def post(self, telegram_id: int):
        async with async_session() as session:
            async with session.begin():
                try:
                    user_manager = UserManager()
                    user = await user_manager.get(telegram_id=telegram_id)
                    if not user:
                        print("[ERR] Пользователь не найден")
                        return False
                    
                    # Проверяем, не отмечался ли уже сегодня
                    today = datetime.now(MOSCOW_TZ).date()
                    
                    existing_attendance = await session.execute(
                        select(Attendance).filter(
                            Attendance.user_id == user.id,
                            Attendance.date >= today
                        )
                    )
                    
                    if existing_attendance.scalars().first():
                        print(f"[WARN] Пользователь {user.full_name} уже отмечался сегодня")
                        return False
                    
                    # Создаем новую запись о посещении
                    attendance = Attendance(user_id=user.id)  # ИСПРАВЛЕНО: user_id вместо user
                    session.add(attendance)
                    await session.commit()
                    print(f"[OK] {user.full_name} - Отмечен(а)")
                    return True
                    
                except Exception as e:
                    await session.rollback()
                    print("[ERR]", e)
                    return False

    async def is_marked_today(self, telegram_id: int):
        async with async_session() as session:
            today = datetime.now(MOSCOW_TZ).date()
            user_manager = UserManager()
            user = await user_manager.get(telegram_id=telegram_id)
            if not user:
                print("[ERR] Пользователь не найден")
                return False
            result = await session.execute(
                select(Attendance).filter(
                    Attendance.user_id == user.id,
                    Attendance.date >= today
                )
            )
            return not(result.scalars().first() is None)
# Функция для создания таблиц
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Запуск создания таблиц
if __name__ == "__main__":
    asyncio.run(init_db())