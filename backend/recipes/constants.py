"""Ограничения и настройки моделей рецептов Foodgram."""

from string import ascii_letters, digits

TAG_NAME_MAX_LENGTH = 32
TAG_SLUG_MAX_LENGTH = 32
INGREDIENT_NAME_MAX_LENGTH = 128
MEASUREMENT_UNIT_MAX_LENGTH = 64
RECIPE_NAME_MAX_LENGTH = 256
MIN_COOKING_TIME = 1
MAX_COOKING_TIME = 32000
MIN_INGREDIENT_AMOUNT = 1
MAX_INGREDIENT_AMOUNT = 32000
SHORT_CODE_LENGTH = 8
SHORT_CODE_ALPHABET = digits + ascii_letters
MAX_IMAGE_SIZE = 8 * 1024 * 1024
PHOTO_WIDTH = 1400
IMAGE_DOWNLOAD_TIMEOUT = 30
PHOTO_URL_TEMPLATE = (
    "https://unsplash.com/photos/{photo_id}/download?force=true&"
    "w={width}"
)
