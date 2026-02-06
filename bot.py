import asyncio
import re
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8469292735:AAEe7Iihd499ed0izn-84KALqnk2ElqI8Fw"
GROUP_ID = -1003717188130 
TRUSTED_ADMINS = [1295847583, 5818997833] 
# --------------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    nickname, age, kills, timezone, experience, user_tg = State(), State(), State(), State(), State(), State()

# Удобная клавиатура для часовых поясов
def get_tz_keyboard():
    buttons = [
        [KeyboardButton(text="МСК (Киев/Минск)"), KeyboardButton(text="МСК +1 (Самара)")],
        [KeyboardButton(text="МСК +2 (Урал)"), KeyboardButton(text="МСК +3 (Омск)")],
        [KeyboardButton(text="МСК +4 (Сибирь)"), KeyboardButton(text="МСК +5 (Иркутск)")],
        [KeyboardButton(text="МСК +7 (Владивосток)"), KeyboardButton(text="МСК -1 (Калининград)")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

# --- ОБРАБОТЧИКИ АНКЕТЫ ---

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    if message.chat.type != 'private': return 
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔥 Подать заявку", callback_data="start_anketa")]])
    await message.answer("Привет! Нажми на кнопку для заполнения анкеты в **Q9**.", reply_markup=kb)

@dp.callback_query(F.data == "start_anketa")
async def s1(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("1️⃣ Твой игровой ник:"); await state.set_state(Form.nickname); await c.answer()

@dp.message(Form.nickname)
async def s2(m: types.Message, state: FSMContext):
    await state.update_data(nickname=m.text); await m.answer("2️⃣ Твой возраст:"); await state.set_state(Form.age)

@dp.message(Form.age)
async def s3(m: types.Message, state: FSMContext):
    await state.update_data(age=m.text); await m.answer("3️⃣ Сколько всего киллов:"); await state.set_state(Form.kills)

@dp.message(Form.kills)
async def s4(m: types.Message, state: FSMContext):
    await state.update_data(kills=m.text)
    await m.answer("4️⃣ Выбери свой часовой пояс (разница с Москвой):", reply_markup=get_tz_keyboard())
    await state.set_state(Form.timezone)

@dp.message(Form.timezone)
async def s5(m: types.Message, state: FSMContext):
    # Если ввел руками, а не кнопкой — тоже примем, но кнопки удобнее
    await state.update_data(timezone=m.text)
    await m.answer("5️⃣ Твой опыт в других кланах:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Form.experience)

@dp.message(Form.experience)
async def s6(m: types.Message, state: FSMContext):
    await state.update_data(experience=m.text); await m.answer("6️⃣ Впиши свой Юзернейм (@...):"); await state.set_state(Form.user_tg)

@dp.message(Form.user_tg)
async def final_step(m: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = m.from_user.id
    
    report = (
        f"<b>📝 НОВАЯ АНКЕТА</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 <b>Ник:</b> {data['nickname']}\n"
        f"🎂 <b>Возраст:</b> {data['age']}\n"
        f"🎯 <b>Киллы:</b> {data['kills']}\n"
        f"⏰ <b>Пояс:</b> {data['timezone']}\n"
        f"🤝 <b>Опыт:</b> {data['experience']}\n"
        f"📱 <b>Юзернейм:</b> <i>скрыт до одобрения</i>\n"
        f"━━━━━━━━━━━━━━"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принять", callback_data=f"ok|{uid}|{m.text}"),
        InlineKeyboardButton(text="❌ Отказ", callback_data=f"no|{uid}")
    ]])

    await bot.send_message(GROUP_ID, report, reply_markup=kb, parse_mode="HTML")
    await m.answer("✅ Анкета отправлена в штаб!")
    await state.clear()

# --- ЛОГИКА АДМИНОВ ---

@dp.callback_query(F.data.startswith("ok|") | F.data.startswith("no|"))
async def admin_action(callback: types.CallbackQuery):
    if callback.from_user.id not in TRUSTED_ADMINS:
        return await callback.answer("У тебя нет прав!", show_alert=True)

    parts = callback.data.split("|")
    action, target_uid = parts[0], int(parts[1])
    current_text = callback.message.html_text 

    if action == "ok":
        user_tg = parts[2]
        try:
            await bot.send_message(target_uid, "🎉 Вас приняли в сквад Q9!")
            res_text = f"\n\n🟢 <b>ПРИНЯТ</b>\nЮз: {user_tg}\nАдмин: {callback.from_user.first_name}"
        except:
            res_text = f"\n\n⚠️ <b>ПРИНЯТ (Бот в блоке)</b>\nЮз: {user_tg}\nАдмин: {callback.from_user.first_name}"
        
        new_text = current_text.replace("<i>скрыт до одобрения</i>", f"<b>{user_tg}</b>")
    else:
        try: await bot.send_message(target_uid, "❌ Твоя заявка отклонена.")
        except: pass
        new_text = current_text
        res_text = f"\n\n🔴 <b>ОТКАЗАНО</b>\nАдмин: {callback.from_user.first_name}"

    try:
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=new_text + res_text,
            parse_mode="HTML",
            reply_markup=None 
        )
        await callback.answer("Готово!")
    except Exception as e:
        logging.error(f"Ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())
