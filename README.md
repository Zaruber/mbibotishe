# Telegram Бот Расписания ИБИ СПб

Бот для Telegram, который парсит и отображает расписание занятий для студентов Института бизнеса и инноваций Санкт-Петербурга.

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
# Клонирование репозитория
git clone https://github.com/your-username/Raspisanparser.git
cd Raspisanparser

# Создание config.py
cp config_example.py config.py
# Отредактируйте config.py, указав ваш токен

# Сборка Docker-образа
docker build -t rasp-bot .

# Запуск контейнера
docker run -d --name rasp-bot-container rasp-bot
```

### Вручную

```bash
# Клонирование репозитория
git clone https://github.com/your-username/Raspisanparser.git
cd Raspisanparser

# Создание config.py
cp config_example.py config.py
# Отредактируйте config.py, указав ваш токен

# Установка зависимостей
pip install -r requirements.txt

# Запуск бота
python bot.py
```

## Контрибьютинг

Предложения по улучшению функционала и исправлению ошибок приветствуются! Создавайте issue или pull request. 