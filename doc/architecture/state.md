# Долговечные факты и порядок сохранения

**Статус:** утверждено  
**Владелец фактов:** модель долговечных фактов и порядок фиксации внешних эффектов  
**Читать когда:** меняются состояния, сохраняемые сущности, транзакционные границы или порядок внешних операций  
**Связанные документы:** [карта архитектурной документации](README.md)

## Долговечная модель фактов

Система сохраняет наблюдаемые факты, а не один составной автомат состояний.

### `Run`

```text
run_id
trigger
status: running | completed | cancelled | failed
cancel_requested
started_at
finished_at
problems
```

Один `Run` может создать несколько независимых `DeliveryPlan`. Каждый план сохраняет `run_id` создавшего его запуска; recovery не перепривязывает старый план к восстанавливающему запуску.

### `CaptureBatch`

```text
MessageCursor
  kind: message
  message_id

TimeCursor
  kind: time
  after

CapturingBatch
  status: capturing
  batch_id
  run_id
  stream_id
  cursor_before: MessageCursor | TimeCursor
  cursor_after: MessageCursor
  captured_at

CompleteBatch
  status: complete
  batch_id
  run_id
  stream_id
  cursor_before: MessageCursor | TimeCursor
  cursor_after: MessageCursor
  captured_at
  items: ContentItem[]
```

`captured_at` — timezone-aware UTC-момент открытия batch и фиксации верхней
границы. Обычная нижняя граница содержит неотрицательный message cursor.
Значение `0` является sentinel отсутствия Telegram-сообщений на
зафиксированной границе, а не Telegram message ID. Bootstrap использует
исключительную временную границу `TimeCursor.after`, которая строго
предшествует `captured_at`. Верхняя граница всегда является
`MessageCursor`.

Запись `capturing` с нижней и верхней границами создаётся до чтения. Её
публичное значение не содержит элементов. Неполный batch после сбоя не
используется как частичный вход. Только `complete` предоставляет
неизменяемую последовательность элементов синтезу; пустой complete batch
допустим.

Публичный `CaptureBatch` является закрытым union неизменяемых
`CapturingBatch` и `CompleteBatch`. Завершение создаёт новое публичное
значение с теми же идентификаторами, границами и `captured_at`. Хранилище
может реализовать этот переход атомарным обновлением строк; публичный DTO не
делает физическую схему частью контракта.

Элементы `capturing` batch невидимы выборке синтеза. При восстановлении `monitoring` повторяет чтение по тем же границам и атомарно заменяет частичные строки полным результатом; если повтор невозможен, частичные строки удаляются, а источник фиксируется заново отдельным batch.

Для message-based диапазона `cursor_after >= cursor_before`; равенство
соответствует пустому диапазону. Message IDs complete-элементов находятся
строго после message-based нижней границы и не выше верхней. При bootstrap
числовая проверка применяется только к верхней границе. Наборы message IDs
разных элементов не пересекаются. Верхняя граница `0` требует пустого
complete batch.

Все элементы complete batch имеют его `batch_id` и `stream_id`, а их
`item_id` уникальны. Элементы сохраняют порядок capture без дополнительной
сортировки.

### `ContentItem`

```text
item_id
batch_id
stream_id
normalized_content:
  SemanticTextContent:
    mode: semantic_text
    semantic_text
    metadata: ContentMetadata
  | MetadataOnlyContent:
    mode: metadata_only
    metadata: ContentMetadata
  ContentMetadata:
    content_type: text | link | poll | photo | video | audio | voice | document | album | other_media
    media_count
    links
    forward_attribution?:
      username_snapshot?
      title_snapshot?
origin:
  username_snapshot
  title_snapshot
  message_ids
  public_url
```

`normalized_content` — закрытый discriminated union. Вариант
`SemanticTextContent` всегда содержит семантический текст, а вариант
`MetadataOnlyContent` не содержит текстового поля. Поэтому отсутствие текста
является выбранным режимом обработки, а не nullable-состоянием.

`OriginReference` не содержит платформенный `peer_id`. Стабильную прикладную
идентичность источника задаёт `ContentItem.stream_id`, а платформенное
сопоставление остаётся приватным фактом `monitoring`.

Сохраняемый `normalized_content` не содержит произвольного словаря metadata
или платформенного payload. Его варианты сохраняют только поля закрытой
публичной схемы; добавление поля выполняется как изменение публичного
контракта и схемы состояния.

`media_count` является неотрицательным целым числом. `links` содержит только
HTTP(S) URL. Необязательный `forward_attribution` содержит хотя бы один снимок
username или названия и не содержит платформенную идентичность пересылки.

