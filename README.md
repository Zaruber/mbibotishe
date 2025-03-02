# Telegram Бот Расписания МБИ СПб

Бот для Telegram, который парсит и отображает расписание занятий для студентов. 
Деплоит на https://deploy.cx

## Возможности

- Получение расписания на заданный период
- Парсинг и форматирование данных с официального сайта расписания
- Удобное отображение занятий с эмодзи и кликабельными ссылками

## Команды бота

- `/rasspisan ДД.ММ.ГГГГ - ДД.ММ.ГГГГ` - получение расписания на указанный период (например, `/rasspisan 02.03.2025 - 09.03.2025`)
- `/schedule` - отображение последнего загруженного расписания

## Технические детали

- Язык: Python 3.9+
- Библиотеки: python-telegram-bot, BeautifulSoup4, requests, nest_asyncio
- Парсинг HTML: регулярные выражения и BeautifulSoup
- Поддержка обработки некорректной HTML-структуры

## Установка и запуск

### Настройка токена

Перед запуском необходимо настроить токен бота:

1. Создайте копию файла `config_example.py` и назовите её `config.py`
2. Откройте `config.py` и замените `YOUR_BOT_TOKEN_HERE` на ваш токен от BotFather
3. При необходимости измените `GROUP_ID` на код вашей группы в системе расписания

### Через Docker

```bash
FROM python:3.9-slim

# Установка git
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Клонирование репозитория
RUN git clone --depth 1 https://github.com/Zaruber/mbibotishe.git . && \
    ls -la

# Копирование шаблона конфигурационного файла
RUN cp config_example.py config.py

# Устанавливаем ваш токен бота напрямую в Dockerfile
ENV BOT_TOKEN="ТОКЕН_БОТА"

# Заменяем токен в конфигурационном файле
RUN sed -i "s/YOUR_BOT_TOKEN_HERE/$BOT_TOKEN/g" config.py

# ID группы по умолчанию (если требуется другой, измените здесь)
ENV GROUP_ID="2471"
RUN sed -i "s/\"2471\"/\"$GROUP_ID\"/g" config.py

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Даем разрешение на запись файлов для временных HTML-файлов
RUN chmod -R 777 /app

# Установка переменных окружения для оптимизации Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Запускаем бота
CMD ["python", "bot.py"]
```

## Контрибьютинг

Предложения по улучшению функционала и исправлению ошибок приветствуются! Создавайте issue или pull request. 
