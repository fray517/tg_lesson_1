import asyncio
import os
from pathlib import Path
from typing import Optional

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

IMG_DIR = Path(__file__).resolve().parent / "img"

KRASNODAR: dict[str, float] = {
    "latitude": 45.0355,
    "longitude": 38.9753,
}


def _weather_code_to_ru(weather_code: int) -> str:
    """Преобразует код погоды Open-Meteo в описание на русском."""

    mapping: dict[int, str] = {
        0: "ясно",
        1: "преимущественно ясно",
        2: "переменная облачность",
        3: "пасмурно",
        45: "туман",
        48: "изморозь (туман)",
        51: "лёгкая морось",
        53: "умеренная морось",
        55: "сильная морось",
        56: "лёгкая переохлаждённая " "морось",
        57: "сильная переохлаждённая " "морось",
        61: "лёгкий дождь",
        63: "умеренный дождь",
        65: "сильный дождь",
        66: "лёгкий переохлаждённый дождь",
        67: "сильный переохлаждённый дождь",
        71: "лёгкий снег",
        73: "умеренный снег",
        75: "сильный снег",
        77: "снежные зёрна",
        80: "лёгкие ливни",
        81: "умеренные ливни",
        82: "сильные ливни",
        85: "лёгкие снегопады",
        86: "сильные снегопады",
        95: "гроза",
        96: "гроза с градом (лёгким)",
        99: "гроза с градом (сильным)",
    }
    return mapping.get(weather_code, f"неизвестно (код {weather_code})")


async def _fetch_krasnodar_weather() -> str:
    """Возвращает строку с текущей погодой в Краснодаре."""

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": KRASNODAR["latitude"],
        "longitude": KRASNODAR["longitude"],
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "weather_code,wind_speed_10m"
        ),
        "timezone": "Europe/Moscow",
    }
    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            payload = await response.json()

    current = payload.get("current", {})
    temperature = current.get("temperature_2m")
    feels_like = current.get("apparent_temperature")
    humidity = current.get("relative_humidity_2m")
    wind_speed = current.get("wind_speed_10m")
    weather_code_raw = current.get("weather_code")
    time_value = current.get("time")

    try:
        weather_code = int(weather_code_raw)
    except (TypeError, ValueError):
        return "Не удалось распознать ответ сервиса погоды."

    description = _weather_code_to_ru(weather_code)

    parts: list[str] = ["Погода в Краснодаре:"]
    if time_value:
        parts.append(f"время: {time_value}")
    parts.append(f"состояние: {description}")

    if temperature is not None:
        parts.append(f"температура: {temperature}°C")
    if feels_like is not None:
        parts.append(f"ощущается как: {feels_like}°C")
    if humidity is not None:
        parts.append(f"влажность: {humidity}%")
    if wind_speed is not None:
        parts.append(f"ветер: {wind_speed} м/с")

    return "\n".join(parts)


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

@dp.message(F.photo)
async def save_photo(message: Message) -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    if not message.photo:
        return

    photo = message.photo[-1]

    try:
        tg_file = await bot.get_file(photo.file_id)
        file_path = tg_file.file_path or ""
        suffix = Path(file_path).suffix or ".jpg"

        out_path = IMG_DIR / f"{photo.file_unique_id}{suffix}"
        await bot.download(photo, destination=out_path)
    except aiohttp.ClientError:
        await message.answer("Не удалось скачать фото: ошибка сети/сервиса.")
        return
    except (OSError, ValueError):
        await message.answer("Не удалось сохранить фото на диск.")
        return

    await message.answer(f"Фото сохранено: {out_path.name}")

@dp.message(Command("weather"))
async def weather(message: Message) -> None:
    try:
        text = await _fetch_krasnodar_weather()
    except aiohttp.ClientError:
        text = "Не удалось получить погоду: ошибка сети/сервиса."
    except asyncio.TimeoutError:
        text = "Не удалось получить погоду: превышено время ожидания."

    await message.answer(text)

@dp.message(Command("help"))
async def help(message: Message) -> None:
    await message.answer("Команды:\n/start\n/help\n/weather")

@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(f"Приветствую, {message.from_user.first_name}")


async def main() -> None:
    try:
        await dp.start_polling(bot)
    except (asyncio.CancelledError, KeyboardInterrupt):
        # Нормальное завершение при остановке процесса (Ctrl+C).
        pass
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())