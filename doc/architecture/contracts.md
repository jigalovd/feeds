# Публичные контракты и внешние порты

**Статус:** утверждено  
**Владелец фактов:** публичные API, DTO, внешние порты, конфигурация и readiness  
**Читать когда:** меняется межмодульный контракт, внешний порт или вычисление готовности  
**Связанные документы:** [карта архитектурной документации](README.md)

## Минимальные публичные API

```text
monitoring
  discover_sources() -> Source[]
  capture_enabled_sources() -> CaptureBatch[]
  advance_cursors(batch_ids)

synthesis
  synthesize(items, policy) -> SynthesisResult

delivery
  build_plan(result, warnings, delivery_target) -> DeliveryPlan
  send(message) -> DeliveryReceipt

operations
  run(trigger) -> RunResult
  cancel(run_id)
  retry(problem_id)
  status()
```

Публичный набор DTO ограничен:

- `Source`;
- `ContentItem`;
- `CaptureBatch`;
- `SynthesisPolicy`;
- `SynthesisResult`;
- `DeliveryPlan`;
- `DeliveryUnit`;
- `DeliveryMessage`;
- `DeliveryReceipt`;
- `RunResult`;
- `RunProblem`.

`ContentItem` имеет ровно пять полей верхнего уровня: `item_id`, `batch_id`,
`stream_id`, `normalized_content` и `origin`.

`normalized_content` является закрытым discriminated union:

```text
SemanticTextContent
  mode: semantic_text
  semantic_text
  metadata: ContentMetadata

MetadataOnlyContent
  mode: metadata_only
  metadata: ContentMetadata

ContentMetadata
  content_type: text | link | poll | photo | video | audio | voice | document | album | other_media
  media_count
  links
  forward_attribution?:
    username_snapshot?
    title_snapshot?
```

`origin` является вложенным `OriginReference`:

```text
username_snapshot
title_snapshot
message_ids
public_url
```

Вложенные value objects не образуют дополнительные верхнеуровневые DTO,
переходные контракты или точки расширения. `peer_id`, `access_hash` и
Telegram SDK-типы в `ContentItem` не входят.

Каждый вариант `normalized_content` содержит только закрытый набор явно
именованных типизированных полей. Произвольные mappings, значения `Any`,
namespaced facts, platform payload и другие открытые контейнеры metadata в
публичном контракте запрещены. Новый вид безопасных metadata требует явного
изменения этого контракта.

`ContentMetadata.media_count` является неотрицательным целым числом, а
`links` содержит только HTTP(S) URL. Если `forward_attribution` присутствует,
в нём заполнен хотя бы один из снимков username или названия. Платформенная
идентичность пересылки и raw `fwd_from` наружу не выходят.

`item_id`, `batch_id` и `stream_id` являются непустыми непрозрачными строками.
Публичный контракт не обещает UUID, составной ключ или другой разбираемый
формат. Потребитель сравнивает идентификаторы целиком и не извлекает из них
платформенные или storage-факты.

`OriginReference.message_ids` содержит положительные уникальные Telegram
message IDs в возрастающем порядке. Снимки username и названия являются
непустыми строками. `public_url` является канонической HTTPS-ссылкой без
credentials и строится по первому message ID.

`ContentItem` и все его вложенные value objects неизменяемы после создания.
Упорядоченные коллекции представлены immutable-последовательностями.
Изменение значения создаёт новый DTO, а не модифицирует существующий.

`Source.stream_id` — стабильный прикладной идентификатор информационного потока. Платформенные `peer_id`, `access_hash` и SDK-объекты остаются внутри `monitoring` и не становятся публичными селекторами.

`DeliveryPlan` — публичный неизменяемый агрегат, который `delivery` строит целиком, а `operations` сохраняет до первой отправки. Он фиксирует `delivery_target` и упорядоченные units и messages, необходимые для детерминированного повтора. Связь плана с входными batches является приватным долговечным фактом `operations`, а не частью DTO `delivery`.

Принадлежность `DeliveryUnit` плану и `DeliveryMessage` unit задаётся вложенностью публичных DTO. Обратные идентификаторы родителей и физические foreign keys являются приватной деталью реализации `StateStore`.

Дублирующие входные DTO, отдельные описатели возможностей цели, переходные DTO, plugin descriptors и селекторы аккаунта/профиля в v1 не вводятся.

## Внешние порты

Архитектура требует только следующие внешние границы:

- `TelegramClient` — чтение, отправка и проверка цели;
- `LlmClient` — одна stateless-операция структурированного вызова; один synthesis может выполнить несколько таких обращений для batch, correction и merge;
- `StateStore` — все долговечные несекретные факты и секционированная конфигурация;
- `SecretStore` — Telegram-сессия и другие секреты;
- `ScheduleInstaller` — reconcile/remove/inspect Windows-задачи;
- `SystemLock` — единственный межпроцессный mutex для полного запуска и исключительных системных изменений;
- `Clock` — время и управляемые задержки.

Конкретные библиотеки и форматы выбираются в техническом дизайне. Архитектура не требует собственного абстрактного слоя над каждым вызовом стандартной библиотеки.

## Конфигурация и готовность

V1 использует один секционированный `AppConfig`. Каждый модуль валидирует только принадлежащую ему секцию. Секретные значения в конфигурацию не попадают: допустимы только ссылки на `SecretStore`.

Готовность вычисляется из сохранённых проверяемых фактов:

```text
telegram_ready
llm_ready
sources_discovered
policy_ready
target_tested
schedule_configured
scheduler_registered
```

Отдельного автомата мастера, долговечного черновика и rollback-протокола нет. Каждый валидированный раздел настройки сохраняется атомарно, а повторное открытие панели начинается с первого неготового шага.

