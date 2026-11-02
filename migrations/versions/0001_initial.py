"""Baseline: полная схема «Города+».

Revision ID: 0001
Revises:
Create Date: 2025-01-01

Стратегия (см. docs/decisions.md и скилл sqlalchemy-async):
единственная «настоящая» ревизия — 0001, она описывает всю схему ровно так,
как её объявляют модели из app.models. Ревизии 0002–0006 — заглушки, которые
резервируют цепочку для будущих изменений. Поэтому 0001 нельзя править после
применения: любые изменения схемы идут новой ревизией.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

NOW = sa.func.now()


def _pk() -> sa.Column:
    """IdMixin: BIGSERIAL в Postgres, INTEGER в SQLite (алиас rowid)."""
    return sa.Column(
        "id",
        sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
        primary_key=True,
        autoincrement=True,
    )


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False
    )


def _updated_at() -> sa.Column:
    return sa.Column(
        "updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False
    )


def upgrade() -> None:
    # ------------------------------- users -------------------------------
    op.create_table(
        "users",
        _pk(),
        sa.Column("tg_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("language", sa.String(2), nullable=False, server_default="ru"),
        sa.Column("show_weather", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_photo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locale", sa.String(2), nullable=False, server_default="ru"),
        sa.Column("first_name", sa.String(64), nullable=True),
        sa.Column("difficulty", sa.String(10), nullable=False, server_default="easy"),
        sa.Column("notify", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
    )
    op.create_index("ix_users_tg_id", "users", ["tg_id"], unique=True)

    # ------------------------------ profiles -----------------------------
    op.create_table(
        "profiles",
        _pk(),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "users.id", ondelete="CASCADE", name="fk_profiles_user_id_users"
            ),
            nullable=False,
        ),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_won", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cities_named", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("favorite_letter", sa.String(2), nullable=True),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cities_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("geo_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_played_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint("user_id", name="uq_profiles_user_id"),
    )

    # ------------------------------- cities ------------------------------
    op.create_table(
        "cities",
        _pk(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("normalized_name", sa.String(120), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("country_name", sa.String(100), nullable=False),
        sa.Column("region", sa.String(120), nullable=True),
        sa.Column("population", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        _created_at(),
        _updated_at(),
    )
    op.create_index("ix_cities_normalized_name", "cities", ["normalized_name"], unique=True)
    op.create_index("ix_cities_country_code", "cities", ["country_code"])

    # -------------------------------- games ------------------------------
    op.create_table(
        "games",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_games_user_id_users"),
            nullable=False,
        ),
        sa.Column(
            "game_type",
            sa.Enum("cities", "geoguessr", name="game_type"),
            nullable=False,
            server_default="cities",
        ),
        sa.Column(
            "status",
            sa.Enum("active", "finished", "abandoned", "timeout", name="game_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("moves_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("difficulty", sa.String(10), nullable=False, server_default="easy"),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("won", sa.Boolean(), nullable=False, server_default=sa.false()),
        _created_at(),
        _updated_at(),
    )
    op.create_index("ix_games_user_id", "games", ["user_id"])
    op.create_index("ix_games_user_status", "games", ["user_id", "status"])

    # ------------------------------ game_moves ---------------------------
    op.create_table(
        "game_moves",
        _pk(),
        sa.Column(
            "game_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey(
                "games.id", ondelete="CASCADE", name="fk_game_moves_game_id_games"
            ),
            nullable=False,
        ),
        sa.Column("city_name", sa.String(120), nullable=False),
        sa.Column("normalized_name", sa.String(120), nullable=False),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("move_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_user", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=True),
        _created_at(),
        sa.UniqueConstraint("game_id", "normalized_name", name="uq_game_city"),
    )
    op.create_index("ix_game_moves_game_id", "game_moves", ["game_id"])
    op.create_index("ix_game_moves_move_number", "game_moves", ["move_number"])

    # ---------------------------- geo_locations --------------------------
    op.create_table(
        "geo_locations",
        _pk(),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("thumb_url", sa.String(500), nullable=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("difficulty", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("source", sa.String(20), nullable=False),
        _created_at(),
        _updated_at(),
    )
    op.create_index(
        "ix_geo_locations_source_country", "geo_locations", ["source", "country_code"]
    )

    # ---------------------------- achievements ---------------------------
    op.create_table(
        "achievements",
        _pk(),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(10), nullable=False),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint("code", name="uq_achievements_code"),
    )

    # --------------------------- user_achievements -----------------------
    op.create_table(
        "user_achievements",
        _pk(),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "users.id", ondelete="CASCADE", name="fk_user_achievements_user_id_users"
            ),
            nullable=False,
        ),
        sa.Column(
            "achievement_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "achievements.id",
                ondelete="CASCADE",
                name="fk_user_achievements_achievement_id_achievements",
            ),
            nullable=False,
        ),
        sa.Column(
            "unlocked_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False
        ),
        sa.UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )
    op.create_index("ix_user_achievements_user_id", "user_achievements", ["user_id"])
    op.create_index(
        "ix_user_achievements_achievement_id", "user_achievements", ["achievement_id"]
    )

    # ------------------------------ api_cache ----------------------------
    op.create_table(
        "api_cache",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("value", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        _created_at(),
    )
    op.create_index("ix_api_cache_provider", "api_cache", ["provider"])
    op.create_index("ix_api_cache_expires_at", "api_cache", ["expires_at"])

    # --------------------------- user_used_cities ------------------------
    op.create_table(
        "user_used_cities",
        _pk(),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "users.id", ondelete="CASCADE", name="fk_user_used_cities_user_id_users"
            ),
            nullable=False,
        ),
        sa.Column("city_norm", sa.String(120), nullable=False),
        sa.Column(
            "game_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey(
                "games.id", ondelete="CASCADE", name="fk_user_used_cities_game_id_games"
            ),
            nullable=True,
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.UniqueConstraint("user_id", "city_norm", "game_id", name="uq_user_used_city"),
    )
    op.create_index("ix_user_used_cities_user_id", "user_used_cities", ["user_id"])
    op.create_index("ix_user_used_cities_city_norm", "user_used_cities", ["city_norm"])

    # --------------------------- daily_challenges ------------------------
    op.create_table(
        "daily_challenges",
        _pk(),
        sa.Column("challenge_date", sa.Date(), nullable=False),
        sa.Column("city_name", sa.String(120), nullable=False),
        sa.Column("hint", sa.String(255), nullable=False),
        sa.Column("reward_score", sa.Integer(), nullable=False, server_default="50"),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint("challenge_date", name="uq_daily_challenge_date"),
    )

    # ---------------------------- notifications --------------------------
    op.create_table(
        "notifications",
        _pk(),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "users.id", ondelete="CASCADE", name="fk_notifications_user_id_users"
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        _created_at(),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    # Порядок обратный: сначала зависимые таблицы, потом родительские.
    op.drop_table("notifications")
    op.drop_table("daily_challenges")
    op.drop_table("user_used_cities")
    op.drop_table("api_cache")
    op.drop_table("user_achievements")
    op.drop_table("achievements")
    op.drop_table("geo_locations")
    op.drop_table("game_moves")
    op.drop_table("games")
    op.drop_table("cities")
    op.drop_table("profiles")
    op.drop_table("users")

    # В Postgres CREATE TABLE с sa.Enum создаёт отдельные типы — убираем их.
    if op.get_bind().dialect.name == "postgresql":
        for type_name in ("game_type", "game_status"):
            op.execute(sa.text(f'DROP TYPE IF EXISTS {type_name}'))
