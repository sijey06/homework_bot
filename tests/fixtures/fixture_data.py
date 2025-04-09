import random
import string
from datetime import datetime

import pytest


@pytest.fixture
def random_timestamp():
    left_ts = 1000198000
    right_ts = 1000198991
    return random.randint(left_ts, right_ts)


@pytest.fixture
def current_timestamp():
    return int(datetime.now().timestamp())


@pytest.fixture
def homework_module():
    import homework
    return homework


@pytest.fixture
def random_message():
    def random_string(string_length=15):
        letters = string.ascii_letters
        return ''.join(random.choice(letters) for _ in range(string_length))
    return random_string()


@pytest.fixture
def data_with_new_hw_status(random_timestamp):
    return {
        'homeworks': [
            {
                'id': 777777777,
                'homework_name': f'hw{random.randint(10, 1000)}.zip',
                'status': 'approved',
                'reviewer_comment': 'Принято!',
                'date_updated': '2021-04-11T10:31:09Z',
                'lesson_name': 'Проект спринта: Деплой бота'
            }
        ],
        'current_date': random_timestamp
    }
