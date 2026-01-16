import asyncio
import os
from pathlib import Path
import subprocess
import tempfile
import html
import re
from typing import Optional

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile
from aiogram.types import Message
from dotenv import load_dotenv

IMG_DIR = Path(__file__).resolve().parent / "img"

KRASNODAR: dict[str, float] = {
    "latitude": 45.0355,
    "longitude": 38.9753,
}

LIBRE_TRANSLATE_URL = "https://libretranslate.de/translate"
GOOGLE_MOBILE_TRANSLATE_URL = "https://translate.google.com/m"

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


def _is_ffmpeg_available() -> bool:
    """Проверяет, доступен ли ffmpeg в PATH."""

    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False

    return True


async def _translate_to_english(text: str) -> str:
    """Переводит текст на английский через бесплатные публичные API."""

    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(
                GOOGLE_MOBILE_TRANSLATE_URL,
                params={
                    "sl": "auto",
                    "tl": "en",
                    "q": text,
                },
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            ) as response:
                response.raise_for_status()
                page = await response.text()

            match = re.search(r'class="result-container">(.*?)<', page)
            if match:
                translated = html.unescape(match.group(1)).strip()
                if translated:
                    return translated
        except (aiohttp.ClientError, re.error):
            pass

        payload = {
            "q": text,
            "source": "auto",
            "target": "en",
            "format": "text",
        }
        async with session.post(LIBRE_TRANSLATE_URL, json=payload) as response:
            response.raise_for_status()
            data = await response.json(content_type=None)

    translated = data.get("translatedText")
    if not isinstance(translated, str) or not translated.strip():
        raise ValueError("Пустой перевод")

    return translated.strip()


def _synthesize_tts_mp3(text: str, mp3_path: Path) -> None:
    """Синтезирует английскую речь в MP3."""

    from gtts import gTTS

    tts = gTTS(text=text, lang="en")
    tts.save(str(mp3_path))


def _convert_mp3_to_ogg_opus(mp3_path: Path, ogg_path: Path) -> None:
    """Конвертирует MP3 в OGG/OPUS (для voice-сообщений Telegram)."""

    from pydub import AudioSegment

    audio = AudioSegment.from_file(mp3_path, format="mp3")
    audio.export(str(ogg_path), format="ogg", codec="libopus")


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
    await message.answer("Команды:\n/start\n/help\n/weather\n/voice")

@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(f"Приветствую, {message.from_user.first_name}")


@dp.message(Command("voice"))
async def voice(message: Message) -> None:
    if message.reply_to_message and message.reply_to_message.voice:
        await message.answer_voice(message.reply_to_message.voice.file_id)
        return

    if not message.text:
        await message.answer(
            "Чтобы отправить голосовое, используйте:\n"
            "/voice <file_id|url>\n"
            "или ответьте на голосовое и отправьте /voice"
        )
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "Чтобы отправить голосовое, используйте:\n"
            "/voice <file_id|url>\n"
            "или ответьте на голосовое и отправьте /voice"
        )
        return

    voice_id_or_url = parts[1].strip()
    await message.answer_voice(voice_id_or_url)


@dp.message(F.text & ~F.text.startswith("/"))
async def translate_and_voice(message: Message) -> None:
    if not message.text or not message.text.strip():
        return

    source_text = message.text.strip()

    try:
        translated = await _translate_to_english(source_text)
    except aiohttp.ClientError:
        await message.answer("Не удалось перевести текст: ошибка сети/сервиса.")
        return
    except (asyncio.TimeoutError, ValueError):
        await message.answer("Не удалось перевести текст.")
        return

    await message.answer(translated)

    with tempfile.TemporaryDirectory() as tmp_dir:
        mp3_path = Path(tmp_dir) / "tts.mp3"
        ogg_path = Path(tmp_dir) / "tts.ogg"

        try:
            _synthesize_tts_mp3(translated, mp3_path)
        except Exception:
            await message.answer("Не удалось озвучить текст.")
            return

        if _is_ffmpeg_available():
            try:
                _convert_mp3_to_ogg_opus(mp3_path, ogg_path)
                await message.answer_voice(FSInputFile(str(ogg_path)))
                return
            except Exception:
                pass

        await message.answer_audio(FSInputFile(str(mp3_path)))


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