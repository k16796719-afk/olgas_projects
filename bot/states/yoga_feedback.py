# states/yoga_feedback.py
from aiogram.fsm.state import StatesGroup, State

class YogaFeedback(StatesGroup):
    q1_difficulty = State()
    q2_tempo = State()
    q3_feelings = State()
    q4_format = State()
    q5_frequency = State()
    q6_types = State()
