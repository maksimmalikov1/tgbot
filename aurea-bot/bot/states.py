"""FSM-состояния сценария записи."""
from aiogram.fsm.state import State, StatesGroup


class Booking(StatesGroup):
    service = State()   # выбор услуги
    date = State()      # выбор даты
    time = State()      # выбор времени
    name = State()      # ввод имени
    phone = State()     # ввод телефона
    confirm = State()   # подтверждение
