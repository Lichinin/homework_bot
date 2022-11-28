import os

import requests
import time
import logging

import telegram

from dotenv import load_dotenv

logging.basicConfig(
    handlers=[logging.FileHandler(
        filename='program.log',
        encoding='utf-8',
        mode='w')
    ],
    level=logging.DEBUG,
    format='%(asctime)s, %(funcName)s, %(levelname)s, %(message)s, %(name)s'
)

# logging.debug('Бот отправил сообщение')
# logging.info('Сообщение отправлено')
# logging.warning('Большая нагрузка!')
# logging.error('Сбой в работе программы')
# logging.critical('Всё упало! Зовите админа!1!111')

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 100
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем токены."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return False
    return True


def send_message(bot, message):
    """Отправляем сообщение в Telegram"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено в чат {TELEGRAM_CHAT_ID}')
    except Exception as error:
        logging.error(f'Сообщение не удалось отправить: {error}', exc_info=True)


def get_api_answer(timestamp):
    """Запрашиваем информация из API"""
    try:
        response = requests.get(
            ENDPOINT,
            headers={'Authorization': f'OAuth {PRACTICUM_TOKEN}'},
            params={'from_date': timestamp}
        )
    except Exception as error:
        logging.error(f'Ошибка получения данных API: {error}')
    if response.status_code != 200:
        logging.error('Эндпоинт недоступен')
        raise Exception('Эндпоинт недоступен')

    response = response.json()
    return response


def check_response(response):
    """Проверяем ответ API"""
    if type(response['homeworks']) is not list:
        raise TypeError('Вернулся не словарь')
    try:
        response.get('homeworks')
    except TypeError as error:
        logging.error(f'Нет homework: {error}')
    if 'homeworks' not in response:
        raise TypeError('Нет homeworks')
    try:
        homework = response['homeworks'][0]
    except IndexError:
        homework = False
        logging.debug('Нет домашек')
    return homework


def parse_status(homework):
    """Формируем сообщение о статусе работы."""
    try:
        homework_name = homework['homework_name']
    except Exception:
        logging.ERROR('Пустое имя домашней работы')
    try:
        verdict = HOMEWORK_VERDICTS[homework['status']]
    except Exception:
        logging.ERROR('Неверный статус работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical('Отсутствует обязательная переменная окружения')
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - 1814450

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            print(homework)
            if homework:
                cached_message = ''
                message = parse_status(homework)
                if cached_message != message:
                    send_message(bot, message)
            timestamp = response['current_date']

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
