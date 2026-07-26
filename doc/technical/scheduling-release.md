# Расписание и поставка v1

**Статус:** утверждено  
**Владелец фактов:** Windows Task Scheduler и формат поставки v1  
**Читать когда:** меняются расписание, Task Scheduler или PyInstaller-поставка  
**Связанные документы:** [карта технической документации](README.md)

## Windows Task Scheduler

Windows Task Scheduler 2.0 — backend расписания v1. Адаптер использует COM API через pywin32, а не PowerShell или `schtasks.exe`.

`ScheduleInstaller` предоставляет:

```text
reconcile(config)
remove()
inspect()
```

Единственная задача регистрируется в корне Task Scheduler с identity:

```text
\Feeds Telegram News Digest
```

`reconcile` создаёт или обновляет задачу через `TASK_CREATE_OR_UPDATE`. Передаются текущий SID пользователя, `TASK_LOGON_INTERACTIVE_TOKEN`, пустой password и `TASK_RUNLEVEL_LUA`. Выполнение после выхода пользователя не требуется. Задача работает в том же `CurrentUser`-контексте DPAPI, что интерактивная настройка.

Exec action:

```text
executable: <absolute installation path>\feeds.exe
arguments:  run --scheduled
working directory: <absolute installation path>
```

Environment не содержит конфигурацию или секреты. Пользовательские данные разрешаются через `%LOCALAPPDATA%\Feeds`.

Задача имеет один фиксированный time trigger. После `reconcile`, который создал или изменил definition, первый автоматический запуск происходит через полный настроенный интервал. Repetition использует интервал от 30 минут до 72 часов и не останавливает уже начатый процесс.

Settings фиксированы:

```text
StartWhenAvailable = true
WakeToRun = false
RunOnlyIfIdle = false
RunOnlyIfNetworkAvailable = false
DisallowStartIfOnBatteries = false
StopIfGoingOnBatteries = false
ExecutionTimeLimit = PT0S
RestartCount = 0
AllowHardTerminate = false
Hidden = false
MultipleInstances = TASK_INSTANCES_IGNORE_NEW
```

Windows может выполнить один пропущенный запуск при первой доступной возможности. Приложение не переустанавливает следующую границу относительно фактического старта. Если предыдущий экземпляр ещё работает, новый trigger игнорируется; накопившееся содержимое остаётся после локальных cursors и попадёт в следующий запуск.

`remove` идемпотентен и считает отсутствие задачи успехом. `reconcile` и `remove` используют `SystemLock`; при активном run возвращается типизированный конфликт.

`inspect` не захватывает lock и возвращает безопасный статус:

```text
registered
enabled
state
last_run_time
next_run_time
last_task_result
```

`scheduler_registered = true` означает, что задача существует, включена и вызывает текущий абсолютный путь `feeds.exe` с ожидаемыми аргументами.

При сохранении интервала панель сначала атомарно обновляет конфигурацию, затем вызывает `reconcile`. Если конфигурация сохранена, а Windows-операция не выполнена, `schedule_configured = true`, `scheduler_registered = false`, а пользователь получает типизированную проблему и может повторить сохранение.

При отключении расписания панель сначала вызывает `remove`, затем очищает настроенный интервал. Ошибка между шагами оставляет безопасное восстанавливаемое состояние без зарегистрированной задачи; повторное отключение завершает очистку конфигурации.

Отдельный демон расписания, очередь triggers, сетевой наблюдатель и внеплановые OS-задачи не создаются.

## Поставка v1

V1 собирается как самодостаточный PyInstaller `onedir`. Каталог содержит `feeds.exe`, миграции, локальные web-assets и runtime dependencies. Установленная поставка не скачивает зависимости и не изменяет собственные файлы.

Первый запуск создаёт пользовательскую схему через Alembic. Встроенные backup, обновление существующей установки, активация соседней версии и rollback в v1 отсутствуют.

Перед первым обновлением после v1 эти операции проектируются как отдельная возможность на основании фактической схемы, формата поставки и опыта эксплуатации. Текущий документ не резервирует для них CLI-команды, состояния или формат manifest.
