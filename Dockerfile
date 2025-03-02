FROM python:3.9-slim

# Установка git
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Клонирование репозитория
# Замените на свой репозиторий после создания на GitHub
ARG REPO_URL=https://github.com/yourusername/Raspisanparser.git
ARG BRANCH=main
RUN git clone --depth 1 --branch ${BRANCH} ${REPO_URL} .

# Копирование шаблона конфигурационного файла
RUN cp config_example.py config.py

# Аргументы для настройки конфигурации
ARG BOT_TOKEN
ARG GROUP_ID=2471

# Если передан токен, заменяем его в конфигурационном файле
RUN if [ -n "$BOT_TOKEN" ]; then \
    sed -i "s/YOUR_BOT_TOKEN_HERE/$BOT_TOKEN/g" config.py; \
    fi

# Если передан ID группы, заменяем его в конфигурационном файле
RUN if [ -n "$GROUP_ID" ]; then \
    sed -i "s/\"2471\"/\"$GROUP_ID\"/g" config.py; \
    fi

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Даем разрешение на запись файлов для сохранения temporary HTML-файлов
RUN chmod -R 777 /app

# Установка переменных окружения для предотвращения создания .pyc файлов
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Запускаем бота
CMD ["python", "bot.py"] 