`item_id`, `batch_id` и `stream_id` сохраняются как непустые непрозрачные
строки. Их внутренний способ построения не становится частью публичного
контракта. `OriginReference.message_ids` хранит положительные уникальные
Telegram message IDs в возрастающем порядке; снимки username и названия
непусты, а `public_url` является канонической HTTPS-ссылкой без credentials.

`ContentItem` и все вложенные value objects неизменяемы после создания.
Упорядоченные коллекции сохраняются как immutable-последовательности.
Коррекция нормализованного значения создаёт новый объект до фиксации complete
batch и не изменяет уже сохранённый элемент на месте.

Принадлежность элемента к незакрытому batch определяет необходимость обработки. Отдельные per-item состояния доставки, подтверждения или переноса не нужны.

### `SynthesisResult`

Сохраняется только полностью полученный и валидный результат. Частичный или невалидный ответ LLM отбрасывается.

### `DeliveryPlan`

```text
plan_id
run_id
delivery_target:
  peer_id
  access_hash
units
```

`DeliveryPlan` — долговечный неизменяемый агрегат намерения доставки. До первого внешнего вызова он целиком фиксирует минимальную адресную metadata приватного send-only получателя и упорядоченные `DeliveryUnit` и `DeliveryMessage`.

Изменение текущей конфигурации цели не изменяет уже сохранённый план. При восстановлении `operations` загружает прежний план и повторяет его с теми же `delivery_target`, финальным представлением и `random_id`.

`operations` отдельно сохраняет связь `plan_id → batch_ids`. Она не входит в публичный DTO `delivery`. Только после `confirmed` всех сообщений плана эта связь используется для атомарного продвижения локальных cursors до `cursor_after`.

### `DeliveryUnit`

```text
unit_id
kind: content_card | advertisement_summary | deterministic_summary | warning_summary
covered_item_ids
messages
```

В каждом успешно построенном плане каждый входной элемент входит ровно в одну unit с непустым `covered_item_ids`. Предупреждающая unit не покрывает элементы и не влияет на подтверждение.

Одна unit вида `content_card` соответствует одному содержательному тегу и покрывает элементы всех карточек этого тега. Все Telegram-сообщения серии тега принадлежат этой unit. Сводки рекламы и детерминированных элементов образуют по одной собственной unit соответствующего вида.

### `DeliveryMessage`

```text
message_id
order
final_text
entities:
  kind: bold | text_link
  offset_utf16
  length_utf16
  url?
random_id
outcome: pending | confirmed | unknown | failed
external_message_id
```

Принадлежность units и messages задаётся вложенностью в `DeliveryPlan`. Если физическая схема использует обратные foreign keys, они остаются приватной деталью ORM и не расширяют публичные DTO.

Статус unit не хранится отдельно. Для продвижения cursor значим только результат всего плана.

`final_text` и entities являются окончательным Telegram-представлением. Смещения и длины сохраняются в кодовых единицах UTF-16, поэтому повторная отправка не пересчитывает их из Python-индексов. Entities не пересекаются и не выходят за границы сообщения.

### `RunProblem`

Проблема содержит безопасный код, фазу, повторяемость и флаг `attention_required`. Последний является признаком проблемы, а не состоянием отдельной сущности.

Терминальные статусы `Run` определяются так:

| Статус | Условие |
|---|---|
| `completed` | Координатор дошёл до конца. Допустимы сохранённые изолированные проблемы источника, уведомления или `possible_duplicate`. |
| `cancelled` | Запрошена отмена и сохранён поздний результат текущего внешнего вызова. |
| `failed` | Обязательная фаза не завершена: системный capture завершился неизолируемой ошибкой, синтез не дал полного результата либо текущая доставка остановилась на `failed`/неисчерпанном `unknown`. |

Флаг `attention_required` сам по себе не меняет статус: он описывает необходимое действие над конкретной проблемой.

## Порядок сохранения

Для внешней операции действует правило:

1. сохранить достаточное намерение для безопасного повтора;
2. выполнить внешний вызов;
3. сохранить наблюдаемый результат до следующего внешнего вызова.

Для доставки это означает:

1. целиком сохранить неизменяемый план, `delivery_target`, финальный текст, entities и `random_id`;
2. отправить ровно одно сообщение;
3. сохранить `DeliveryReceipt`;
4. только затем начинать следующее сообщение.

После `confirmed` всех сообщений плана `operations` одной локальной транзакцией продвигает cursors связанных complete batches. При частичном или неизвестном исходе cursors остаются прежними.

Граница транзакции локального хранилища выбирается технически, но сохранение одного результата внешней операции должно быть атомарным.

