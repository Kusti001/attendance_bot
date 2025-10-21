from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from . import keyboards as kb

from db.models import UserManager, AttendanceManager
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
        await message.answer("Вы уже зарегистрированы",reply_markup=kb.CheckIn_keyboard)
    else:
        await message.answer("Введите ФИО")
        await state.set_state(Registration.full_name)

@router.message(Registration.full_name)
async def enter_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    user_manager = UserManager()
    if await user_manager.check_full_name(message.text):
        await message.answer("Пользователь с таким ФИО уже зарегистрирован")
    else:
        await message.answer("Введите номер группы")
        await state.set_state(Registration.group)

@router.message(Registration.group)
async def enter_group(message: Message, state: FSMContext):
    await state.update_data(group=message.text)
    data = await state.get_data()
    await message.answer(
        "Подтвердите запись:\n"
        f"ФИО: {data['full_name']}\n"
        f"Группа: {data['group']}",
        reply_markup=kb.confirm_keyboard
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
        await callback.message.answer("✅ Регистрация завершена!",reply_markup=kb.CheckIn_keyboard)
        await state.clear()
    else:
        await state.clear()
        await callback.message.answer("Введите ФИО заново:")
        await state.set_state(Registration.full_name)

@router.message(F.text=="Отметиться")
async def start_mark_attendance(message: Message, state: FSMContext):
    # Проверяем, зарегистрирован ли пользователь
    user_manager = UserManager()
    if await user_manager.check_tg_id(str(message.from_user.id)):
        await state.set_state(AttendanceState.waiting_code)
        await message.answer("Введите код с экрана")
    else:
        await message.answer("Вы не зарегистрированы. Используйте /start для регистрации")
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
                await message.answer("Посещение отмечено!")
            else:
                await message.answer("Ошибка при отметке посещения")
        else:
            await message.answer("Неверный код или срок действия истёк!")
    except ValueError:
        await message.answer("Код должен быть числом!")
    finally:
        await state.clear()