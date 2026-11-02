# Внешние API и каскад провайдеров

Документ описывает фактическое состояние слоя `app/services/external/` и
`app/utils/provider_chain.py` в этом репозитории. Всё, что ниже, проверено
чтением кода; сетевые вызовы в этой среде не выполнялись (см. «Статус
проверки» в `docs/decisions.md`).

## Слои

- `app/services/external/base.py` — контракт `BaseProvider`:
  атрибуты `name`, `category`, `requires_key`, `base_url`, `timeout`;
  свойство `is_configured` (не метод) = `not requires_key or bool(api_key)`;
  `call(method_name, ...)` делегирует в `fetch(...)`;
  `get_json(...)` бросает `ExternalAPIError` на сетевую/HTTP≥400/битую
  JSON-выгрузку и `RateLimitError` на 429.
  Там же хелпер `provider_key(*names)`: ищет ключ в окружении по конвенции
  `<NAME>_API_KEY` → `<NAME>_TOKEN` → `<NAME>_KEY` → `<NAME>_USERNAME`, чтобы
  «длинный хвост» провайдеров не раздувал `Settings` на десятки полей.
- `app/services/external/registry.py` — `ExternalRegistry` и `build_chain()`:
  собирают `ProviderChain` из `settings.provider_order`, кэшируют цепочки,
  пропускают имена без класса-провайдера.
- `app/utils/provider_chain.py` — последовательный обход провайдеров,
  `app/utils/quota_manager.py` (квоты), `app/utils/circuit_breaker.py`
  (предохранитель), `app/utils/cache.py` (Redis/`MemoryCache`).

## Контракт каскада

```python
result = await chain.call("fetch", query=...)   # метод ищется через getattr
value = result.value                            # ChainResult.value
result.provider_used, result.latency_ms, result.attempts  # AttemptLog
```

- Порядок обхода: `is_configured` → квота → circuit breaker → вызов.
  Ненастроенные провайдеры пропускаются с `reason="not_configured"` и не
  расходуют квоту.
- `ChainResult(value, provider_used, latency_ms, attempts)`; каждый
  `AttemptLog(provider, outcome="success"|"skipped"|"failed", reason,
  latency_ms)`.
- Если не сработал никто — `app.exceptions.AllProvidersFailedError`
  (историческое имя `AllProvidersFailed` оставлено алиасом в
  `app/exceptions.py`). Сообщение пользователю по умолчанию:
  `«Сервис временно недоступен, но игра продолжается.»`; детали уходят в
  лог без секретов.
- Квоты: предупреждение при 90% (`warning_threshold=0.9`), исчерпание —
  при 100%; периоды `second/minute/hour/day/week/month/unlimited`.
- Circuit breaker: `failure_threshold=5`, `recovery_timeout=60` с,
  состояния CLOSED/OPEN/HALF_OPEN; 4xx (кроме 429) ошибкой не считается.
- Кэш Redis по ключам `app/utils/cache_keys.py`; при недоступности Redis
  деградация в in-memory, а не падение.

## Реестр: 77 провайдеров, все имена цепочек разрешаются

`registry._PROVIDERS` отображает имя из `PROVIDER_CHAINS` в класс модуля
`app/services/external/<name>.py`. Все **75** имён, перечисленных в
`PROVIDER_CHAINS`, зарегистрированы (проверено сверкой множеств regex'ом по
обоим файлам: «missing in registry: нет»), поэтому ни одна цепочка больше не
пропускает имена «в пустоту». В этой итерации заполнены все модули-заглушки:
64 нулевых файла (включая агрегаторы `weather.py`, `maps.py`, `translate.py`)
и два модуля с `call() → None` (`pexels.py`, `timezone.py`).

Каскадов теперь **16** (по числу полей `provider_order_*` в `Settings`):
`cities` (9), `weather` (9), `photo` (6), `maps` (6), `wiki` (6),
`countries` (5), `panorama` (6), `translate` (5), `timezone` (3),
`exchange` (4), `holidays` (2), `air_quality` (3), `poi` (4), `nature` (4),
`media` (5), `ip_geo` (2).

## Работают без ключей

Провайдеры с `requires_key = False` — их каскад вызывает без регистрации:

