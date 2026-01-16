import asyncio
import os
from typing import Optional

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv


NEWSAPI_URL = "https://newsapi.org/v2/everything"
NEWS_QUERY = "forex OR currency OR fx OR USD OR EUR"
NEWS_PAGE_SIZE = 5

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


def _get_newsapi_key() -> str:
    """Возвращает ключ NewsAPI из окружения."""

    load_dotenv()
    api_key: Optional[str] = os.getenv("NEWSAPI_KEY")
    if not api_key:
        raise RuntimeError(
            "Не найден NEWSAPI_KEY. Добавьте в .env строку "
            "NEWSAPI_KEY=ваш_ключ_newsapi"
        )
    return api_key


async def _fetch_forex_news_text() -> str:
    """Получает и форматирует 5 свежих новостей по форексу через NewsAPI."""

    api_key = _get_newsapi_key()
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for language in ("ru", "en"):
            params = {
                "q": NEWS_QUERY,
                "language": language,
                "sortBy": "publishedAt",
                "pageSize": str(NEWS_PAGE_SIZE),
            }
            headers = {"X-Api-Key": api_key}

            async with session.get(
                NEWSAPI_URL,
                params=params,
                headers=headers,
            ) as response:
                payload = await response.json(content_type=None)

            if response.status != 200:
                message = payload.get("message") if isinstance(payload, dict) else None
                details = f": {message}" if isinstance(message, str) else ""
                raise RuntimeError(f"Ошибка NewsAPI ({response.status}){details}")

            articles = payload.get("articles") if isinstance(payload, dict) else None
            if not isinstance(articles, list) or not articles:
                continue

            lines: list[str] = ["Новости форекс (свежие):"]
            for idx, item in enumerate(articles[:NEWS_PAGE_SIZE], start=1):
                if not isinstance(item, dict):
                    continue

                title = item.get("title")
                url = item.get("url")
                source = (item.get("source") or {}).get("name")

                title_text = title.strip() if isinstance(title, str) else "Без заголовка"
                url_text = url.strip() if isinstance(url, str) else ""
                source_text = (
                    f" ({source.strip()})" if isinstance(source, str) and source else ""
                )

                if url_text:
                    lines.append(f"{idx}. {title_text}{source_text}\n{url_text}")
                else:
                    lines.append(f"{idx}. {title_text}{source_text}")

            return "\n\n".join(lines)

    return "Не нашёл свежих новостей по форексу. Попробуйте позже."


bot = Bot(token=_get_token())
dp = Dispatcher()

# Вот в этом промежутке мы будем работать и писать новый код


@dp.message(Command("news"))
async def news(message: Message) -> None:
    try:
        text = await _fetch_forex_news_text()
    except aiohttp.ClientError:
        text = "Не удалось получить новости: ошибка сети/сервиса."
    except asyncio.TimeoutError:
        text = "Не удалось получить новости: превышено время ожидания."
    except RuntimeError as exc:
        text = f"Не удалось получить новости: {exc}"

    await message.answer(text)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())