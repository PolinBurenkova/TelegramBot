"""Error handler."""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

log = logging.getLogger("errors")
router = Router()


@router.error()
async def on_error(event: ErrorEvent) -> None:
    log.exception("Unhandled exception: %s", event.exception)
    try:
        update = event.update
        if update.message:
            await update.message.answer("⚠️ Что-то пошло не так.")
        elif update.callback_query:
            await update.callback_query.answer("⚠️ Ошибка", show_alert=False)
    except Exception:
        pass