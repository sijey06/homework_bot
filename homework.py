import os
import time
import logging
import requests

from telebot import TeleBot
from dotenv import load_dotenv


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(filename='bot1.log', mode='a', encoding='utf-8')  # Указываем кодировку
    ]
)


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


def check_tokens():
    """Проверяет наличие необходимых токенов."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logging.critical("Отсутствуют необходимые токены! Проверьте переменные окружения.")
        raise ValueError("Отсутствуют необходимые токены!")


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f"Бот успешно отправил сообщение: '{message}'.")
    except Exception as e:
        logging.error(f"Произошла ошибка при отправке сообщения: {e}")


def get_api_answer(timestamp):
    """Делает запрос к API."""
    params = {"from_date": timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            raise Exception(
                f"Ошибка при запросе к API Practicum: {response.status_code}"
            )
        return response.json()
    except requests.RequestException as e:
        raise ConnectionError(f"Ошибка соединения с API Practicum: {e}")


def check_response(response):
    """Проверка ответа от API."""
    if not isinstance(response, dict):
        logging.error("Ответ от API не является словарем.")
        raise TypeError("Ответ от API не является словарем.")

    if "error" in response:
        logging.error(f"Ошибка в ответе API: {response['error']}.")
        raise Exception(f"Ошибка в ответе API: {response['error']}")

    if "homeworks" not in response or "current_date" not in response:
        logging.error("Не найдены ключи 'homeworks' или 'current_date'.")
        raise KeyError("Не найдены ключи 'homeworks' или 'current_date'.")

    if not isinstance(response["homeworks"], list):
        logging.error("Данные под ключом 'homeworks' не являются списком.")
        raise TypeError("Данные под ключом 'homeworks' не являются списком.")

    if len(response["homeworks"]) == 0:
        logging.debug("В ответе API отсутствуют новые статусы.")
        return None

    return response["homeworks"]


def parse_status(homework):
    """Извлечение статуса работы из ответа API."""
    if "homework_name" not in homework:
        logging.error("Ключ 'homework_name' отсутствует в ответе API.")
        raise KeyError("Ключ 'homework_name' отсутствует в ответе API.")

    homework_name = homework["homework_name"]
    if "status" not in homework:
        logging.error("Ключ 'status' отсутствует в ответе API.")
        raise KeyError("Ключ 'status' отсутствует в ответе API.")

    status = homework["status"]
    if status not in HOMEWORK_VERDICTS:
        logging.error(f"Недокументированный статус домашней работы: {status}.")
        raise ValueError(f"Недокументированный статус домашней работы: {status}.")

    verdict = HOMEWORK_VERDICTS.get(status, "Статус неизвестен.")

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

            timestamp = api_answer.get("current_date", timestamp)

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            send_message(bot, message)
            logging.error(message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
