import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

logging.basicConfig(
    handlers=[
        logging.FileHandler(
            filename='program.log',
            encoding='utf-8',
            mode='a+'
        ),
        logging.StreamHandler(sys.stdout)
    ],
    level=logging.DEBUG,
    format='%(asctime)s, %(funcName)s, %(levelname)s, %(message)s, %(name)s'
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
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
    logging.info('Токены в порядке')
    return True


def send_message(bot, message):
    """Отправляем сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено в чат {TELEGRAM_CHAT_ID}')
    except Exception as error:
        logging.error(
            f'Сообщение не удалось отправить: {error}', exc_info=True
        )
        raise Exception(
            f'Сообщение не удалось отправить: {error}', exc_info=True
        )


def get_api_answer(timestamp):
    """Запрашиваем информация из API."""
    try:
        response = requests.get(
            ENDPOINT,
            headers={'Authorization': f'OAuth {PRACTICUM_TOKEN}'},
            params={'from_date': timestamp}
        )
    except Exception as error:
        logging.error(f'Ошибка получения данных API: {error}')
        raise Exception(f'Ошибка получения данных API: {error}')
    if response.status_code != HTTPStatus.OK:
        logging.error('Эндпоинт недоступен')
        raise Exception('Эндпоинт недоступен')

    response = response.json()
    return response


def check_response(response):
    """Проверяем ответ API."""
    if type(response) is not dict:
        raise TypeError('Ответ API не является словрем')
    try:
        response['homeworks']
    except Exception:
        raise Exception('В API нет ключа homeworks')
    if type(response['homeworks']) is not list:
        raise TypeError('Homeworks не является списком')
    try:
        homework = response['homeworks'][0]
    except Exception:
        homework = False
        logging.debug('Нет домашних заданий')
    return homework


def parse_status(homework):
    """Формируем сообщение о статусе домашней работы."""
    try:
        homework_name = homework['homework_name']
    except Exception:
        logging.ERROR('Пустое имя домашней работы')
        raise Exception('Пустое имя домашней работы')
    try:
        verdict = HOMEWORK_VERDICTS[homework['status']]
    except Exception:
        logging.ERROR('Неверный статус работы')
        raise Exception('Неверный статус работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical('Отсутствует обязательная переменная окружения')
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    ERROR_MESSAGE = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
                timestamp = response['current_date']

        except Exception as error:
            if str(error) != ERROR_MESSAGE:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                ERROR_MESSAGE = str(error)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
