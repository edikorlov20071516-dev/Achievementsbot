import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота (замени на свой)
BOT_TOKEN = "8125367276:AAGAF5aCtopQB5Hg45Le3EjE3Q5OwAbs9mo"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# Классы состояний для FSM
class AchievementStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_category = State()
    waiting_for_search = State()
    waiting_for_edit_title = State()
    waiting_for_edit_description = State()
    waiting_for_edit_category = State()


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('achievements.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'Общее',
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


# Клавиатуры
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Добавить достижение")],
            [KeyboardButton(text="📋 Мои достижения"), KeyboardButton(text="🔍 Поиск")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🏷 Категории")],
            [KeyboardButton(text="❌ Удалить все")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_categories_keyboard():
    categories = ["🏆 Спорт", "💼 Работа", "📚 Учеба", "🎨 Творчество", "❤️ Личное", "➕ Другое"]
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=cat)] for cat in categories] + [[KeyboardButton(text="◀️ Назад")]],
        resize_keyboard=True
    )
    return keyboard


def get_edit_keyboard(achievement_id):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"edit_title_{achievement_id}")],
            [InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"edit_desc_{achievement_id}")],
            [InlineKeyboardButton(text="🏷 Изменить категорию", callback_data=f"edit_cat_{achievement_id}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{achievement_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_list")]
        ]
    )
    return keyboard


# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот для записи твоих достижений. Помогу тебе отслеживать прогресс и помнить о важных событиях.\n\n"
        "Используй кнопки ниже для управления:",
        reply_markup=get_main_keyboard()
    )


# Команда /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
📚 <b>Доступные команды:</b>

📝 <b>Добавить достижение</b> - записать новое достижение
📋 <b>Мои достижения</b> - посмотреть все записи
🔍 <b>Поиск</b> - найти достижения по ключевым словам
📊 <b>Статистика</b> - статистика по категориям
🏷 <b>Категории</b> - просмотр по категориям
❌ <b>Удалить все</b> - очистить все достижения

