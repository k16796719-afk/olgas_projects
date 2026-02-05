from __future__ import annotations
from dataclasses import dataclass

# aiogram CallbackData
from aiogram.filters.callback_data import CallbackData

class YF(CallbackData, prefix="yf"):
    action: str   # start, a, skip, done6, toggle6, renew
    q: int = 0    # номер вопроса
    v: str = ""   # значение

# action:
# start -> начать опрос
# a     -> ответ на вопрос (single-choice)
# skip  -> пропустить вопрос
# toggle6 -> переключить вариант для q6
# done6 -> завершить q6
# renew -> перейти к оплате/продлению
