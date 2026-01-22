from __future__ import annotations
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from datetime import timedelta
from typing import Optional

async def create_invite_link(bot: Bot, chat_id: int, name: str) -> str:
    # Creates a join request link that can be used by the user.
    invite = await bot.create_chat_invite_link(chat_id=chat_id, name=name, creates_join_request=False)
    return invite.invite_link

async def kick_user(bot: Bot, chat_id: int, tg_user_id: int) -> None:
    # For supergroups: ban then unban to "kick" cleanly. For channels, this might fail.
    try:
        await bot.ban_chat_member(chat_id=chat_id, user_id=tg_user_id)
    except TelegramForbiddenError:
        return
    except TelegramBadRequest:
        return
