"""Кодирование идентификаторов для коротких ссылок на рецепты."""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)


def encode_base62(number):
    """Кодирует положительный идентификатор в строку Base62."""

    if number < 1:
        raise ValueError("Only positive identifiers can be encoded")
    result = []
    while number:
        number, remainder = divmod(number, BASE)
        result.append(ALPHABET[remainder])
    return "".join(reversed(result))


def decode_base62(value):
    """Преобразует корректный код Base62 обратно в идентификатор."""

    if not value:
        raise ValueError("An empty short code is invalid")
    number = 0
    for char in value:
        try:
            digit = ALPHABET.index(char)
        except ValueError as error:
            raise ValueError("Invalid short code") from error
        number = number * BASE + digit
    if number < 1:
        raise ValueError("Invalid short code")
    return number
