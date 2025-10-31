import pandas as pd
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import User, Attendance
from config.config import ADMIN_IDS, MOSCOW_TZ
from dotenv import load_dotenv, set_key
import openpyxl

# Загружаем .env файл
load_dotenv()

def is_admin(telegram_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return telegram_id in ADMIN_IDS


def get_admin_ids() -> list:
    """Получает список ID администраторов"""
    return ADMIN_IDS.copy()


def add_admin(telegram_id: int) -> bool:
    """
    Добавляет администратора
    
    Args:
        telegram_id: ID пользователя Telegram
        
    Returns:
        bool: True если успешно добавлен, False если уже существует
    """
    try:
        if telegram_id in ADMIN_IDS:
            return False
        
        # Обновляем .env файл
        current_admins = ",".join(map(str, ADMIN_IDS + [telegram_id]))
        set_key(".env", "ADMIN_IDS", current_admins)
        
        ADMIN_IDS.append(telegram_id)
        
        return True
    except Exception as e:
        print(f"[ERR] Ошибка при добавлении администратора: {e}")
        return False


def remove_admin(telegram_id: int) -> bool:
    """
    Удаляет администратора
    
    Args:
        telegram_id: ID пользователя Telegram
        
    Returns:
        bool: True если успешно удален, False если не найден
    """
    try:
        if telegram_id not in ADMIN_IDS:
            return False
        
        # Обновляем .env файл
        updated_admins = [admin_id for admin_id in ADMIN_IDS if admin_id != telegram_id]
        current_admins = ",".join(map(str, updated_admins))
        set_key(".env", "ADMIN_IDS", current_admins)
        

        ADMIN_IDS = updated_admins
        
        return True
    except Exception as e:
        print(f"[ERR] Ошибка при удалении администратора: {e}")
        return False


def reload_admin_ids():
    """Перезагружает список администраторов из .env файла"""
    try:
        from config.config import ADMIN_IDS as new_admin_ids
        global ADMIN_IDS
        ADMIN_IDS = new_admin_ids
        return True
    except Exception as e:
        print(f"[ERR] Ошибка при перезагрузке администраторов: {e}")
        return False

async def export_attendance_to_excel(session: AsyncSession, output_file: str = None) -> str:
    """
    Экспортирует данные о посещаемости в Excel-файл.

    Args:
        session: SQLAlchemy сессия для доступа к базе данных
        output_file: Имя выходного файла (по умолчанию attendance_DD-MM-YYYY.xlsx)

    Returns:
        str: Путь к созданному файлу
    """
    try:
        # Если имя файла не указано, генерируем его с датой
        if output_file is None:
            timestamp = datetime.now(MOSCOW_TZ).strftime("%d-%m-%Y")
            output_file = f"attendance_{timestamp}.xlsx"
        
        # Базовый запрос с JOIN
        query = select(Attendance, User).join(User, Attendance.user_id == User.id)
        result = await session.execute(query)
        data = result.all()
        if not data:
            # Если данных нет, создаем пустой DataFrame
            df = pd.DataFrame(columns=["Дата", "ФИО", "Группа"])
        else:
            # Создаем DataFrame из результатов
            df = pd.DataFrame(
                [
                    {
                        "Дата": a.date.strftime("%d-%m-%Y") if a.date else "",
                        "ФИО": u.full_name if u.full_name else "",
                        "Группа": u.group if u.group else ""
                    }
                    for a, u in data
                ],
                columns=["Дата", "ФИО", "Группа"]
            )
        
        # Сортируем по дате и группе
        df = df.sort_values(by=["Дата", "Группа", "ФИО"])
        
        # Группируем данные по дням с разрывами и статистикой
        final_data = []
        
        if not df.empty:
            # Группируем по датам
            grouped_by_date = df.groupby("Дата")
            
            for date, day_data in grouped_by_date:
                # Добавляем данные за день
                for _, row in day_data.iterrows():
                    final_data.append({
                        "Дата": row["Дата"],
                        "ФИО": row["ФИО"],
                        "Группа": row["Группа"]
                    })
                
                # Добавляем статистику за день
                day_stats = day_data.groupby("Группа").size().reset_index(name="Количество")
                total_day_visits = len(day_data)
                unique_students_day = day_data["ФИО"].nunique()
                
                # Пустая строка для разделения
                final_data.append({"Дата": "", "ФИО": "", "Группа": ""})
                
                # Статистика по группам за день
                final_data.append({"Дата": "", "ФИО": f"СТАТИСТИКА ЗА {date}:", "Группа": ""})
                for _, stat_row in day_stats.iterrows():
                    final_data.append({
                        "Дата": "",
                        "ФИО": f"  Группа {stat_row['Группа']}:",
                        "Группа": f"{stat_row['Количество']} чел."
                    })
                
                # Общая статистика за день
                final_data.append({"Дата": "", "ФИО": f"  Всего посещений:", "Группа": f"{total_day_visits} чел."})
                
                # Разрыв между днями
                final_data.append({"Дата": "", "ФИО": "", "Группа": ""})
                final_data.append({"Дата": "", "ФИО": "─" * 50, "Группа": ""})
                final_data.append({"Дата": "", "ФИО": "", "Группа": ""})
            
            # Статистика по группам за весь период
            overall_group_stats = df.groupby("Группа").size().reset_index(name="Количество")
            final_data.append({"Дата": "", "ФИО": "ОБЩАЯ СТАТИСТИКА ПО ГРУППАМ (ВСЕГО):", "Группа": ""})
            for _, row in overall_group_stats.iterrows():
                final_data.append({
                    "Дата": "",
                    "ФИО": f"  Группа {row['Группа']}:",
                    "Группа": f"{row['Количество']} посещений"
                })
        
        # Создаем финальный DataFrame
        df = pd.DataFrame(final_data, columns=["Дата", "ФИО", "Группа"])
        
        # Сохраняем в Excel (используем встроенный движок xlwt для .xls)
        df.to_excel(output_file, index=False,engine='openpyxl')
        
        return output_file
        
    except Exception as e:
        print(f"[ERR] Ошибка при экспорте в Excel: {e}")
        raise e

async def export_users_to_excel(session: AsyncSession, output_file: str = None) -> str:
    try:

        if output_file is None:
            output_file = f"users.xlsx"

        # Базовый запрос с JOIN
        query = select(User)
        result = await session.execute(query)
        data = result.scalars().all()
        if not data:
            # Если данных нет, создаем пустой DataFrame
            df = pd.DataFrame(columns=["ФИО", "Группа","ТГ_АЙДИ"])
        else:
            # Создаем DataFrame из результатов
            df = pd.DataFrame(
                [
                    {

                        "ФИО": u.full_name if u.full_name else "",
                        "Группа": u.group if u.group else "",
                        "ТГ_АЙДИ": u.telegram_id if u.telegram_id else ""
                    }
                    for u in data
                ],
                columns=["Группа","ФИО","ТГ_АЙДИ"]
            )

        # Сортируем по дате и группе
        df = df.sort_values(by=["Группа","ФИО","ТГ_АЙДИ"])

        # Сохраняем в Excel (используем встроенный движок xlwt для .xls)
        df.to_excel(output_file, index=False, engine='openpyxl')

        return output_file

    except Exception as e:
        print(f"[ERR] Ошибка при экспорте в Excel: {e}")
        raise e

async def get_attendance_stats(session: AsyncSession) -> dict:
    """
    Получает статистику посещаемости за текущий день.
    
    Args:
        session: SQLAlchemy сессия для доступа к базе данных
        
    Returns:
        dict: Словарь со статистикой за день
    """
    try:
        # Получаем текущую дату в московском времени
        today = datetime.now(MOSCOW_TZ).date()
        
        # Запрос посещений за сегодня
        today_query = select(Attendance, User).join(User, Attendance.user_id == User.id).where(
            Attendance.date >= today
        )
        today_result = await session.execute(today_query)
        today_data = today_result.all()
        
        if not today_data:
            return {
                "total_today": 0,
                "group_stats_today": {},
                "fastest_student": None,
                "fastest_time": None,
                "message": "Сегодня еще никто не отметился"
            }
        
        # Общее количество посещений за день
        total_today = len(today_data)
        
        # Статистика по группам за день
        group_stats_today = {}
        for attendance, user in today_data:
            group = user.group if user.group else "Без группы"
            if group not in group_stats_today:
                group_stats_today[group] = 0
            group_stats_today[group] += 1
        
        # Находим того, кто отметился быстрее всех (самое раннее время)
        fastest_attendance = min(today_data, key=lambda x: x[0].date)
        fastest_student = fastest_attendance[1].full_name
        fastest_time = fastest_attendance[0].date.strftime("%H:%M:%S")
        
        return {
            "total_today": total_today,
            "group_stats_today": group_stats_today,
            "fastest_student": fastest_student,
            "fastest_time": fastest_time,
            "message": f"Сегодня отметилось {total_today} человек"
        }
        
    except Exception as e:
        print(f"[ERR] Ошибка при получении статистики: {e}")
        return {
            "total_today": 0,
            "group_stats_today": {},
            "fastest_student": None,
            "fastest_time": None,
            "message": "Ошибка при получении статистики"
        }