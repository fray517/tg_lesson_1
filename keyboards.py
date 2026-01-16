from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

CALLBACK_DYNAMIC_MORE = "dynamic_more"
CALLBACK_DYNAMIC_OPTION_1 = "dynamic_option_1"
CALLBACK_DYNAMIC_OPTION_2 = "dynamic_option_2"


def get_main_menu() -> ReplyKeyboardMarkup:
    """Возвращает главное меню с кнопками."""

    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Привет"))
    builder.add(KeyboardButton(text="Пока"))
    builder.adjust(2)
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…",
    )


def get_links_keyboard() -> InlineKeyboardMarkup:
    """Возвращает инлайн-кнопки с URL-ссылками."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Новости",
                    url="https://ria.ru/world/",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Музыка",
                    url="https://radiopotok.ru/radio/221",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Видео",
                    url="https://www.youtube.com/watch?v=ZRqHzvA6OvY",
                )
            ],
        ]
    )


def get_dynamic_start_keyboard() -> InlineKeyboardMarkup:
    """Возвращает стартовую инлайн-клавиатуру для /dynamic."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Показать больше",
                    callback_data=CALLBACK_DYNAMIC_MORE,
                )
            ]
        ]
    )


def get_dynamic_options_keyboard() -> InlineKeyboardMarkup:
    """Возвращает инлайн-клавиатуру с опциями для /dynamic."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Опция 1",
                    callback_data=CALLBACK_DYNAMIC_OPTION_1,
                ),
                InlineKeyboardButton(
                    text="Опция 2",
                    callback_data=CALLBACK_DYNAMIC_OPTION_2,
                ),
            ]
        ]
    )

