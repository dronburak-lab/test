#!/usr/bin/env python3
"""Print the current local date and time."""

from __future__ import annotations

from datetime import datetime


def main() -> None:
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
