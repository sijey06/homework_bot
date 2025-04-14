import os
import time
import logging

import requests
from telebot.apihelper import ApiException
from telebot import TeleBot
from dotenv import load_dotenv

from exception import SendMessExcept


load_dotenv()


PRACTICUM_TOKEN = os.getenv('TOKEN_PRACT')
TELEGRAM_TOKEN = os.getenv('TOKEN_TG')
TELEGRAM_CHAT_ID = os.getenv('ID_CHAT')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

STATUS_OK = 200


def check_tokens():
    """Проверяет наличие необходимых токенов."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }

    missing_tokens = [
        token_name for token_name, token_value in tokens.items(
        ) if not token_value
    ]

    if missing_tokens:
        message = f"Отсутствуют следующие токены: {', '.join(missing_tokens)}"
        logging.critical(message)
        raise ValueError(message)


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот успешно отправил сообщение: "{message}".')
    except (requests.RequestException, ApiException) as err:
        raise SendMessExcept(f'Ошибка при отправке сообщения: {err}') from err


def get_api_answer(timestamp):
    """Делает запрос к API."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
    except requests.RequestException as e:
        raise ConnectionError(f'Ошибка соединения с API Practicum: {e}')

    if response.status_code != STATUS_OK:
        raise Exception(
            f'Ошибка при запросе к API Practicum: {response.status_code}'
        )

    return response.json()


def check_response(response):
    """Проверка ответа от API."""
    if not isinstance(response, dict):
        raise TypeError('Ответ от API не является словарем.')

    if 'error' in response:
        raise ValueError(f'Ошибка в ответе API: {response["error"]}')

    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError('Не найдены ключи "homeworks" или "current_date".')

    if not isinstance(response['homeworks'], list):
        raise TypeError('Данные под ключом "homeworks" не являются списком.')

    if not response['homeworks']:
        logging.debug('В ответе API отсутствуют новые статусы.')
        return None

    return response['homeworks']


def parse_status(homework):
    """Извлечение статуса работы из ответа API."""
    if 'homework_name' not in homework:
        raise KeyError('Ключ "homework_name" отсутствует в ответе API.')

    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError('Ключ "status" отсутствует в ответе API.')

    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус домашней работы: {status}.')

    verdict = HOMEWORK_VERDICTS.get(status, 'Статус неизвестен.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            api_answer = get_api_answer(timestamp)
            new_homeworks = check_response(api_answer)

            if new_homeworks is not None:
                for homework in new_homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
                    # try:
                    #     send_message(bot, message)
                    # except Exception as e:
                    #     logging.error(f'Ошибка при отправке сообщения: {e}')

            timestamp = api_answer.get('current_date', timestamp)

        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(filename='bot.log', mode='a', encoding='utf-8')
        ]
    )

    main()
