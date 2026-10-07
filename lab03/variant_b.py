"""Переиспользуемые ленивые этапы обработки данных."""

from functools import lru_cache, partial, reduce
from itertools import batched, chain, combinations, groupby, islice, product


def generate_numbers(start: int = 0, end: int = 100, step: int = 1):
    yield from range(start, end, step)


def filter_by_condition(data, condition):
    yield from filter(condition, data)


def filter_by_type(data, expected_type):
    yield from filter_by_condition(data, lambda item: isinstance(item, expected_type))


def transform_data(data, func):
    yield from map(func, data)


def batch_process(data, batch_size: int):
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
        raise ValueError("batch_size должен быть положительным целым числом")
    for batch in batched(data, batch_size):
        yield list(batch)


def aggregate(data, func):
    return func(data)


def create_pipeline(*steps):
    """Собирает этапы; последний может вернуть скалярный результат."""
    def pipeline(data):
        for step in steps:
            data = step(data)
        return data
    return pipeline


def sum_values(data):
    return reduce(lambda total, item: total + item, data, 0)


def average(data):
    total, count = reduce(
        lambda state, item: (state[0] + item, state[1] + 1),
        data, (0, 0),
    )
    if count == 0:
        raise ValueError("среднее пустой последовательности не определено")
    return total / count


def group_sorted(data, key):
    """Группирует соседние равные ключи; вход должен быть отсортирован."""
    for group_key, items in groupby(data, key):
        yield group_key, list(items)


def take(data, count: int):
    if count < 0:
        raise ValueError("count должен быть неотрицательным")
    yield from islice(data, count)


def concatenate(*iterables):
    yield from chain.from_iterable(iterables)


def pairs(data):
    yield from combinations(data, 2)


def cartesian(left, right):
    yield from product(left, right)


@lru_cache(maxsize=128)
def square(number):
    return number * number


def even_squares_pipeline():
    """Пример сборки этапов как готовая функция домашнего решения."""
    return create_pipeline(
        partial(filter_by_condition, condition=lambda number: number % 2 == 0),
        partial(transform_data, func=square),
        sum_values,
    )
