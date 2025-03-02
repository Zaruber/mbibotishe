import os
import logging
import asyncio
import requests
import re
import nest_asyncio  # Добавляем nest_asyncio для решения проблемы с циклами
from bs4 import BeautifulSoup
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

# Проверяем наличие файла конфигурации
try:
    from config import BOT_TOKEN, GROUP_ID
except ImportError:
    # Если файл не найден, выводим инструкцию и завершаем программу
    print("""
    ОШИБКА: Файл конфигурации не найден!
    
    Создайте файл config.py на основе config_example.py:
    1. Скопируйте config_example.py в config.py
    2. Откройте config.py и укажите токен вашего Telegram бота
    
    Пример:
    BOT_TOKEN = "ваш_токен_бота"
    GROUP_ID = "2471"  # ID вашей группы в системе расписания
    """)
    import sys
    sys.exit(1)

# Применяем патч для nested event loops
nest_asyncio.apply()

# Функция для предварительной обработки HTML
def preprocess_html(html_content):
    """
    Исправляет проблемы со структурой HTML перед парсингом.
    """
    # Исправляем ячейки, находящиеся вне строк (сразу после </tr>)
    html_content = re.sub(r'</tr>\s*(<td[^>]*>)', r'</tr><tr>\1', html_content)
    
    # Добавляем закрывающий </tr> после последней ячейки в строке, если его нет
    html_content = re.sub(r'(</td>)\s*(<tr|<table|$)', r'\1</tr>\2', html_content)
    
    # Исправляем атрибуты href в тегах <a>, заключая URL в кавычки
    html_content = re.sub(r'<a\s+href=([^ >]+)([^>]*?)>', r'<a href="\1"\2>', html_content)
    
    # Удаляем переносы строк внутри тегов <a>
    html_content = re.sub(r'<a([^>]*?)[\r\n]+([^>]*?)>', r'<a\1 \2>', html_content)
    
    # Заменяем неразрывные пробелы на обычные для упрощения парсинга
    html_content = html_content.replace('&nbsp;', ' ')
    
    return html_content

# Функция для извлечения деталей занятия
def extract_lesson_details(cell):
    """Извлекает подробную информацию о занятии из ячейки таблицы."""
    if not cell or not hasattr(cell, 'text'):
        return None
        
    text = cell.text.strip()
    
    # Пустая ячейка
    if not text or text == " ":
        return None
    
    # Извлечение ссылки на занятие, если есть
    link = cell.find('a')
    link_url = None
    if link and 'href' in link.attrs:
        link_url = link['href'].strip()
        # Удаляем переносы строк и пробелы из URL
        link_url = link_url.replace('\n', '').replace('\r', '').replace(' ', '%20')
    
    # Проверка, есть ли пометка "ОНЛАЙН"
    is_online = 'ОНЛАЙН' in text
    
    # Регулярные выражения для более точного извлечения деталей занятия
    # Паттерн: Предмет -Тип, Преподаватель, ауд. Аудитория
    
    result = {
        'full_text': text,
        'is_online': is_online,
        'link': link_url
    }
    
    # Используем регулярное выражение для извлечения предмета и типа занятия
    subject_type_match = re.match(r'^([^,]+?)(?:\s+-([^,]+))?(?:,|$)', text)
    if subject_type_match:
        if subject_type_match.group(1):
            result['subject'] = subject_type_match.group(1).strip()
        if subject_type_match.group(2):
            result['lesson_type'] = subject_type_match.group(2).strip()
    
    # Извлекаем преподавателя (второй элемент после запятой)
    teacher_match = re.search(r',\s*([^,]+?)\s*(?:,|$)', text)
    if teacher_match:
        result['teacher'] = teacher_match.group(1).strip()
    
    # Извлекаем аудиторию (после "ауд.")
    classroom_match = re.search(r'ауд\.\s*([^,\s]+)', text)
    if classroom_match:
        result['classroom'] = classroom_match.group(1).strip()
    
    return result

# Функция для правильного форматирования URL для Markdown
def format_markdown_url(url):
    """
    Форматирует URL для использования в Markdown-ссылках Telegram.
    Экранирует специальные символы и обеспечивает совместимость.
    """
    if not url:
        return ""
        
    # Убедимся, что URL не содержит пробелов и переносов строк
    url = url.strip().replace('\n', '').replace('\r', '').replace(' ', '%20')
    
    # Экранируем специальные символы в URL для Markdown
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        url = url.replace(char, f"\\{char}")
        
    return url

