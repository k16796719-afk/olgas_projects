from aiogram.fsm.state import State, StatesGroup

class LangFlow(StatesGroup):
    goal = State()
    level = State()
    freq = State()
    product = State()
    payment = State()
    wait_proof = State()

class YogaFlow(StatesGroup):
    wait_intro = State()
    plan = State()
    payment = State()
    wait_proof = State()

class AstroFlow(StatesGroup):
    sphere = State()
    fmt = State()
    payment = State()
    wait_proof = State()

class MentorFlow(StatesGroup):
    plan = State()
    payment = State()
    wait_proof = State()
