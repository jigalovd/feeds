# Документация `feeds`

**Статус комплекта:** дизайн утверждён, реализация отсутствует  
**Последнее обновление:** 2026-07-26  
**Назначение:** единая маршрутизация нормативного контекста для разработчиков и ИИ-агентов

Этот индекс отвечает только за навигацию, владение и жизненный цикл документов. Действующие продуктовые, архитектурные и технические правила находятся в документах-владельцах.

## С чего начать

1. Определи тип изменения по матрице маршрутов.
2. Прочитай обязательный контекст и только затронутые дополнительные документы.
3. Измени документ-владелец вместе с кодом или контрактом.
4. Проверь documentation impact и выполни документационную проверку.

Для общего знакомства читай: [цель и границы](product/goal-and-scope.md) → [архитектурные границы](architecture/boundaries.md) → применимый [технический раздел](technical/README.md).

## Источники истины

| Область | Владелец | Локальная карта |
|---|---|---|
| Пользовательская ценность, наблюдаемое поведение, scope и приёмка | `product` | [Продукт](product/README.md) |
| Модули, зависимости, публичные границы, долговечные факты и восстановление | `architecture` | [Архитектура](architecture/README.md) |
| Runtime, библиотеки, платформенные протоколы, форматы, безопасность и эксплуатация | `technical` | [Технический дизайн](technical/README.md) |
| Локальные правила разработки | `engineering` | [Workflow разработки](engineering/development-workflow.md), [Why-комментарии](engineering/why-comments.md) |
| Общие термины без новых правил поведения | `reference` | [Глоссарий](reference/glossary.md) |

Один нормативный факт имеет ровно одного владельца. Смежные документы ссылаются на него и не создают альтернативную формулировку.

## Маршруты по типу задачи

| Задача | Обязательный контекст | Читать дополнительно |
|---|---|---|
| Изменить продуктовую границу | [goal and scope](product/goal-and-scope.md), применимый продуктовый владелец | архитектурные и технические следствия |
| Изменить `monitoring` | [content model](product/content-model.md), [boundaries](architecture/boundaries.md), [contracts](architecture/contracts.md), [state](architecture/state.md), [Telegram](technical/telegram.md) | [persistence](technical/persistence.md) и [recovery](architecture/recovery.md), если меняются долговечные факты |
| Изменить `synthesis` | [content model](product/content-model.md), [acceptance](product/acceptance.md), [boundaries](architecture/boundaries.md), [contracts](architecture/contracts.md), [LLM](technical/llm.md) | [state](architecture/state.md), если меняется сохраняемый результат |
| Изменить `delivery` | [user flows](product/user-flows.md), [acceptance](product/acceptance.md), [contracts](architecture/contracts.md), [run lifecycle](architecture/run-lifecycle.md), [state](architecture/state.md), [Telegram](technical/telegram.md) | [recovery](architecture/recovery.md), если меняются повторы |
| Изменить `operations` | [boundaries](architecture/boundaries.md), [state](architecture/state.md), [run lifecycle](architecture/run-lifecycle.md), [recovery](architecture/recovery.md) | [persistence](technical/persistence.md), [scheduling](technical/scheduling-release.md), [observability](technical/testing-observability.md) |
| Изменить CLI или панель | [user flows](product/user-flows.md), [contracts](architecture/contracts.md), [interfaces](technical/interfaces.md), [security](technical/security.md) | владелец затронутого предметного правила |
| Изменить поставку v1 или расписание | [goal and scope](product/goal-and-scope.md), [run lifecycle](architecture/run-lifecycle.md), [recovery](architecture/recovery.md), [scheduling and packaging](technical/scheduling-release.md) | [security](technical/security.md) и [persistence](technical/persistence.md) |
| Реализовать вертикальный срез или исправление | [workflow разработки](engineering/development-workflow.md), нормативный владелец поведения, применимый архитектурный сценарий | технический владелец интеграции |
| Изменить тестовую стратегию | [workflow разработки](engineering/development-workflow.md), [acceptance](product/acceptance.md), [architecture scenarios](architecture/recovery.md), [testing](technical/testing-observability.md) | документы изменяемой области |
| Работать с комментариями | [Why-комментарии](engineering/why-comments.md), нормативный владелец изменяемого кода | decision с причиной, если она не закреплена у владельца |
| Изменить документационную структуру | [решение об AI-first структуре](decisions/2026-07-25-ai-first-documentation-structure.md) | [архивный план миграции](plans/archive/2026-07-25-ai-first-documentation-migration.md), если нужна история |

## Типы артефактов

| Тип | Назначение | Является источником истины |
|---|---|---|
| Normative | Действующее правило в области владельца | да |
| Guide | Практика разработки в пределах нормативных правил | только для своей инженерной практики |
| Reference | Термины или generated-представление кодового контракта | нет |
| Decision | Контекст, альтернативы и причина решения | нет; действующее следствие переносится владельцу |
| Active plan | Ещё не завершённая последовательность работы | нет |
| Archive plan | Историческое намерение и команды | нет |

- [Решения](decisions/README.md)
- [Планы](plans/README.md)

## Статусы нормативных документов

- `проектируется` — в области документа остаются открытые решения;
- `требует синхронизации` — решение принято, но нормативный текст ещё не согласован;
- `утверждено` — открытых решений уровня нет, но статус не подтверждает реализацию.

Закрытый вопрос становится обычной частью документа-владельца. Идентификаторы решений не переиспользуются.

## Documentation impact

Каждое изменение кода, публичного контракта или конфигурации обязано:

1. определить затронутых нормативных владельцев;
2. обновить их документы либо явно завершиться с выводом `documentation impact: none`;
3. обновить generated reference, если изменился его авторитетный кодовый источник;
4. выполнить проверку после последнего изменения.

`documentation impact: none` допустим только когда не изменились наблюдаемое поведение, границы, публичные контракты, эксплуатация и агентские маршруты.

Нормативная проза поддерживается как docs-as-code и автоматически не сочиняется. После появления кода автоматически формируются только проверяемые reference-артефакты с авторитетным кодовым источником: схема конфигурации, карта архитектурных импортов и migration head. CLI reference или JSON Schema появляются только вместе с отдельным утверждённым публичным машинным контрактом. Пустые generated-файлы до появления авторитетного источника не создаются.

## Проверка

Каноническая структурная проверка:

```console
python tools/check_docs.py
```

Self-test проверяющего скрипта:

```console
python tools/test_check_docs.py
```

Проверка выявляет битые ссылки и якоря, дубли явных anchors, отсутствующую нормативную метаинформацию, недостижимые документы, временные файлы и маркеры незавершённого текста в утверждённых нормативных документах.

## Текущий статус реализации

Документация определяет целевое поведение и дизайн. Код приложения, его CI и generated reference ещё не существуют. Проверяющий Markdown-скрипт подтверждает только структуру документации и не доказывает реализацию продукта.
