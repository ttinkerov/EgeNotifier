from aiogram.fsm.state import State, StatesGroup


class AuthFlow(StatesGroup):
    name = State()
    region = State()
    document = State()
    captcha = State()


class AdminFlow(StatesGroup):
    broadcast = State()