# Функция для обработки URL для безопасного использования в HTML
def sanitize_url_for_html(url):
    """
    Подготавливает URL для безопасного использования в HTML-тегах.
    Убирает проблемные символы и делает URL совместимым с HTML.
    """
    if not url:
        return ""
    
    # Удаляем пробелы и переносы строк
    url = url.strip().replace('\n', '').replace('\r', '')
    
    # Замена пробелов на %20
    url = url.replace(' ', '%20')
    
    # Экранируем спецсимволы HTML
    url = url.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    url = url.replace('"', '&quot;').replace("'", '&#39;')
    
    return url

# Функция для парсинга расписания с использованием регулярных выражений и BeautifulSoup
def parse_schedule():
    """
    Универсальный парсер расписания, устойчивый к проблемам структуры HTML.
    Использует выявленные паттерны для более точного извлечения данных.
    """
    if not os.path.exists('templeraspisan.html'):
        logging.error("Файл с расписанием не найден.")
        return "Файл с расписанием не найден."

    try:
        with open('templeraspisan.html', 'r', encoding='utf-8') as file:
            html_content = file.read()
            
        # Предварительная обработка HTML для исправления структурных проблем
        html_content = preprocess_html(html_content)
            
        # Создаем объект BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Получение названия группы из заголовка
        group_title = soup.find('h4')
        group_title_text = group_title.text.strip() if group_title else "Расписание занятий"
        
        # Начинаем формировать результат, используя HTML теги вместо Markdown
        result = f"📅 <b>{group_title_text}</b>\n\n"
        
        # Находим таблицу с расписанием
        table = soup.find('table')
        if not table:
            logging.warning("Таблица с расписанием не найдена!")
            return f"{result}\nТаблица с расписанием не найдена!"
        
        # Извлекаем временные интервалы из HTML
        # Ищем ячейки с временными слотами по характерному стилю background-color: #f6ecc8
        time_slots = []
        time_cells = table.select('td[style*="background-color: #f6ecc8"]')
        
        for cell in time_cells:
            if cell.find('b'):  # Временные слоты обычно внутри <b> тегов
                slot_text = cell.text.strip()
                if '18:30' in slot_text or '20:10' in slot_text:
                    time_slots.append(slot_text)
        
        # Если не нашли по стилю, ищем по тексту
        if not time_slots:
            for td in table.find_all('td'):
                td_text = td.text.strip()
                if '18:30' in td_text or '20:10' in td_text:
                    time_slots.append(td_text)
        
        logging.info(f"Найденные временные слоты: {time_slots}")
        
        # Словарь для цветов в зависимости от типа занятия
        colors = {
            'Лекц': '🟢',  # зеленый
            'Прак': '🔵',  # синий
            'Экз': '🔴',   # красный
            'Зач': '🟠',   # оранжевый
            'Лаб': '🟣',   # фиолетовый
            'default': '📚'  # книга (по умолчанию)
        }
        
        # Обрабатываем строки с данными
        # Ищем строки, которые содержат дату (паттерн ДД.ММ День)
        lesson_rows = []
        
        # Ищем строки с данными расписания, они имеют паттерн даты в первой ячейке
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if not cells:
                continue
                
            # Проверяем, содержит ли первая ячейка дату
            date_cell = cells[0]
            date_text = date_cell.text.strip()
            
            # Проверяем по паттерну ДД.ММ День или Д.ММ День
            if re.search(r'\d{1,2}\.\d{2}\s+\w{2}\b', date_text):
                lesson_rows.append(row)
        
        # Обрабатываем найденные строки с занятиями
        for row in lesson_rows:
            cells = row.find_all('td')
            
            if not cells or len(cells) < 2:
                continue
            
            # Первая ячейка в строке содержит дату
            date_cell = cells[0]
            date_text = date_cell.text.strip()
            
            # Добавляем дату в результат (используем HTML-тег <b> вместо Markdown *)
            result += f"\n🗓 <b>{date_text}</b>\n\n"
            
            # Обрабатываем остальные ячейки в строке (занятия по времени)
            for idx, cell in enumerate(cells[1:], 0):
                # Определяем временной слот
                time_slot = time_slots[idx] if idx < len(time_slots) else f"Слот {idx+1}"
                
                # Извлекаем детали занятия
                lesson = extract_lesson_details(cell)
                if not lesson:
                    continue  # Пропускаем пустые ячейки
                
                # Проверяем, есть ли информация о предмете
                if 'subject' not in lesson or not lesson['subject']:
                    continue
                
                # Определяем иконку в зависимости от типа занятия
                lesson_type = lesson.get('lesson_type', '')
                icon = colors.get(lesson_type, colors['default'])
                
                # Добавляем информацию о занятии (используем HTML-теги вместо Markdown)
                subject = lesson.get('subject', '')
                
                result += f"⏰ <b>{time_slot}</b>\n"
                result += f"{icon} <b>{subject}</b>"
                if lesson_type:
                    result += f" ({lesson_type})"
                result += "\n"
                
                # Добавляем информацию о преподавателе
                teacher = lesson.get('teacher', '')
                if teacher:
                    result += f"👨‍🏫 {teacher}\n"
                
                # Добавляем информацию об аудитории
                classroom = lesson.get('classroom', '')
                if classroom:
                    result += f"🏛 Ауд: {classroom}\n"
                
                # Добавляем информацию о формате (онлайн)
                if lesson.get('is_online', False):
                    result += f"💻 <b>ОНЛАЙН</b>\n"
                
                # Добавляем ссылку на собрание, если есть
                if lesson.get('link'):
                    # Очищаем URL для безопасного использования в HTML
                    clean_url = sanitize_url_for_html(lesson['link'])
                    # Используем HTML-тег для создания кликабельного текста
                    result += f'🔗 <a href="{clean_url}">Вход на лекцию</a>\n'
                
                result += "\n"
        
        return result
    except Exception as e:
        logging.error(f"Произошла ошибка при парсинге: {str(e)}")
        return f"Произошла ошибка при парсинге: {str(e)}"

