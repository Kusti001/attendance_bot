from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
import os
from datetime import datetime
from utilits.utilits import export_attendance_to_excel, is_admin, get_attendance_stats, add_admin, remove_admin, get_admin_ids
from . import keyboards as kb
from config.config import MOSCOW_TZ
from db.models import UserManager, AttendanceManager, async_session
router = Router()


class Registration(StatesGroup):
    full_name = State()
    group = State()
    confirmation = State()

class AttendanceState(StatesGroup):
    waiting_code = State()

@router.message(CommandStart())
async def start_registration(message: Message, state: FSMContext):
    await state.clear()
    user_manager = UserManager()
    if await user_manager.check_tg_id(message.from_user.id):
        keyboard = kb.admin_keyboard if is_admin(message.from_user.id) else kb.student_keyboard
        await message.answer("Вы уже зарегистрированы",reply_markup=keyboard)
    else:
        await message.answer("👋 Добро пожаловать! Введите ваше ФИО для регистрации в формате: Иванов Иван Иванович\n⚠️ Внимание! Указывайте данные корректно: ФИО нельзя изменить, регистрация возможна только один раз!")
        await state.set_state(Registration.full_name)

@router.message(Registration.full_name)
async def enter_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    user_manager = UserManager()
    if await user_manager.check_full_name(message.text):
        await message.answer("❌ Пользователь с таким ФИО уже зарегистрирован. Обратитесь к администратору")
    else:
        await message.answer("📚 Теперь введите номер вашей группы в формате: 5132704/50001")
        await state.set_state(Registration.group)