| Цепочка | Провайдеры без ключа |
|---|---|
| cities | Nominatim, Photon, Open-Meteo Geocoding |
| weather | Open-Meteo |
| wiki | Wikipedia (ru, REST), Wikipedia RU (Action API), Wikidata, DBpedia, Wikivoyage |
| photo | Wikimedia Commons |
| maps | OSM Static Map |
| countries | REST Countries, REST Countries by name, FlagCDN, FlagsAPI, CountriesNow |
| panorama | KartaView, Panoramax, Yandex Panoramas (публичный endpoint) |
| translate | LibreTranslate (локальный сервис), MyMemory |
| timezone | WorldTimeAPI, Sunrise-Sunset |
| exchange | Frankfurter, ExchangeRate-API, exchangerate.host |
| holidays | Nager.Date |
| air_quality | Open-Meteo Air Quality |
| poi | Overpass API |
| nature | USGS Earthquakes, NASA APOD (`DEMO_KEY`), World Bank |
| media | — (все требуют ключ) |
| ip_geo | ipapi.co / ip-api.com |

LibreTranslate формально без ключа, но требует поднятого локального сервиса
(`docker compose --profile translate`, `Dockerfile.libretranslate`): без него
вызов уходит в сетевую ошибку, и каскад идёт дальше.

## Реализованы, но требуют ключа

HTTP-вызов и разбор ответа реализованы; без токена `is_configured = False`,
поэтому каскад их пропускает (`skipped/not_configured`) и не фейкает ответ:

`geonames` (бесплатный username), `opencage`, `positionstack`, `geoapify`,
`locationiq`, `mapbox_geocoding`, `openweather`, `weather_api`,
`visual_crossing`, `weatherstack`, `tomorrow_io`, `weatherbit`, `meteosource`,
`accuweather`, `pexels`, `unsplash`, `pixabay`, `flickr`, `yandex_maps`,
`mapbox`, `maptiler`, `thunderforest`, `stadia_maps`, `mapillary`,
`google_streetview`, `bing_streetside`, `google_translate`, `deepl`,
`yandex_translate`, `timezonedb`, `open_exchange_rates`, `holiday_api`,
`openaq`, `airvisual`, `foursquare`, `opentripmap`, `yelp`,
`carbon_interface`, `gnews`, `newsapi`, `guardian`, `youtube`, `vimeo`,
`abstract_api`.

Ключи читаются либо из `app/config.py` (`SecretStr`, например
`openweather_api_key`), либо через `provider_key(...)` из окружения; в коде
секретов нет. Наличие адаптера не означает, что реальный endpoint проверен —
сетевые прогоны не выполнялись.

## Модули-агрегаторы

`weather.py`, `maps.py`, `translate.py` не содержат классов-провайдеров: это
реэкспорты существующих реализаций и кортежи `WEATHER_PROVIDERS`,
`MAP_PROVIDERS`, `TRANSLATE_PROVIDERS` для тех, кому нужен весь набор
категории сразу. Импортируются только непустые модули, поэтому агрегаторы не
падают при частичной реализации.

## Цепочки и переопределения

`app/constants.py` (`PROVIDER_CHAINS`) объявляет **16** видов — 8 исходных
(`cities`, `weather`, `photo`, `maps`, `wiki`, `countries`, `panorama`,
`translate`) и 8 дополнительных (`timezone`, `exchange`, `holidays`,
`air_quality`, `poi`, `nature`, `media`, `ip_geo`), которые раньше были
объявлены только как поля `provider_order_*` и не влияли ни на что.

Все виды попадают в `settings.provider_order`; переменные
`PROVIDER_ORDER_<KIND>` (например `PROVIDER_ORDER_CITIES=nominatim,photon`)
переопределяют порядок через запятую. Порядок обхода равен порядку в списке:
первый настроенный провайдер, ответивший не-`None`, завершает каскад.

## Тесты

Внешние ответы подменяются JSON-моками `tests/mocks/*_responses.json` (по
кейсам `success`/`empty`/`error`), реальная сеть не используется: HTTP
перехватывается `httpx.MockTransport` через фикстуры `mock_http` /
`mock_http_factory` из `tests/conftest.py`. Провайдеры в тестах собираются
напрямую (`GeoNamesProvider(http=client)`) либо через
`ProviderChain([...])`/`build_chain(...)`.

Все тестовые функции `tests/external/` (6 модулей: geonames, weather, wiki,
panorama, maps, countries) помечены `pytest.mark.external`, поэтому джоб
`unit` в CI, запускаемый с `-m "not integration and not external and not slow"`,
их не подхватывает. Тесты не требуют ключей: для «ненастроенных» провайдеров
проверяется `is_configured == False` и пропуск каскадом, для цепочек —
фактический состав из `PROVIDER_CHAINS`, а пустая цепочка проверяется как
`AllProvidersFailedError` без попыток. Тесты не запускались — запуск
процессов в текущей среде запрещён, см. `docs/testing.md`.
