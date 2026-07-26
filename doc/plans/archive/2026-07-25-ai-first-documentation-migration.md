# AI-first Documentation Migration Implementation Plan

**Статус артефакта:** архивный; миграция выполнена и проверена 2026-07-25  
**Действующая структура:** [карта документации](../../README.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Разделить документацию `feeds` на небольшие документы-владельцы, создать task-oriented маршрутизацию для агентов и добавить исполняемую проверку актуальности структуры.

**Architecture:** Корневой `AGENTS.md` остаётся машинной точкой входа, корневой `README.md` — человеческой, а `doc/README.md` становится единственным маршрутизатором контекста. Нормативные документы разделяются по владельцам фактов без смыслового изменения; структурная проверка обеспечивает ссылки, якоря, метаинформацию, отсутствие сирот и запрещённых временных артефактов.

**Tech Stack:** Markdown, PowerShell 7/Windows PowerShell, встроенные .NET API; внешние пакеты и documentation framework не используются.

**Ограничение выполнения:** каталог не распознаётся как Git-репозиторий, поэтому шаги commit отсутствуют. Коммиты нельзя считать критерием выполнения этой миграции.

---

## Карта файлов

### Точки входа

- Create: `README.md` — краткая человеческая ориентация и честный статус реализации.
- Modify: `AGENTS.md` — машинный маршрут, documentation impact и подтверждённая команда проверки.
- Rewrite: `doc/README.md` — единая матрица контекста, карта владельцев и жизненный цикл.

### Нормативные владельцы

- Create: `doc/product/README.md`
- Create: `doc/product/goal-and-scope.md`
- Create: `doc/product/content-model.md`
- Create: `doc/product/user-flows.md`
- Create: `doc/product/acceptance.md`
- Create: `doc/architecture/README.md`
- Create: `doc/architecture/boundaries.md`
- Create: `doc/architecture/contracts.md`
- Create: `doc/architecture/state.md`
- Create: `doc/architecture/run-lifecycle.md`
- Create: `doc/architecture/recovery.md`
- Create: `doc/technical/README.md`
- Create: `doc/technical/runtime.md`
- Create: `doc/technical/telegram.md`
- Create: `doc/technical/llm.md`
- Create: `doc/technical/persistence.md`
- Create: `doc/technical/security.md`
- Create: `doc/technical/interfaces.md`
- Create: `doc/technical/scheduling-release.md`
- Create: `doc/technical/testing-observability.md`

### Инженерные, справочные и исторические материалы

- Move: `doc/WHY_COMMENTS.md` → `doc/engineering/why-comments.md`
- Create: `doc/reference/glossary.md`
- Create: `doc/decisions/README.md`
- Move: `doc/why-comments-skill-design.md` → `doc/decisions/2026-07-25-why-comments-skill-design.md`
- Create: `doc/plans/README.md`
- Move: `doc/plans/2026-07-25-maintain-why-comments-agent-skill.md` → `doc/plans/archive/2026-07-25-maintain-why-comments-agent-skill.md`
- Keep: `doc/decisions/2026-07-25-ai-first-documentation-structure.md`
- Keep during execution: `doc/plans/active/2026-07-25-ai-first-documentation-migration.md`

### Проверка

- Create: `tools/check-docs.ps1` — каноническая структурная проверка.
- Create: `tools/test-check-docs.ps1` — изолированные positive/negative сценарии проверяющего скрипта.

### Удаляемые исходные агрегаты

- Delete after content comparison: `doc/business.md`
- Delete after content comparison: `doc/architecture.md`
- Delete after content comparison: `doc/technical.md`

### Task 1: Создать проверяющий контур до миграции

**Files:**

- Create: `tools/check-docs.ps1`
- Create: `tools/test-check-docs.ps1`

- [x] **Step 1: Создать failing self-test**

Self-test создаёт временный workspace и последовательно проверяет:

1. минимальный связный комплект завершается с кодом `0`;
2. отсутствующая Markdown-ссылка завершается ненулевым кодом и кодом проблемы `broken-link`;
3. отсутствующий якорь возвращает `broken-anchor`;
4. два одинаковых явных anchor ID возвращают `duplicate-anchor`;
5. нормативный документ без четырёх обязательных полей возвращает `missing-metadata`;
6. документ без входящей ссылки возвращает `orphan-document`;
7. временный файл возвращает `temporary-file`;
8. незавершённый маркер в нормативном документе возвращает `unfinished-marker`.

Run:

```powershell
pwsh -NoProfile -File .\tools\test-check-docs.ps1
```

Expected before implementation: failure because `tools/check-docs.ps1` does not exist.

- [x] **Step 2: Реализовать минимальный checker**

`tools/check-docs.ps1` принимает необязательный `-WorkspaceRoot`, по умолчанию использует родительский каталог `tools`. Скрипт:

- перечисляет Markdown через `Get-ChildItem`;
- разбирает обычные Markdown links, исключая внешние URI и содержимое fenced code blocks;
- разрешает относительные пути от каталога документа;
- строит heading anchors и читает явные HTML anchor IDs;
- требует поля `Статус`, `Владелец фактов`, `Читать когда`, `Связанные документы` для файлов под `doc/product`, `doc/architecture` и `doc/technical`, кроме локальных `README.md`;
- строит граф входящих ссылок от `README.md`, `AGENTS.md` и `doc/README.md`;
- разрешает отсутствие входящей ссылки только у этих трёх корней;
- проверяет расширения `.tmp`, `.bak`, `.orig` и суффикс `~`;
- ищет служебные маркеры незавершённого текста только в утверждённых нормативных документах;
- печатает стабильные строки `<code>: <relative-path>: <detail>`;
- завершает работу кодом `1`, если найдена хотя бы одна проблема, иначе печатает счётчики и `DOCS_CHECK=PASS`.

Не добавлять Why-комментарии к прямолинейному обходу файлов. Краткий Why-комментарий допустим только рядом с исключением fenced code blocks: примеры команд и исторические планы не должны превращаться в активные ссылки графа.

- [x] **Step 3: Запустить self-test**

Run:

```powershell
pwsh -NoProfile -File .\tools\test-check-docs.ps1
```

Expected: восемь сценариев `PASS` и итог `CHECK_DOCS_TESTS=PASS`.

### Task 2: Создать точки входа и протокол актуальности

**Files:**

- Create: `README.md`
- Rewrite: `doc/README.md`
- Modify: `AGENTS.md`

- [x] **Step 1: Создать корневой README**

Зафиксировать назначение продукта, статус «дизайн утверждён, кодовая база отсутствует», ссылки для пользователя, разработчика и агента. Не копировать нормативные правила.

- [x] **Step 2: Переписать индекс документации**

Добавить:

- hierarchy источников истины;
- таблицу маршрутов из design-документа;
- карту действующих документов;
- различие normative, guide, reference, decision, active plan и archive;
- обязательный documentation-impact шаг;
- границу generated reference;
- каноническую команду проверки после её фактического успешного запуска.

- [x] **Step 3: Сократить и обновить AGENTS**

Сохранить четыре архитектурных границы и правила секретов. Заменить старые пути на `doc/README.md` и task-oriented routing. Добавить обязательные действия:

```text
1. определить documentation impact;
2. обновить документ-владелец либо обосновать documentation impact: none;
3. выполнить pwsh -NoProfile -File .\tools\check-docs.ps1;
4. не объявлять завершение при несинхронизированной документации.
```

### Task 3: Разделить продуктовый источник истины

**Files:**

- Create: `doc/product/README.md`
- Create: `doc/product/goal-and-scope.md`
- Create: `doc/product/content-model.md`
- Create: `doc/product/user-flows.md`
- Create: `doc/product/acceptance.md`
- Source: `doc/business.md`

- [x] **Step 1: Разнести разделы без смыслового изменения**

Mapping:

| Новый владелец | Разделы исходного документа |
|---|---|
| `goal-and-scope.md` | «Конечная бизнес-цель», «Исходная проблема», «Границы первой версии» |
| `content-model.md` | «Информационные потоки», «Элементы содержимого», «Реклама», «Фиксация новых элементов», «Систематизация и обобщение» |
| `user-flows.md` | «Расписание и запуск», «Доставка результата», «Пользовательский контур v1», «Ошибки и уведомления» |
| `acceptance.md` | «Критерии достижения бизнес-цели», «Порядок реализации первой версии», «Стратегия приёмки первой версии» |

Каждый файл получает четыре обязательных поля и ссылку на `doc/product/README.md`.

- [x] **Step 2: Создать локальный product index**

Индекс отвечает, какой файл читать для scope, content model, flows и acceptance. Правила дочерних файлов не дублируются.

- [x] **Step 3: Сравнить покрытие заголовков**

Каждый `##` исходного `business.md`, кроме заголовка документа, должен существовать ровно в одном новом нормативном файле.

### Task 4: Разделить архитектурный источник истины

**Files:**

- Create: `doc/architecture/README.md`
- Create: `doc/architecture/boundaries.md`
- Create: `doc/architecture/contracts.md`
- Create: `doc/architecture/state.md`
- Create: `doc/architecture/run-lifecycle.md`
- Create: `doc/architecture/recovery.md`
- Source: `doc/architecture.md`

- [x] **Step 1: Разнести разделы по владельцам**

| Новый владелец | Разделы исходного документа |
|---|---|
| `boundaries.md` | «Архитектурная цель», «Принятое решение», «Модули и ответственность», «Правило зависимостей» |
| `contracts.md` | «Минимальные публичные API», «Внешние порты», «Конфигурация и готовность» |
| `state.md` | «Долговечная модель фактов», «Порядок сохранения» |
| `run-lifecycle.md` | «Сквозной поток запуска», «Атомарность доставки», «Подтверждение источника», «Bootstrap» |
| `recovery.md` | «Ошибки и повторы», «Кооперативная отмена», «Конкурентные триггеры», «Точки входа», «Наблюдаемость и безопасность», «Архитектура для ИИ-разработки», «Проверяемые сквозные сценарии», «Порядок реализации», «Архитектурные инварианты» |

- [x] **Step 2: Создать локальный architecture index**

Индекс маршрутизирует boundary, contract, state, lifecycle и recovery changes.

- [x] **Step 3: Сравнить покрытие заголовков**

Каждый исходный `##` и принадлежащие ему `###` должны сохраниться ровно у одного владельца.

### Task 5: Разделить технический источник истины

**Files:**

- Create: `doc/technical/README.md`
- Create: `doc/technical/runtime.md`
- Create: `doc/technical/telegram.md`
- Create: `doc/technical/llm.md`
- Create: `doc/technical/persistence.md`
- Create: `doc/technical/security.md`
- Create: `doc/technical/interfaces.md`
- Create: `doc/technical/scheduling-release.md`
- Create: `doc/technical/testing-observability.md`
- Source: `doc/technical.md`

- [x] **Step 1: Разнести разделы по техническим владельцам**

| Новый владелец | Разделы исходного документа |
|---|---|
| `runtime.md` | «Статус технического стека», «Повторы внешних операций» |
| `telegram.md` | «Техническая граница Telegram» и все разделы `Telegram:*`, а также «План и единицы доставки» |
| `llm.md` | «Контракт LLM», «LLM: контекст и пакетирование» |
| `persistence.md` | «Долговечное состояние», «Миграции схемы и восстановление», «Конфигурация» |
| `security.md` | «Секреты», «Единый межпроцессный lock» |
| `interfaces.md` | «Настройка и readiness», «Локальная админ-панель», «CLI» |
| `scheduling-release.md` | «Windows Task Scheduler», «Ручное обновление и rollback поставки» |
| `testing-observability.md` | «Тестовый стек», «Диагностика и срок жизни» |

- [x] **Step 2: Создать локальный technical index**

Индекс маршрутизирует platform, runtime, persistence, security, interface, release и verification changes.

- [x] **Step 3: Сравнить покрытие заголовков**

Все 27 исходных разделов `##` должны существовать ровно у одного нового владельца.

### Task 6: Классифицировать ненормативные материалы

**Files:**

- Move and modify: `doc/engineering/why-comments.md`
- Create: `doc/reference/glossary.md`
- Create: `doc/decisions/README.md`
- Move and modify: `doc/decisions/2026-07-25-why-comments-skill-design.md`
- Create: `doc/plans/README.md`
- Move and annotate: `doc/plans/archive/2026-07-25-maintain-why-comments-agent-skill.md`

- [x] **Step 1: Выделить glossary**

Перенести термины из старого `doc/README.md` без изменения определений. Glossary не вводит поведение и ссылается на нормативного владельца при споре.

- [x] **Step 2: Переместить инженерное руководство**

Обновить ссылки в примерах Why-комментариев на новые устойчивые документы-владельцы.

- [x] **Step 3: Создать decision и plan indexes**

Decision index объясняет, что действующее следствие всегда находится у нормативного владельца. Plan index отделяет active от archive и предупреждает, что чекбоксы не являются свидетельством выполнения.

- [x] **Step 4: Архивировать завершённый план skill**

Добавить в начало статус `архивный, выполнен` и ссылку на соответствующий decision. Старые пути внутри командных примеров оставить историческими; checker игнорирует fenced code blocks и не включает archive в проверку устаревших нормативных путей.

### Task 7: Удалить агрегаты и провести сквозную проверку

**Files:**

- Delete: `doc/business.md`
- Delete: `doc/architecture.md`
- Delete: `doc/technical.md`
- Verify: all Markdown
- Verify: `tools/check-docs.ps1`

- [x] **Step 1: Проверить полноту переноса**

Сравнить множества заголовков исходных и новых документов и вручную проверить все вводные абзацы, таблицы, code blocks и явные anchors.

- [x] **Step 2: Удалить только полностью перенесённые агрегаты**

Удалять исходный файл только после подтверждения покрытия всех его разделов.

- [x] **Step 3: Запустить self-test checker**

Run:

```powershell
pwsh -NoProfile -File .\tools\test-check-docs.ps1
```

Expected: `CHECK_DOCS_TESTS=PASS`.

- [x] **Step 4: Запустить каноническую проверку**

Run:

```powershell
pwsh -NoProfile -File .\tools\check-docs.ps1
```

Expected: `DOCS_CHECK=PASS`, ноль битых ссылок, якорей, дублей, сирот, отсутствующих metadata, временных файлов и незавершённых нормативных маркеров.

- [x] **Step 5: Провести cold-read маршрутов**

Проверить маршруты `monitoring`, `synthesis`, `delivery`, `operations`, CLI/panel, scheduling/release и testing. Для каждого маршрута определить владельца изменения без чтения несвязанного технического раздела.

- [x] **Step 6: Финально проверить область изменений**

Убедиться, что:

- утверждённые продуктовые, архитектурные и технические решения не изменены;
- generated reference описан как будущий контракт, но пустые generated-файлы не созданы;
- новые implementation-команды не заявлены;
- Why-комментарий в checker, если он существует, объясняет только локальное исключение fenced code blocks;
- текущий активный план отражает фактические завершённые шаги.

