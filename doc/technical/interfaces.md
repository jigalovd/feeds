# Пользовательские и машинные интерфейсы

**Статус:** утверждено  
**Владелец фактов:** readiness, локальная панель и операционный CLI  
**Читать когда:** меняются setup, HTTP-интерфейс панели или команды CLI  
**Связанные документы:** [карта технической документации](README.md)

## Настройка и readiness

Панель сохраняет каждый валидированный раздел атомарно. Готовность вычисляется:

```text
telegram_ready
llm_ready
sources_discovered
policy_ready
target_tested
schedule_configured
scheduler_registered
```

При повторном открытии UI начинает с первого неготового шага. Отдельного persisted wizard-state, черновика и общего rollback нет.

Регистрация расписания разрешена только после готовности Telegram, LLM, источников, политики и цели.

## Локальная админ-панель

`feeds panel open` запускает скрытый дочерний процесс `feeds panel serve --internal`, ожидает readiness и открывает браузер. Сервер слушает только случайный порт `127.0.0.1`. Runtime descriptor содержит PID, port и время старта, но не bootstrap-токен. URL и токен не печатаются в stdout или лог.

Панель реализована на Starlette `1.x` и минимальном Uvicorn `0.51.x` без extra `standard`. Приложение создаётся фабрикой с явными routes и middleware; Pydantic-модели остаются границей HTTP DTO. Статические HTML, CSS и JavaScript поставляются локально из каталога `web`. Jinja, multipart, OpenAPI, WebSocket и framework-level DI не используются.

Uvicorn запускается внутри скрытого процесса через `uvicorn.Config` и `uvicorn.Server.serve()` со следующей фиксированной политикой:

```text
host = 127.0.0.1
port = 0
loop = asyncio
http = h11
ws = none
lifespan = on
workers = 1
reload = false
proxy_headers = false
access_log = false
server_header = false
```

Composition root передаёт приложению уже собранные публичные операции. Starlette не становится владельцем бизнес-зависимостей или отдельным DI-контейнером.

Для нового браузера создаётся 256-битный одноразовый токен со сроком две минуты:

```text
http://127.0.0.1:<port>/bootstrap#token=<token>
```

Fragment не отправляется HTTP-серверу. Локальный JavaScript передаёт токен одним POST-запросом, после чего выполняет `history.replaceState`. Успешно использованный или просроченный токен недействителен.

Сервер создаёт непрозрачную in-memory session и cookie с `HttpOnly`, `SameSite=Strict` и `Path=/`. Session не сохраняется на диск. Все изменяющие запросы требуют отдельный CSRF-токен, точный `Host`, точный `Origin` и ожидаемый content type.

CORS и OpenAPI UI отключены. Панель использует только локальные assets, запрещает inline scripts и отправляет CSP, `frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` и `Cache-Control: no-store`.

Telegram-код, пароль 2FA, Telegram `api_hash` и ключ LLM вводятся только в локальной форме и сразу передаются `SecretStore`. HTTP API никогда не возвращает существующее значение секрета: только `configured`, `missing` или `reauth_required`, а также операции replace/delete.

Несколько вкладок разделяют одну cookie-session. Каждая изменяющая операция использует актуальную readiness и `expected_revision`; устаревшая вкладка получает конфликт. Число вкладок не управляет временем жизни сервера.

Панель останавливается:

- явной командой UI;
- командой `feeds panel stop`;
- после 30 минут отсутствия пользовательской активности;
- безусловно через 8 часов.

Фоновый polling активностью не считается. Активная прикладная операция временно запрещает остановку; её поздний результат сохраняется, но после запроса закрытия новые операции не принимаются.

Если runtime descriptor указывает на живой процесс с совпадающим PID и временем старта, новый запуск возвращает `panel_already_running`. Устаревший descriptor удаляется. Отдельный IPC-механизм выдачи bootstrap-токена второй вкладке в v1 не создаётся.

## CLI

CLI v1 является небольшим операционным интерфейсом для человека и Windows Task Scheduler. Отдельного публичного машинного JSON-контракта нет.

Команды v1:

```text
status
run
run --scheduled
cancel --run-id <id>
retry --problem-id <id>
panel open
panel stop
panel status
diagnostics export
diagnostics debug status
diagnostics debug enable
diagnostics debug disable
```

Telegram-авторизация, Telegram `api_hash`, ключ LLM, discovery и выбор источников, пользовательская политика, цель доставки и расписание изменяются только через панель и не имеют CLI-параметров.

`run --scheduled` не задаёт интерактивных вопросов и предназначен только для зарегистрированной Windows-задачи. Если полный run уже активен, ручной `run` возвращает `run_already_active`, а Scheduler не создаёт новый экземпляр.

Общий `status` возвращает безопасную сводку расписания:

```text
schedule_configured
scheduler_registered
next_run_time
```

CLI печатает безопасный человекочитаемый результат и не принимает секреты. Exit codes:

| Код | Значение |
|---:|---|
| `0` | команда успешно завершена |
| `1` | операция не выполнена; причина напечатана безопасным типизированным кодом |
| `2` | синтаксическая ошибка |

Команда сброса дорелизной БД является только development-командой и в поставку не входит.

## Post-v1 MCP

Для агентской интеграции после v1 выбрано направление MCP. V1 не поставляет MCP-сервер, tools или resources; транспорт, полномочия, установка и отображение ошибок пока не являются публичным контрактом и не могут служить oracle для реализации v1.

