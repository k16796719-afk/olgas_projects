from __future__ import annotations
from aiogram.fsm.state import State, StatesGroup

class YogaSurvey(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()
    q6 = State()
