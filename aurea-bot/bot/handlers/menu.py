"""Главное меню и информационные разделы: услуги, о враче, контакты."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot import keyboards as kb
from data import load_services, texts

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == kb.CB_MENU)
async def to_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.answer(texts.MENU_TITLE, reply_markup=kb.main_menu())
    await cb.answer()


@router.callback_query(F.data == kb.CB_SERVICES)
async def show_services(cb: CallbackQuery) -> None:
    await cb.message.answer(texts.services_list(), reply_markup=kb.services_kb(load_services()))
    await cb.answer()


@router.callback_query(F.data == kb.CB_DOCTOR)
async def show_doctor(cb: CallbackQuery) -> None:
    await cb.message.answer(texts.DOCTOR, reply_markup=kb.back_menu_kb())
    await cb.answer()


@router.callback_query(F.data == kb.CB_CONTACTS)
async def show_contacts(cb: CallbackQuery) -> None:
    await cb.message.answer(texts.CONTACTS, reply_markup=kb.contacts_kb())
    await cb.answer()
