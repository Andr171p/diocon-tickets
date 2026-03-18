import argparse
import asyncio
import logging
import sys

from .commands import create_first_admin, init_s3_storage


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI утилиты для diocon-tickets")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Команда `create-first-admin`
    subparsers.add_parser(
        "create-first-admin", help="Создать первого администратора"
    )
    # Команда `init-s3-storage`
    subparsers.add_parser("init-s3-storage", help="Инициализация S3 хранилища")

    args = parser.parse_args()

    if args.command == "create-first-admin":
        asyncio.run(create_first_admin())
    elif args.command == "init-s3-storage":
        asyncio.run(init_s3_storage())
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
