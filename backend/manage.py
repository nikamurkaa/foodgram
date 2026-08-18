#!/usr/bin/env python
"""Утилита командной строки для управления проектом Django."""

import os
import sys


def main():
    """Передаёт аргументы командной строки системе управления Django."""

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodgram.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
