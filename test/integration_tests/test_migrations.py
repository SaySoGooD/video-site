"""The migration and the ORM models must describe the same schema.

Two things define the database — ``Base.metadata`` and the Alembic scripts —
and nothing stops them drifting apart except a check like this one. A drift is
invisible in the test suite (which builds tables from the models) and shows up
in production (which builds them from the migrations).

The migration runs against a throwaway SQLite file: the point is the shape of
the schema, not the dialect.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect

# Importing the models registers them on the metadata.
import users_service.adapter.database.orm_models  # noqa: F401
from users_service.adapter.database.base import Base

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def migrated_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Apply every migration to an empty SQLite database; return its URL."""
    database = tmp_path / "migrated.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database}")

    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    command.upgrade(config, "head")

    return f"sqlite:///{database}"


class TestMigrations:
    def test_creates_every_table_the_models_declare(
        self, migrated_url: str
    ) -> None:
        engine = create_engine(migrated_url)
        try:
            tables = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()

        assert set(Base.metadata.tables) <= tables

    def test_creates_every_column_the_models_declare(
        self, migrated_url: str
    ) -> None:
        engine = create_engine(migrated_url)
        try:
            inspector = inspect(engine)
            missing: dict[str, set[str]] = {}
            for name, table in Base.metadata.tables.items():
                actual = {c["name"] for c in inspector.get_columns(name)}
                expected = {c.name for c in table.columns}
                if expected - actual:
                    missing[name] = expected - actual
        finally:
            engine.dispose()

        assert not missing, f"columns missing from the migration: {missing}"

    def test_downgrade_removes_everything(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        database = tmp_path / "reversible.sqlite"
        monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database}")
        config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))

        command.upgrade(config, "head")
        command.downgrade(config, "base")

        engine = create_engine(f"sqlite:///{database}")
        try:
            remaining = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()

        # Alembic keeps its own bookkeeping table; nothing of ours survives.
        assert remaining <= {"alembic_version"}
