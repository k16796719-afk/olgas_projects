from __future__ import annotations
from aiogram import Bot
from aiogram.types import InputMediaPhoto
from bot.keyboards.keyboards import admin_approve_kb

async def notify_admins_with_proof(bot: Bot, admin_ids: list[int], text_md: str, proof_file_id: str, payment_id: int):
    # send photo/document if possible. Telegram stores photo/file_id.
    for aid in admin_ids:
        try:
            await bot.send_photo(
                chat_id=aid,
                photo=proof_file_id,
                caption=text_md,
                parse_mode="HTML",
                reply_markup=admin_approve_kb(payment_id),
            )
        except Exception:
            # fallback text only
            await bot.send_message(
                chat_id=aid,
                text=text_md + "\n\n(Не смог прикрепить медиа, проверь в истории чата пользователя.)",
                parse_mode="HTML",
                reply_markup=admin_approve_kb(payment_id),
            )
