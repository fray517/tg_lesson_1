import asyncio
import logging
import os
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from dotenv import load_dotenv

from keyboards import (
    CALLBACK_DYNAMIC_MORE,
    CALLBACK_DYNAMIC_OPTION_1,
    CALLBACK_DYNAMIC_OPTION_2,
    get_dynamic_options_keyboard,
    get_dynamic_start_keyboard,
    get_links_keyboard,
    get_main_menu,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)


def _get_token() -> str:
    """Возвращает токен бота из окружения."""

    load_dotenv()
    token: Optional[str] = os.getenv("TOKEN")
    if not token:
        raise RuntimeError(
            "Не найден TOKEN. Создайте файл .env рядом с main.py и добавьте "
            "строку TOKEN=ваш_токен_бота"
        )
    return token


bot = Bot(token=_get_token())
dp = Dispatcher()


def _get_user_name(message: Message) -> str:
    """Возвращает имя пользователя для подстановки в ответы."""

    if message.from_user is None:
        return "друг"
    return message.from_user.first_name or message.from_user.full_name or "друг"


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    """Показывает меню при /start."""

    await message.answer(
        "Меню:",
        reply_markup=get_main_menu(),
    )


@dp.message(Command("links"))
async def links_handler(message: Message) -> None:
    """Показывает инлайн-кнопки с URL-ссылками."""

    await message.answer(
        "Полезные ссылки:",
        reply_markup=get_links_keyboard(),
    )


@dp.message(Command("dynamic"))
async def dynamic_handler(message: Message) -> None:
    """Показывает динамическую инлайн-клавиатуру."""

    await message.answer(
        "Динамическое меню:",
        reply_markup=get_dynamic_start_keyboard(),
    )


@dp.callback_query(F.data == CALLBACK_DYNAMIC_MORE)
async def dynamic_more_handler(callback: CallbackQuery) -> None:
    """Заменяет кнопку 'Показать больше' на две опции."""

    if callback.message is not None:
        await callback.message.edit_reply_markup(
            reply_markup=get_dynamic_options_keyboard(),
        )
    await callback.answer()


@dp.callback_query(F.data.in_({CALLBACK_DYNAMIC_OPTION_1, CALLBACK_DYNAMIC_OPTION_2}))
async def dynamic_option_handler(callback: CallbackQuery) -> None:
    """Отправляет сообщение с выбранной опцией."""

    if callback.data == CALLBACK_DYNAMIC_OPTION_1:
        text = "Опция 1"
    else:
        text = "Опция 2"

    if callback.message is not None:
        await callback.message.answer(text)
    await callback.answer()


@dp.message(F.text == "Привет")
async def hello_handler(message: Message) -> None:
    """Отвечает на кнопку 'Привет'."""

    user_name = _get_user_name(message)
    await message.answer(f"Привет, {user_name}!")


@dp.message(F.text == "Пока")
async def bye_handler(message: Message) -> None:
    """Отвечает на кнопку 'Пока'."""

    user_name = _get_user_name(message)
    await message.answer(f"До свидания, {user_name}!")


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())