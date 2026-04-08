import re

WORDS_COUNT = 2
MIN_KEY_LENGTH = 2
MAX_KEY_LENGTH = 10


def generate_project_key(name: str, default: str = "PRJ") -> str:
    """
    Генерирует предложение ключа проекта на основе его имени.

    Алгоритм:
     1. Оставляем только буквы (латиница, кириллица) и пробелы.
     2. Приводим к верхнему регистру.
     3. Берём первые буквы от первых 1-3 слов, если слов несколько.
     4. Если получилось слишком коротко (<2) – берём первые 2-4 буквы первого слова.
     5. Обрезаем до 10 символов.
     6. Если результат всё ещё пуст – возвращаем default.
    """

    if not name:
        return default

    # 1. Только буквы и пробелы (удаление цифр, знаков, эмодзи)
    cleaned = re.sub(r"[^A-Za-zА-Яа-яЁё\s]", "", name)
    cleaned = cleaned.upper()

    # 2. Разбиение на слова
    words = cleaned.split()
    if not words:
        return default

    # 3. Генерация ключа
    key = "".join(word[0] for word in words[:3]) if len(words) > WORDS_COUNT else words[0][:4]

    # 4. Обеспечение минимальной длины (2 символа)
    if len(key) < MIN_KEY_LENGTH:
        key = (key + key).ljust(2, "X")[:2]  # "А" -> "АА" или "АX"

    # 5. Обрезание до максимальной длины (10 символов)
    key = key[:10]

    # 6. Дополнительная проверка, что первый символ является буквой
    if not key[0].isalpha():
        key = "P" + key[1:] if len(key) > 1 else "PR"

    return key
