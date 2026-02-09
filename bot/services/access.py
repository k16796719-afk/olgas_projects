from __future__ import annotations

import json

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


def _extract_yoga_plan(payload) -> Optional[int]:
    """
    Returns 4 or 8 if can detect, else None.
    payload может быть dict или json-string.
    """
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return None
    if not isinstance(payload, dict):
        return None

    # ВАЖНО: у тебя payload сейчас хранится с РУССКИМИ ключами: "Тариф"
    v = payload.get("Тариф") or payload.get("План") or payload.get("Абонемент") or payload.get("product") or payload.get("plan")
    if not v:
        return None
    s = str(v).lower()

    # подстрой под свои названия, но суть такая:
    if "8" in s:
        return 8
    if "4" in s:
        return 4
    return None


def _yoga_channel_id(cfg, plan: int) -> Optional[int]:
    if plan == 4:
        return cfg.yoga_channel_4_id
    if plan == 8:
        return cfg.yoga_channel_8_id
    return None


async def _kick_from_chat(bot, chat_id: int, user_id: int) -> None:
    """
    Удаляем пользователя из канала/группы.
    В Telegram это делается баном, затем разбаном (чтобы мог зайти снова по ссылке).
    """
    try:
        await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        await bot.unban_chat_member(chat_id=chat_id, user_id=user_id, only_if_banned=True)
    except Exception:
        # если не был участником, нет прав, уже кикнут и т.п. — просто молчим
        pass
