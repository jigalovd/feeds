# Волна 1: декомпозиция fake capture

**Статус:** активный план; утверждена только граница пакета `fake capture`

**Волна:** один `ContentItem` проходит `capture → synthesis → delivery → cursor advance` на fake-адаптерах

**Сквозной сценарий волны:** `RUN-HAPPY-001`

**Режим выполнения утверждённых срезов:** `AFK`

Этот план задаёт исполнимую декомпозицию только первого пакета волны. Он не
объявляет `fake capture` отдельным milestone и не закрывает `RUN-HAPPY-001`.
Формальный граф milestones первой волны будет зафиксирован после такой же
декомпозиции synthesis, delivery и orchestration.

## Нормативные владельцы

- [публичные контракты и внешние порты](../../architecture/contracts.md);
- [долговечное состояние](../../architecture/state.md);
- [жизненный цикл полного запуска](../../architecture/run-lifecycle.md);
- [сквозные сценарии восстановления](../../architecture/recovery.md);
- [workflow вертикального PR-среза](../../engineering/development-workflow.md).

Источником цели волны остаётся
[продуктовая приёмка](../../product/acceptance.md#волны-реализации-первой-версии).
План не расширяет её требования.

## Ограничения текущей стадии

Кодовая база приложения, её структура и implementation-команды ещё не созданы.
Поэтому план не выдумывает пути пакетов, test targets или команды запуска.
Первый срез может добавить только минимальный исполнимый каркас, необходимый
его публичному oracle. Выбранные пути и команды должны быть зафиксированы в
контракте среза и проектной документации до завершения его реализации.

Отдельный scaffold без наблюдаемого публичного результата не образует срез.

## Граф утверждённых PR-срезов

```text
C01 ContentItem
  → C02 CaptureBatch
    → C03 deterministic fake read
      → C04 monitoring capture
```

Каждый узел выполняется в отдельной ветке и pull request, получает собственный
clean-context verdict и попадает в `main` через squash merge.

- [ ] **C01: публичный `ContentItem`** `risk:high` `depends:[]` `mode:AFK`
  > После этого публичный контракт представляет один нормализованный элемент без Telegram SDK-типов.
- [ ] **C02: контракт `CaptureBatch`** `risk:medium` `depends:[C01]` `mode:AFK`
  > После этого контракт отличает незавершённый batch от complete-входа и фиксирует границы cursor без его продвижения.
- [ ] **C03: детерминированное fake-чтение** `risk:medium` `depends:[C02]` `mode:AFK`
  > После этого одинаковые границы чтения дают через fake один и тот же публичный `ContentItem`.
- [ ] **C04: capture одного включённого источника** `risk:high` `depends:[C03]` `mode:AFK`
  > После этого monitoring возвращает один complete batch с одним элементом, оставляя локальный cursor прежним.

### C01 — публичный `ContentItem`

**Зависимости:** нет

**Риск:** высокий: первый исполнимый срез создаёт минимальную основу приложения

**Классификация:** `AFK`

**Наблюдаемый результат**

Публичный контракт позволяет создать и прочитать `ContentItem` с нормативными
полями `item_id`, `batch_id`, `stream_id`, `normalized_content` и `origin`.
`normalized_content` различает `SemanticTextContent` и
`MetadataOnlyContent` через закрытый discriminated union. `origin` содержит
снимки username и названия, message IDs и публичную ссылку. Telegram
`peer_id`, `access_hash` и SDK-типы не входят в этот контракт.

**Oracle**

- набор и смысл публичных полей соответствуют владельцу состояния;
- `SemanticTextContent` обязательно содержит семантический текст, а
  `MetadataOnlyContent` не имеет текстового поля;
- оба варианта содержат закрытый `ContentMetadata` с типом элемента,
  неотрицательным количеством медиа, HTTP(S)-ссылками и необязательной
  безопасной атрибуцией пересылки;
- `ContentItem.stream_id` задаёт прикладную идентичность источника без
  публичного `peer_id`;
- `item_id`, `batch_id` и `stream_id` являются непустыми непрозрачными
  строками без обещанного разбираемого формата;
- `OriginReference` содержит непустые снимки username и названия,
  положительные уникальные возрастающие message IDs и каноническую
  HTTPS-ссылку без credentials;
- `ContentItem`, его вложенные value objects и упорядоченные коллекции
  неизменяемы после создания;
- `normalized_content` не принимает произвольные mappings, `Any`, namespaced
  facts или платформенные payload;
- DTO доступен через публичную границу, а не внутренности реализации;
- контракт не вводит дополнительные переходные DTO или платформенные типы.

**Допустимая поддерживающая работа**

Только минимальная структура приложения и тестовый запуск, необходимые для
исполнения этого oracle. Остальные модули, адаптеры и универсальный framework
заранее не создаются.

**Не входит**

`CaptureBatch`, чтение внешнего источника, persistence batch, synthesis,
delivery и orchestration полного запуска.

**Минимальный контекст исполнителя**

1. [workflow: иерархия и контракт среза](../../engineering/development-workflow.md#контракт-среза);
2. [contracts: публичные DTO](../../architecture/contracts.md#минимальные-публичные-api);
3. [state: `ContentItem`](../../architecture/state.md#contentitem).

### C02 — контракт `CaptureBatch`

**Зависимости:** `C01`

**Риск:** средний

**Классификация:** `AFK`

**Наблюдаемый результат**

Публичный контракт представляет batch с нормативными идентификаторами,
границами cursor, временем capture и состоянием `capturing | complete`.
Принадлежащий batch элемент использует уже принятый `ContentItem`.

**Oracle**

- `capturing` не является завершённым входом дальнейшей обработки;
- только `complete` предоставляет элементы следующей фазе;
- `cursor_before` и `cursor_after` являются границами batch, но их наличие
  само по себе не продвигает локальный cursor.

**Не входит**

Внешнее чтение, автоматическое завершение batch, восстановление частичного
batch и фактическое продвижение cursor.

**Минимальный контекст исполнителя**

1. [contracts: публичные DTO](../../architecture/contracts.md#минимальные-публичные-api);
2. [state: `CaptureBatch`](../../architecture/state.md#capturebatch);
3. [state: `ContentItem`](../../architecture/state.md#contentitem).

### C03 — детерминированное fake-чтение

**Зависимости:** `C02`

**Риск:** средний

**Классификация:** `AFK`

**Наблюдаемый результат**

Fake внешнего чтения в заданных границах детерминированно возвращает ровно один
нормализованный `ContentItem`, достаточный для будущего happy path.

**Oracle**

- повтор с одинаковыми входными границами даёт тот же наблюдаемый результат;
- наружу не выходят Telegram SDK-объекты или платформенные селекторы;
- fake проверяется по публичному контракту внешней границы и не становится
  самостоятельным источником ожидаемого поведения.

**Не входит**

Fault injection, ошибки источника, bootstrap, recovery, orchestration
`capture_enabled_sources()` и изменение cursor.

**Минимальный контекст исполнителя**

1. [contracts: внешние порты](../../architecture/contracts.md#внешние-порты);
2. [contracts: граница `stream_id`](../../architecture/contracts.md#минимальные-публичные-api);
3. [state: `ContentItem`](../../architecture/state.md#contentitem);
4. [recovery: требование к fake](../../architecture/recovery.md#проверяемые-сквозные-сценарии).

### C04 — capture одного включённого источника

**Зависимости:** `C03`

**Риск:** высокий: впервые связывает публичный monitoring API, batch и внешний fake

**Классификация:** `AFK`

**Наблюдаемый результат**

`capture_enabled_sources()` для одного включённого источника открывает batch до
внешнего чтения, завершает его после успешного чтения и возвращает один
`complete CaptureBatch` с одним `ContentItem`. Локальный cursor остаётся прежним.

**Oracle**

- запись `capturing` предшествует внешнему чтению;
- успешный результат становится видимым как один complete batch;
- `advance_cursors(batch_ids)` не вызывается внутри capture;
- следующий пакет получает только complete batch, но synthesis в этом срезе не
  запускается.

**Не входит**

Ошибки источника, повтор незавершённого batch, несколько источников, synthesis,
delivery, `operations.run()` и milestone-gate `RUN-HAPPY-001`.

**Минимальный контекст исполнителя**

1. [contracts: monitoring API](../../architecture/contracts.md#минимальные-публичные-api);
2. [state: `CaptureBatch`](../../architecture/state.md#capturebatch);
3. [run lifecycle: шаги capture](../../architecture/run-lifecycle.md#сквозной-поток-запуска);
4. [run lifecycle: cursor](../../architecture/run-lifecycle.md#локальные-cursors).

## Общий gate каждого среза

Для `C01`–`C04` обязательны:

1. oracle, выведенный из указанных нормативных владельцев до production-кода;
2. применимые developer, contract и protected tests;
3. проверка архитектурных границ и соседних Why-комментариев;
4. явный documentation impact;
5. независимый clean-context verify текущей версии PR;
6. канонические проверки документации:

```console
python tools/check_docs.py
python tools/test_check_docs.py
```

Implementation-команды добавляются сюда только после их появления и проверки.
Отсутствующая команда не заменяется предполагаемой.

## Карта границ

- `C01` производит публичный `ContentItem`, который используют `C02` и `C03`;
- `C02` производит контракт состояний и cursor-границ `CaptureBatch`, который
  используют `C03` и `C04`;
- `C03` производит детерминированное fake-чтение, которое вызывает `C04`;
- `C04` производит complete batch для будущего synthesis и гарантирует отсутствие
  преждевременного cursor commit.

## Граница продолжения плана

После интеграции `C04` пакет `fake capture` завершён, но волна и milestone не
завершены. Следующее планирование должно сначала декомпозировать synthesis до
сопоставимого размера PR-срезов. Добавлять synthesis одним крупным срезом
запрещено.
