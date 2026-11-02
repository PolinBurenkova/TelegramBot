---
name: aiogram-bot
description: Build the Telegram layer with aiogram 3.x the way this repo expects — router hierarchy, thin handlers that delegate to services, FSM with the right storage, middlewares for session/config/throttling, callback data factories, keyboards, and safe error handling with graceful shutdown.
whenToUse: Adding or editing handlers, routers, filters, keyboards, FSM states, middlewares, bot startup, webhook/polling setup, or notifier services.
---

# aiogram 3.x — house rules

## Composition

- `run.py` builds `Bot`, `Dispatcher`, includes routers, registers middlewares and the error handler, then starts polling or the webhook, and shuts down gracefully.
- Router tree per feature: `app/bot/routers.py` aggregates feature routers from `app/handlers/` in a fixed order — fallback/echo routers last.
- Handler modules export `router = Router(name="<feature>")` and nothing else global.
- `Dispatcher` storage: `MemoryStorage` for local/dev only, `RedisStorage` in compose/prod (Redis is part of the stack).
- Never put `Dispatcher`/`Bot` construction inside a handler module; no module-level side effects on import.

## Thin handlers

A handler does exactly four things: get the update, call a service, render the answer, handle the domain error. No SQL, no HTTP, no chain logic.

```python
@router.message(Command("start"))
async def cmd_start(message: Message, user_service: UserService) -> None:
    profile = await user_service.register_or_get(message.from_user.id)
    await message.answer(texts.greeting(profile.city))
```

- Extract domain work into `app/services/`; handlers stay ≤ ~20 lines.
- Put hidden values in `callback_data` via `CallbackData` factory classes (typed, packed with `pack`), never raw `"act:1"` strings.
- Validate everything from `message.text` before passing it to a service; user input is untrusted.

## FSM

- States live in `app/fsm/*_states.py` as `class GuessStates(StatesGroup): waiting_city = State()`.
- Set/clear state around the flow; always clear on completion and on cancel, and on `/start` reset.
- Do not stash domain objects in FSM data; store IDs and let services hydrate.
- Long flows get an explicit cancel button and a timeout policy; document the timeout in the handler docstring.

## Middlewares and filters

- Session middleware (DB) opens the `AsyncSession` per update and closes it in `finally`; it injects the session/repos into `data`.
- Config/settings come from `app/config.py` and are injected once, not re-read per handler.
- Throttling/anti-flood middleware in `app/middlewares/` for guess input; keep the bucket in Redis, not in-process, when running multiple replicas.
- Custom filters (`app/filters/`) implement `__call__` returning `bool | dict` with full annotations; no hidden side effects inside filters.
- Admin checks by immutable user id from settings, not by username (usernames change).

## Keyboards

- Markup builders in `app/keyboards/` return `ReplyKeyboardMarkup` / `InlineKeyboardMarkup`; handlers never build markup inline.
- Callback buttons carry typed `CallbackData`; reply buttons carry `KeyboardButton(text=...)` matching a text constant from the locales module.
- Buttons are localized consistently with the reply texts; no mixed languages.

## Messages, texts, media

- Send user-facing text from one source per string (code constant or `app/utils/locales/ru.json`), with `.format`/f-string placeholders, not concatenation.
- Escape user-supplied content with `html.escape` when using `parse_mode="HTML"`.
- Photos from provider URLs: send via URL first, fall back to download+buffer when Telegram rejects the URL; always supply a caption fallback.
- Long text is split before hitting Telegram's 4096-character limit; helper lives in `app/utils/`.

## Errors and shutdown

- Register `dp.errors` handler: log with update context, answer the user with a neutral message, never leak tracebacks to chat.
- Convert `TelegramAPIError`/retry-after into service-level failure; `TelegramRetryAfter` must be honored with sleep, not ignored.
- Graceful shutdown: cancel pending tasks, close the bot session, dispose the engine, close Redis in `finally` / lifespan.
- Polling conflicts (`409 Conflict`) mean a second instance is running: fail loudly, do not silently retry forever.
- Correlate logs with `update.update_id` and `user_id` for traceability.
