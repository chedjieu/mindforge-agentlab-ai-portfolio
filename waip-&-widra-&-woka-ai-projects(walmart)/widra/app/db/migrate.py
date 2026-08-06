"""Apply PostgreSQL schema migrations."""

from __future__ import annotations

from app.db import migrate


def main() -> None:
    migrate()
    print("WIDRA schema applied.")


if __name__ == "__main__":
    main()