# Команда /schedule
async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = parse_schedule()
    # Используем HTML вместо MARKDOWN для корректного отображения ссылок
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)

# Функция для парсинга расписания с сайта по заданным датам
async def rasspisan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Ожидается, что команда выглядит так: /rasspisan 02.03.2025 - 05.03.2025
    args = context.args
    if len(args) != 3 or args[1] != '-':
        await update.message.reply_text("Использование: /rasspisan <начальная дата> - <конечная дата>\nПример: /rasspisan 02.03.2025 - 05.03.2025")
        return

    date_from = args[0]
    date_end = args[2]
    
    # Сообщаем пользователю о начале загрузки
    progress_message = await update.message.reply_text("Загрузка расписания...")

    url = "http://inet.ibi.spb.ru/raspisan/rasp.php"

    headers = {
        "accept": "*/*",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/x-www-form-urlencoded",
        "proxy-connection": "keep-alive"
    }

    # Используем GROUP_ID из конфигурационного файла
    body = f"rtype=1&group={GROUP_ID}&exam=0&datafrom={date_from}&dataend={date_end}&formo=0&allp=0&hour=0&tuttabl=0"

    try:
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status()

        # Сохраняем ответ в файл для возможности локального просмотра
        with open('templeraspisan.html', 'w', encoding='utf-8') as file:
            file.write(response.text)
            
        # Создаем копию ответа для отладки в server_response.html
        with open('server_response.html', 'w', encoding='utf-8') as file:
            file.write(response.text)

        # После сохранения файла, используем функцию parse_schedule 
        # для получения отформатированного расписания
        result = parse_schedule()
        
        # Удаляем сообщение о загрузке
        await progress_message.delete()

        # Если сообщение слишком длинное, разделяем его
        if len(result) > 4096:
            chunks = [result[i:i+4096] for i in range(0, len(result), 4096)]
            for chunk in chunks:
                # Используем HTML вместо MARKDOWN для корректного отображения ссылок
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
        else:
            # Используем HTML вместо MARKDOWN для корректного отображения ссылок
            await update.message.reply_text(result, parse_mode=ParseMode.HTML)
            
    except Exception as e:
        logging.error(f"Ошибка при получении расписания с сайта: {str(e)}")
        # Удаляем сообщение о загрузке
        await progress_message.delete()
        await update.message.reply_text(f"Ошибка при получении расписания: {str(e)}")

# Основная функция для запуска бота
async def main():
    # Настраиваем более подробное логирование
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Используем токен из конфигурационного файла
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler('schedule', schedule))
    application.add_handler(CommandHandler('rasspisan', rasspisan))
    
    # Запускаем бота
    await application.run_polling()

# Изменение способа запуска для предотвращения ошибок с event loop
if __name__ == '__main__':
    try:
        # Пытаемся запустить с использованием asyncio.run
        asyncio.run(main())
    except RuntimeError as e:
        # Если получаем ошибку о том, что цикл уже запущен,
        # используем другой подход
        if "This event loop is already running" in str(e):
            # Получаем текущий event loop и запускаем в нем наше приложение
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            # Убедимся, что цикл запущен
            if not loop.is_running():
                loop.run_forever()
        else:
            # Если другая ошибка - пробрасываем её дальше
            raise 