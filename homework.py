import logging
import os
import sys
import time
from http import HTTPStatus
import exceptions

import requests
import telegram
from dotenv import load_dotenv

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
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляем сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено в чат {TELEGRAM_CHAT_ID}')
    except telegram.error.TelegramError as error:
        logging.error(
            f'Сообщение не удалось отправить: {error}',
            exc_info=True
        )
        raise exceptions.SendMessageError from error(
            f'Сообщение не удалось отправить: {error}'
        )


def get_api_answer(timestamp):
    """Запрашиваем информация из API."""
    try:
        response = requests.get(
            ENDPOINT,
            headers={'Authorization': f'OAuth {PRACTICUM_TOKEN}'},
            params={'from_date': timestamp}
        )
    except requests.exceptions.RequestException as error:
        raise exceptions.GetApiError(f'Ошибка получения данных API: {error}')

    if response.status_code != HTTPStatus.OK:
        raise requests.HTTPError('Эндпоинт недоступен')

    try:
        return response.json()
    except ValueError as error:
        raise exceptions.GetApiError(
            f'Ошибка преобразования данных API в json: {error}'
        )


def check_response(response):
    """Проверяем ответ API."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словрем')
    try:
        response['homeworks']
    except KeyError:
        raise KeyError('В API нет ключа homeworks')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Homeworks не является списком')
    try:
        homework = response['homeworks'][0]
    except IndexError:
        homework = False
        logging.debug('Нет домашних заданий')
    return homework


def parse_status(homework):
    """Формируем сообщение о статусе домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        raise KeyError('Пустое имя домашней работы')
    try:
        verdict = HOMEWORK_VERDICTS[homework['status']]
    except KeyError:
        raise KeyError('Неверный статус работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует обязательная переменная окружения')
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    error_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
                timestamp = response['current_date']

        except Exception as error:
            logging.exception(error)
            if str(error) != error_message:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                error_message = str(error)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        handlers=[
            logging.FileHandler(
                filename='program.log',
                encoding='utf-8',
                mode='w'
            ),
            logging.StreamHandler(sys.stdout)
        ],
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
    )

    main()
