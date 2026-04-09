#!/usr/bin/env python3
"""Выводит текущие дату и время."""

from datetime import datetime

if __name__ == "__main__":
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