@router.message(Registration.group)
async def enter_group(message: Message, state: FSMContext):
    await state.update_data(group=message.text)
    data = await state.get_data()
    await message.answer(
        "📋 **Подтвердите ваши данные:**\n\n"
        f"👤 **ФИО:** {data['full_name']}\n"
        f"🎓 **Группа:** {data['group']}\n\n"
        "Всё верно?",
        reply_markup=kb.confirm_keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(Registration.confirmation)

@router.callback_query(Registration.confirmation)
async def confirm(callback: CallbackQuery, state: FSMContext):
    # ОБЯЗАТЕЛЬНО отвечаем на callback
    await callback.answer()
    if callback.data == 'confirm':
        data = await state.get_data()
        user_manager = UserManager()
        await user_manager.post(telegram_id=callback.from_user.id,full_name=data['full_name'],group=data['group'])
        # Показываем соответствующую клавиатуру в зависимости от роли
        keyboard = kb.admin_keyboard if is_admin(callback.from_user.id) else kb.student_keyboard
        await callback.message.answer("🎉 **Регистрация успешно завершена!**\n\nТеперь вы можете отмечаться на занятиях!", reply_markup=keyboard, parse_mode="Markdown")
        await state.clear()
    else:
        await state.clear()
        await callback.message.answer("🔄 Начинаем регистрацию заново. Введите ваше ФИО:")
        await state.set_state(Registration.full_name)

@router.message(F.text.in_(["Отметиться", "📝 Отметиться"]))
async def start_mark_attendance(message: Message, state: FSMContext):
    # Проверяем, зарегистрирован ли пользователь
    user_manager = UserManager()
    if await user_manager.check_tg_id(message.from_user.id):
        attendance_manager = AttendanceManager()
        if await attendance_manager.is_marked_today(message.from_user.id):
            await message.answer("Вы уже отмечались сегодня")
            return
        await state.set_state(AttendanceState.waiting_code)
        await message.answer("Введите код с экрана для отметки посещения")
    else:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации")
        return

@router.message(AttendanceState.waiting_code)
async def process_code(message: Message, state: FSMContext, generator):
    attendance_manager = AttendanceManager()
    code_str = message.text.strip()
    try:
        code = int(code_str)
        if generator.is_code_valid(code):
            success = await attendance_manager.post(message.from_user.id)
            if success:
                await message.answer("✅ **Посещение успешно отмечено!**")
                await state.clear()
            else:
                await message.answer("⚠️ Вы уже отмечались сегодня!")
                await state.clear()
        else:
            await message.answer("❌ Неверный код или срок действия истёк! Попробуйте еще раз.")
    except ValueError:
        await message.answer("⚠️ Код должен быть числом! Введите только цифры.")

@router.message(F.text.in_(["📁 Экспорт", "Экспорт"]))
async def export_attendance(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Эта команда доступна только администраторам!")
        return
    
    try:
        # Создаем новую сессию для экспорта
        async with async_session() as session:
            # Вызываем функцию экспорта напрямую (она уже асинхронная)
            output_file = await export_attendance_to_excel(session)
            
            # Проверяем, что файл создался
            if os.path.exists(output_file):
                await message.answer_document(FSInputFile(output_file))
                # Удаляем временный файл после отправки
                os.remove(output_file)
            else:
                await message.answer("❌ Ошибка: файл не был создан")
                
    except Exception as e:
        await message.answer(f"❌ Ошибка при экспорте данных: {str(e)}")

@router.message(F.text.in_(["📊 Статистика", "Статистика"]))
async def get_stats(message: Message):
    """Получение статистики посещаемости за день"""
    if not is_admin(message.from_user.id):
        await message.answer("Эта команда доступна только администраторам!")
        return
    
    try:
        async with async_session() as session:
            stats = await get_attendance_stats(session)
            
            # Формируем сообщение со статистикой за день
            stats_text = f"**Статистика за {datetime.now(MOSCOW_TZ).strftime("%d-%m-%Y")}:**\n\n"
            stats_text += f"{stats['message']}\n\n"
            
            if stats['total_today'] > 0:
                # Статистика по группам
                if stats['group_stats_today']:
                    stats_text += "**По группам:**\n"
                    for group, count in stats['group_stats_today'].items():
                        stats_text += f"• {group}: {count} чел.\n"
                    stats_text += "\n"
                
                # Самый быстрый студент
                if stats['fastest_student']:
                    stats_text += f"🏃‍♂️ **Первый отметился:**\n"
                    stats_text += f"• {stats['fastest_student']} в {stats['fastest_time']}\n"
            else:
                stats_text += "Сегодня еще никто не отметился"
            
            await message.answer(stats_text, parse_mode="Markdown")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении статистики: {str(e)}")

@router.message(Command("admins"))
async def manage_admins(message: Message):
    """Управление администраторами (только для супер-админов)"""
    # Проверяем, что пользователь является администратором
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды!")
        return
    
    admin_list = get_admin_ids()
    admin_text = "👥 **Список администраторов:**\n\n"
    
    if admin_list:
        for i, admin_id in enumerate(admin_list, 1):
            admin_text += f"{i}. `{admin_id}`\n"
    else:
        admin_text += "Администраторы не найдены"
    
    admin_text += "\n**Команды:**\n"
    admin_text += "• `/add_admin <ID>` - добавить администратора\n"
    admin_text += "• `/remove_admin <ID>` - удалить администратора\n"
    admin_text += "• `/admins` - показать список администраторов"
    
    await message.answer(admin_text, parse_mode="Markdown")

@router.message(Command("add_admin"))
async def add_admin_command(message: Message):
    """Добавление администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды!")
        return
    
    # Получаем ID из команды
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("❌ Использование: `/add_admin <ID>`\nПример: `/add_admin 123456789`")
        return
    
    try:
        new_admin_id = int(command_parts[1])
        
        # Проверяем, что пользователь существует
        user_manager = UserManager()
        if not await user_manager.check_tg_id(new_admin_id):
            await message.answer("❌ Пользователь с таким ID не зарегистрирован в боте!")
            return
        
        # Добавляем администратора
        if add_admin(new_admin_id):
            await message.answer(f"✅ Пользователь `{new_admin_id}` добавлен в администраторы!", parse_mode="Markdown")
        else:
            await message.answer(f"⚠️ Пользователь `{new_admin_id}` уже является администратором!", parse_mode="Markdown")
            
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении администратора: {str(e)}")

@router.message(Command("remove_admin"))
async def remove_admin_command(message: Message):
    """Удаление администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды!")
        return
    
    # Получаем ID из команды
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("❌ Использование: `/remove_admin <ID>`\nПример: `/remove_admin 123456789`")
        return
    
    try:
        admin_id_to_remove = int(command_parts[1])
        
        # Нельзя удалить самого себя
        if admin_id_to_remove == message.from_user.id:
            await message.answer("❌ Вы не можете удалить сами себя из администраторов!")
            return
        
        # Удаляем администратора
        if remove_admin(admin_id_to_remove):
            await message.answer(f"✅ Пользователь `{admin_id_to_remove}` удален из администраторов!", parse_mode="Markdown")
        else:
            await message.answer(f"⚠️ Пользователь `{admin_id_to_remove}` не является администратором!", parse_mode="Markdown")
            
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при удалении администратора: {str(e)}")

@router.message(Command("help"))
async def help_command(message: Message):
    """Показывает справку по командам"""
    help_text = """
🤖 **Бот учета посещаемости**

**Основные команды:**
/start - Начать работу с ботом
/help - Показать эту справку
/status - Показать ваш профиль
/myid - Показать ваш ID

**Для студентов:**
📝 Отметиться - Отметить посещение

**Для администраторов:**
📊 Статистика - Показать статистику за день
📁 Экспорт - Экспортировать данные в Excel

**Как пользоваться:**
1. Нажмите /start для регистрации
2. Введите ваше ФИО и номер группы
3. Подтвердите регистрацию
4. Используйте кнопку "Отметиться" для отметки посещения
5. Введите код с экрана для подтверждения

**Поддержка:** Обратитесь к администратору при возникновении проблем
    """
    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("status"))
async def status_command(message: Message):
    """Показывает статус пользователя"""
    user_manager = UserManager()
    if await user_manager.check_tg_id(message.from_user.id):
        user = await user_manager.get(message.from_user.id)
        status_text = f"""
👤 **Ваш профиль:**
📝 ФИО: {user.full_name}
🎓 Группа: {user.group}
🔑 Роль: {'Администратор' if is_admin(message.from_user.id) else 'Студент'}

✅ Вы зарегистрированы и можете отмечаться!
        """
        keyboard = kb.admin_keyboard if is_admin(message.from_user.id) else kb.student_keyboard
        await message.answer(status_text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации")


@router.message(Command("myid"))
async def get_my_id(message: Message):
    """Показывает ID пользователя"""
    await message.answer(f"**Ваш ID:** `{message.from_user.id}`\n\nИспользуйте этот ID для решения проблем с регистрацией", parse_mode="Markdown")



@router.message(Command("reset_user"))
async def reset_user(message: Message):
    """Сброс пользователя"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды!")
        return
    
    # Получаем ID из команды
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("❌ Использование: `/reset_user <ID>`\nПример: `/reset_user 123456789`")
        return
    else:
        user_manager = UserManager()
        if await user_manager.check_tg_id(command_parts[1]):
            await user_manager.delete(command_parts[1])
            await message.answer(f"✅ Пользователь `{command_parts[1]}` сброшен!")
        else:
            await message.answer(f"❌ Пользователь с таким ID не зарегистрирован!")

@router.message(Command("force_mark"))
async def force_mark(message: Message):
    """Форсированная отметка"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды!")
        return
    
    # Получаем ID из команды
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("❌ Использование: `/force_mark <ID>`\nПример: `/force_mark 123456789`")
        return
    else:
        user_manager = UserManager()
        if await user_manager.check_tg_id(command_parts[1]):
            attendance_manager = AttendanceManager()
            success = await attendance_manager.post(message.from_user.id)
            if success:
                await message.answer(f"✅ Пользователь `{command_parts[1]}` отмечен!")
            await message.answer(f"❌ Ошибка!")
        else:
            await message.answer(f"❌ Пользователь с таким ID не зарегистрирован!")
