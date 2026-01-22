from __future__ import annotations
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from bot.keyboards import main_menu_kb

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, db, cfg):
    await db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        "Привет! Выбери направление:",
        reply_markup=main_menu_kb()
    )

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=main_menu_kb())

@router.callback_query(lambda c: c.data == "menu")
async def cb_menu(call: CallbackQuery):
    await call.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    await call.answer()