При добавлении достижения можно указать:
• Название (обязательно)
• Описание (по желанию)
• Категорию
    """
    await message.answer(help_text, parse_mode="HTML")


# Обработка кнопки "Добавить достижение"
@dp.message(lambda message: message.text == "📝 Добавить достижение")
async def add_achievement_start(message: Message, state: FSMContext):
    await state.set_state(AchievementStates.waiting_for_title)
    await message.answer("Введите название достижения:")


# Обработка ввода названия
@dp.message(AchievementStates.waiting_for_title)
async def add_achievement_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AchievementStates.waiting_for_description)
    await message.answer(
        "Введите описание достижения (или отправьте '-' чтобы пропустить):",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="- Пропустить")]],
            resize_keyboard=True
        )
    )


# Обработка ввода описания
@dp.message(AchievementStates.waiting_for_description)
async def add_achievement_description(message: Message, state: FSMContext):
    description = message.text if message.text != "- Пропустить" else ""
    await state.update_data(description=description)
    await state.set_state(AchievementStates.waiting_for_category)
    await message.answer(
        "Выберите категорию:",
        reply_markup=get_categories_keyboard()
    )


# Обработка выбора категории
@dp.message(AchievementStates.waiting_for_category)
async def add_achievement_category(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer("Главное меню:", reply_markup=get_main_keyboard())
        return

    # Убираем эмодзи из категории
    category = message.text
    emoji_map = {
        "🏆 Спорт": "Спорт",
        "💼 Работа": "Работа",
        "📚 Учеба": "Учеба",
        "🎨 Творчество": "Творчество",
        "❤️ Личное": "Личное",
        "➕ Другое": "Другое"
    }
    category = emoji_map.get(category, category)

    data = await state.get_data()
    title = data.get('title')
    description = data.get('description', '')

    # Сохраняем в базу данных
    conn = sqlite3.connect('achievements.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO achievements (user_id, title, description, category, date) VALUES (?, ?, ?, ?, ?)",
        (message.from_user.id, title, description, category, datetime.now().strftime("%d.%m.%Y"))
    )
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer(
        f"✅ Достижение успешно добавлено!\n\n"
        f"<b>{title}</b>\n"
        f"Категория: {category}\n"
        f"Описание: {description if description else 'не указано'}",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


# Обработка кнопки "Мои достижения"
@dp.message(lambda message: message.text == "📋 Мои достижения")
async def show_achievements(message: Message):
    conn = sqlite3.connect('achievements.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, description, category, date FROM achievements WHERE user_id = ? ORDER BY created_at DESC",
        (message.from_user.id,)
    )
    achievements = cursor.fetchall()
    conn.close()

    if not achievements:
        await message.answer("📭 У вас пока нет достижений. Добавьте первое!", reply_markup=get_main_keyboard())
        return

    # Отправляем каждое достижение отдельно
    for ach_id, title, desc, category, date in achievements:
        # Определяем эмодзи для категории
        emoji_map = {
            "Спорт": "🏆",
            "Работа": "💼",
            "Учеба": "📚",
            "Творчество": "🎨",
            "Личное": "❤️",
            "Другое": "➕"
        }
        cat_emoji = emoji_map.get(category, "📌")

        text = f"<b>{title}</b>\n"
        text += f"📅 {date} | {cat_emoji} {category}\n"
        if desc:
            text += f"📝 {desc}"

        # Кнопки для управления
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{ach_id}")]
            ]
        )

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


# Обработка кнопки "Редактировать"
@dp.callback_query(
    lambda c: c.data.startswith('edit_') and not c.data.startswith(('edit_title_', 'edit_desc_', 'edit_cat_')))
async def edit_achievement_menu(callback: types.CallbackQuery, state: FSMContext):
    ach_id = callback.data.split('_')[1]
    await state.update_data(current_achievement_id=ach_id)

    await callback.message.edit_text(
        "Выберите действие:",
        reply_markup=get_edit_keyboard(ach_id)
    )
    await callback.answer()


# Обработка изменения названия
@dp.callback_query(lambda c: c.data.startswith('edit_title_'))
async def edit_title_start(callback: types.CallbackQuery, state: FSMContext):
    ach_id = callback.data.split('_')[2]
    await state.update_data(edit_achievement_id=ach_id)
    await state.set_state(AchievementStates.waiting_for_edit_title)

    await callback.message.answer("Введите новое название:")
    await callback.message.delete()
    await callback.answer()


# Обработка ввода нового названия
@dp.message(AchievementStates.waiting_for_edit_title)
async def edit_title_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    ach_id = data.get('edit_achievement_id')
    new_title = message.text

    conn = sqlite3.connect('achievements.db')
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE achievements SET title = ? WHERE id = ? AND user_id = ?",
        (new_title, ach_id, message.from_user.id)
    )
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer("✅ Название успешно обновлено!", reply_markup=get_main_keyboard())


# Обработка изменения описания
@dp.callback_query(lambda c: c.data.startswith('edit_desc_'))
async def edit_description_start(callback: types.CallbackQuery, state: FSMContext):
    ach_id = callback.data.split('_')[2]
    await state.update_data(edit_achievement_id=ach_id)
    await state.set_state(AchievementStates.waiting_for_edit_description)

    await callback.message.answer("Введите новое описание (или отправьте '-' чтобы оставить пустым):")
    await callback.message.delete()
    await callback.answer()


# Обработка ввода нового описания
@dp.message(AchievementStates.waiting_for_edit_description)
async def edit_description_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    ach_id = data.get('edit_achievement_id')
    new_description = message.text if message.text != "-" else ""

    conn = sqlite3.connect('achievements.db')
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE achievements SET description = ? WHERE id = ? AND user_id = ?",
        (new_description, ach_id, message.from_user.id)
    )
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer("✅ Описание успешно обновлено!", reply_markup=get_main_keyboard())


# Обработка изменения категории
@dp.callback_query(lambda c: c.data.startswith('edit_cat_'))
async def edit_category_start(callback: types.CallbackQuery, state: FSMContext):
    ach_id = callback.data.split('_')[2]
    await state.update_data(edit_achievement_id=ach_id)
    await state.set_state(AchievementStates.waiting_for_edit_category)

    await callback.message.answer("Выберите новую категорию:", reply_markup=get_categories_keyboard())
    await callback.message.delete()
    await callback.answer()


# Обработка выбора новой категории
@dp.message(AchievementStates.waiting_for_edit_category)
async def edit_category_finish(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer("Главное меню:", reply_markup=get_main_keyboard())
        return

    # Убираем эмодзи из категории
    category = message.text
    emoji_map = {
        "🏆 Спорт": "Спорт",
        "💼 Работа": "Работа",
        "📚 Учеба": "Учеба",
        "🎨 Творчество": "Творчество",
        "❤️ Личное": "Личное",
        "➕ Другое": "Другое"
    }
    new_category = emoji_map.get(category, category)

    data = await state.get_data()
    ach_id = data.get('edit_achievement_id')

    conn = sqlite3.connect('achievements.db')
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE achievements SET category = ? WHERE id = ? AND user_id = ?",
        (new_category, ach_id, message.from_user.id)
    )
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer("✅ Категория успешно обновлена!", reply_markup=get_main_keyboard())


# Обработка удаления достижения
@dp.callback_query(lambda c: c.data.startswith('delete_'))
async def delete_achievement(callback: types.CallbackQuery):
    ach_id = callback.data.split('_')[1]

    conn = sqlite3.connect('achievements.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM achievements WHERE id = ? AND user_id = ?", (ach_id, callback.from_user.id))
    conn.commit()
    conn.close()

    await callback.message.edit_text("✅ Достижение удалено")
    await callback.answer("Удалено!")


# Обработка кнопки "Назад" в меню редактирования
@dp.callback_query(lambda c: c.data == "back_to_list")
async def back_to_list(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.clear()
    # Показываем список достижений заново
    await show_achievements(callback.message)


# Обработка поиска
@dp.message(lambda message: message.text == "🔍 Поиск")
async def search_start(message: Message, state: FSMContext):
    await state.set_state(AchievementStates.waiting_for_search)
    await message.answer("Введите ключевое слово для поиска:")


@dp.message(AchievementStates.waiting_for_search)
async def search_achievements(message: Message, state: FSMContext):
    search_term = message.text
    conn = sqlite3.connect('achievements.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT title, description, category, date FROM achievements WHERE user_id = ? AND (title LIKE ? OR description LIKE ?)",
        (message.from_user.id, f'%{search_term}%', f'%{search_term}%')
    )
    results = cursor.fetchall()
    conn.close()

    if not results:
        await message.answer(f"По запросу '{search_term}' ничего не найдено.")
    else:
        text = f"🔍 Найдено {len(results)} достижений:\n\n"
        for title, desc, category, date in results[:10]:
            text += f"• <b>{title}</b> ({category}, {date})\n"
        await message.answer(text, parse_mode="HTML")

    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_keyboard())


# Обработка статистики
@dp.message(lambda message: message.text == "📊 Статистика")
async def show_stats(message: Message):
    conn = sqlite3.connect('achievements.db')
    cursor = conn.cursor()

    # Общее количество
    cursor.execute("SELECT COUNT(*) FROM achievements WHERE user_id = ?", (message.from_user.id,))
    total = cursor.fetchone()[0]

    # По категориям
    cursor.execute(
        "SELECT category, COUNT(*) FROM achievements WHERE user_id = ? GROUP BY category",
        (message.from_user.id,)
    )
    categories = cursor.fetchall()

    conn.close()

    stats_text = f"📊 <b>Статистика достижений</b>\n\n"
    stats_text += f"Всего: <b>{total}</b>\n\n"

    if categories:
        stats_text += "🏷 <b>По категориям:</b>\n"
        for cat, count in categories:
            stats_text += f"  • {cat}: {count}\n"

    await message.answer(stats_text, parse_mode="HTML")


# Обработка категорий
@dp.message(lambda message: message.text == "🏷 Категории")
async def show_categories(message: Message):
    conn = sqlite3.connect('achievements.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT category, COUNT(*) FROM achievements WHERE user_id = ? GROUP BY category",
        (message.from_user.id,)
    )
    categories = cursor.fetchall()
    conn.close()

    if not categories:
        await message.answer("У вас пока нет достижений по категориям.")
        return

    # Определяем эмодзи для категорий
    emoji_map = {
        "Спорт": "🏆",
        "Работа": "💼",
        "Учеба": "📚",
        "Творчество": "🎨",
        "Личное": "❤️",
        "Другое": "➕"
    }

    text = "🏷 <b>Ваши категории:</b>\n\n"
    for cat, count in categories:
        emoji = emoji_map.get(cat, "📌")
        text += f"{emoji} {cat}: {count} достижений\n"

    await message.answer(text, parse_mode="HTML")


# Обработка удаления всех достижений
@dp.message(lambda message: message.text == "❌ Удалить все")
async def delete_all_confirm(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить всё", callback_data="confirm_delete_all")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")]
        ]
    )
    await message.answer(
        "⚠️ Вы уверены, что хотите удалить ВСЕ свои достижения? Это действие нельзя отменить!",
        reply_markup=keyboard
    )


@dp.callback_query(lambda c: c.data == "confirm_delete_all")
async def delete_all(callback: types.CallbackQuery):
    conn = sqlite3.connect('achievements.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM achievements WHERE user_id = ?", (callback.from_user.id,))
    conn.commit()
    conn.close()

    await callback.message.edit_text("✅ Все достижения удалены.")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "cancel_delete")
async def cancel_delete(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Операция отменена.", reply_markup=get_main_keyboard())
    await callback.answer()


# Обработка кнопки "Назад"
@dp.message(lambda message: message.text == "◀️ Назад")
async def go_back(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_keyboard())


# Запуск бота
async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())