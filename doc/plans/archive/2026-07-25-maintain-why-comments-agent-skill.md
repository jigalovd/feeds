# Maintain Why Comments Agent Skill Implementation Plan

**Статус артефакта:** архивный; соответствующие проектные файлы присутствуют в текущем workspace  
**Связанное решение:** [универсальный skill Why-комментариев](../../decisions/2026-07-25-why-comments-skill-design.md)  
**Важно:** чекбоксы и команды ниже сохраняют исходное намерение и не являются доказательством выполнения.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать переносимый Agent Skill для сопровождения Why-комментариев, установить его в общей пользовательской точке и подключить к репозиторию `feeds` без дублирования фундаментальных инвариантов.

**Architecture:** Универсальная процедура живёт в одном стандартном `SKILL.md` под `~/.agents/skills/`. Корневой `AGENTS.md` репозитория только активирует процедуру и задаёт проектную иерархию источников, а `WHY_COMMENTS.md` содержит границу «стратегия против тактики» и локальные примеры `feeds`.

**Tech Stack:** Open Agent Skills `SKILL.md`, Markdown, PowerShell, официальный `skills-ref` validator при доступности.

---

## Карта файлов

- Создать временно: `D:\projects\feeds\.skill-build\maintain-why-comments\SKILL.md` — проверяемый staging универсального skill.
- Установить: `C:\Users\jigal\.agents\skills\maintain-why-comments\SKILL.md` — общая пользовательская копия для совместимых агентов.
- Создать: `D:\projects\feeds\AGENTS.md` — проектная точка входа и активация skill.
- Переписать: `D:\projects\feeds\doc\WHY_COMMENTS.md` — проектная граница и примеры.
- Изменить: `D:\projects\feeds\doc\README.md` — обнаружение проектного руководства.
- Удалить после установки: `D:\projects\feeds\.skill-build` — только после проверки совпадения установленного файла.

Git-коммиты не входят в план: `D:\projects\feeds` сейчас не распознаётся как Git-репозиторий.

### Task 1: Подготовить стандартный Agent Skill

**Files:**

- Create: `D:\projects\feeds\.skill-build\maintain-why-comments\SKILL.md`

- [ ] **Step 1: Убедиться, что глобальная цель не существует**

Run:

```powershell
$target = 'C:\Users\jigal\.agents\skills\maintain-why-comments'
if (Test-Path -LiteralPath $target) {
    throw "Target already exists: $target"
}
```

Expected: команда завершается без вывода.

- [ ] **Step 2: Попытаться инициализировать staging штатным генератором skill**

Run with approval because the configured Python launcher is blocked by the current sandbox:

```powershell
python 'C:\Users\jigal\.codex\skills\.system\skill-creator\scripts\init_skill.py' `
  maintain-why-comments `
  --path 'D:\projects\feeds\.skill-build'
```

Expected: создан каталог `D:\projects\feeds\.skill-build\maintain-why-comments`.

Если штатный генератор недоступен из-за отсутствующей runtime-зависимости, зафиксировать точную ошибку и не устанавливать зависимость только ради scaffold. В Step 4 создать `SKILL.md` напрямую через `apply_patch`: открытый стандарт требует содержимое файла, а не конкретный генератор.

- [ ] **Step 3: Удалить vendor-specific metadata из staging**

Генератор может создать `agents/openai.yaml`. Проверить точные цели:

```powershell
$staging = (Resolve-Path -LiteralPath 'D:\projects\feeds\.skill-build\maintain-why-comments').Path
$workspace = (Resolve-Path -LiteralPath 'D:\projects\feeds').Path
if (-not $staging.StartsWith($workspace, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Staging escaped workspace: $staging"
}
Get-ChildItem -Force -Recurse -LiteralPath $staging
```

Если генератор успешно отработал и существует только сгенерированный `agents/openai.yaml`, удалить каталог `agents`:

```powershell
Remove-Item -LiteralPath 'D:\projects\feeds\.skill-build\maintain-why-comments\agents' -Recurse
```

Expected: в каталоге skill остаётся только `SKILL.md`.

- [ ] **Step 4: Заменить шаблон полным универсальным содержимым**

Использовать `apply_patch` и привести `SKILL.md` к точному содержимому:

```markdown
---
name: maintain-why-comments
description: Maintain concise Why comments whenever an agent creates, changes, refactors, fixes, or reviews source code. Use to preserve non-obvious business, architectural, security, compatibility, platform, reliability, and measured performance constraints that a reasonable refactor could accidentally violate.
---

# Maintain Why Comments

## Outcome

Keep comments trustworthy and sparse. Explain why a local implementation must remain unusual; do not narrate what the code already says.

Finishing with no new comments is valid when the code, types, tests, and project documents already communicate enough.

## Establish context

Before editing:

1. Read applicable repository instructions.
2. Find the fundamental documents, ADRs, contracts, tests, and types relevant to the change.
3. Inspect the changed code and its neighboring comments.
4. Resolve contradictions in favor of the current authoritative project source, not the nearest comment.

Fundamental documents own strategy and system invariants. Code comments own only the tactical reason for a specific local implementation.

## Decide whether a comment is needed

Add or retain a Why comment only when both are true:

1. The reason cannot be recovered reliably from code, names, types, or tests.
2. A reasonable-looking change could violate a business invariant, security property, compatibility requirement, platform constraint, recovery guarantee, architectural boundary, or measured performance requirement.

Use this decision:

- `none` — the implementation already communicates enough.
- `refactor` — simplify the code instead of explaining avoidable complexity.
- `enforce` — prefer a type, assertion, test, lint rule, or architectural check when the rule can be verified mechanically.
- `comment` — explain a local non-obvious reason.
- `reference` — state the local consequence briefly and point to a stable authoritative source.

Anticipate refactoring. Code that looks redundant, awkward, or slower than an obvious alternative needs a local explanation only when a confirmed constraint requires that shape.

## Write the comment

Include only what is useful:

- the confirmed reason or constraint;
- why it produces this local implementation;
- what an obvious alternative would break, when that is not already clear;
- a stable document section, ADR, issue, or decision identifier when one exists.

Match the language and comment style declared by the repository. If none is declared, follow the surrounding code. Do not impose English, Russian, a fixed template, or a mandatory `WHY:` prefix.

Keep the comment close to the smallest code region governed by the reason.

## Reject weak comments

Do not add comments that:

- restate a function name, condition, assignment, loop, type, or syntax;
- copy a specification into the source file;
- describe temporary change history instead of the current reason;
- compensate for code that can be made clear safely;
- contain an unverified library bug, benchmark, incident, or external limitation;
- cite line numbers, current commit hashes, or another quickly expiring location;
- prescribe a project-wide invariant that belongs in fundamental documentation.

Claims about external bugs or version-specific behavior need a verifiable issue, release note, test, or other project evidence. Never invent a rationale after the code has been written.

## Maintain existing comments

For every comment adjacent to changed code, choose explicitly:

- keep it when its reason and consequence remain true;
- update it when the invariant survives but the implementation or wording changes;
- delete it when the reason disappears, becomes obvious, or moves to a better enforceable mechanism;
- add a new comment only for a newly introduced non-obvious decision.

An outdated comment is a defect. Preserving comments is not a goal by itself.

## Examples

Bad:

```python
# Increment the retry count.
retry_count += 1
```

Better:

```python
# Keep attempt numbers monotonic because the provider's idempotency key includes
# this value; reusing one can replay an already accepted request.
retry_count += 1
```

Reference instead of duplication:

```python
# Reject partial captures here so downstream synthesis sees only atomic batches.
# See the architecture decision "Capture consistency".
```

Prefer refactoring when the comment merely decodes confusing control flow.

## Finish the task

1. Re-read the changed region without assuming the comments are correct.
2. Confirm every retained comment still matches authoritative project sources.
3. Remove narration and duplicated policy.
4. Run the task's normal verification.
5. Mention material comment additions, updates, or removals in the final summary. Do not create a ceremonial report when no comment change was needed.
```

- [ ] **Step 5: Проверить отсутствие лишних ресурсов**

Run:

```powershell
Get-ChildItem -Force -Recurse -LiteralPath 'D:\projects\feeds\.skill-build\maintain-why-comments'
```

Expected: ровно один файл `SKILL.md`.

### Task 2: Валидировать переносимость skill

**Files:**

- Test: `D:\projects\feeds\.skill-build\maintain-why-comments\SKILL.md`

- [ ] **Step 1: Запустить официальный validator, если он доступен**

Run:

```powershell
skills-ref validate 'D:\projects\feeds\.skill-build\maintain-why-comments'
```

Expected: PASS. Если команда отсутствует, перейти к Step 2 и явно зафиксировать отсутствие official validator; не объявлять официальный PASS.

- [ ] **Step 2: Выполнить структурную fallback-проверку**

Run:

```powershell
$skillPath = 'D:\projects\feeds\.skill-build\maintain-why-comments\SKILL.md'
$raw = Get-Content -Raw -LiteralPath $skillPath

if ($raw -notmatch '(?s)\A---\r?\nname: maintain-why-comments\r?\ndescription: .{1,1024}\r?\n---\r?\n') {
    throw 'Invalid or incomplete SKILL.md frontmatter'
}
if ((Split-Path -Leaf (Split-Path -Parent $skillPath)) -ne 'maintain-why-comments') {
    throw 'Skill name does not match its directory'
}
if ($raw -match '(?i)\b(TODO|TBD|FIXME)\b') {
    throw 'Placeholder found'
}
'fallback validation: PASS'
```

Expected: `fallback validation: PASS`.

- [ ] **Step 3: Проверить отсутствие vendor- и project-specific зависимостей**

Run:

```powershell
rg -n -i 'Codex|OpenAI|Claude|Copilot|Telegram|Telethon|feeds|openai\.yaml|allowed-tools' `
  'D:\projects\feeds\.skill-build\maintain-why-comments'
```

Expected: совпадений нет.

- [ ] **Step 4: Провести четыре ручных сценария**

Проверить решения по алгоритму skill:

| Сценарий | Ожидаемое решение |
|---|---|
| `total = price * quantity` | `none` |
| Порядок durable intent → external call → receipt | `comment` или `reference` |
| Комментарий с отменённым требованием совместимости | удалить |
| Вложенная ветвистая логика, которую можно безопасно выразить именованными функциями | `refactor` |

Expected: skill однозначно приводит к указанным решениям без проектного контекста.

### Task 3: Установить skill в общей пользовательской точке

**Files:**

- Create: `C:\Users\jigal\.agents\skills\maintain-why-comments\SKILL.md`

- [ ] **Step 1: Повторно проверить точную цель**

Run:

```powershell
$source = (Resolve-Path -LiteralPath 'D:\projects\feeds\.skill-build\maintain-why-comments').Path
$targetParent = (Resolve-Path -LiteralPath 'C:\Users\jigal\.agents\skills').Path
$target = Join-Path $targetParent 'maintain-why-comments'

if (Test-Path -LiteralPath $target) {
    throw "Refusing to overwrite existing skill: $target"
}
"source=$source"
"target=$target"
```

Expected: выведены ровно staging и глобальная цель; цель отсутствует.

- [ ] **Step 2: Скопировать проверенный каталог**

Run with approval for writing outside the workspace:

```powershell
Copy-Item `
  -LiteralPath 'D:\projects\feeds\.skill-build\maintain-why-comments' `
  -Destination 'C:\Users\jigal\.agents\skills\maintain-why-comments' `
  -Recurse
```

Expected: создан глобальный каталог с одним `SKILL.md`.

- [ ] **Step 3: Проверить идентичность staging и установленного файла**

Run:

```powershell
$sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath 'D:\projects\feeds\.skill-build\maintain-why-comments\SKILL.md').Hash
$installedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\Users\jigal\.agents\skills\maintain-why-comments\SKILL.md').Hash
if ($sourceHash -ne $installedHash) {
    throw 'Installed skill differs from validated staging'
}
"installed SHA256=$installedHash"
```

Expected: один SHA-256 и отсутствие ошибки.

### Task 4: Подключить skill к `feeds`

**Files:**

- Create: `D:\projects\feeds\AGENTS.md`

- [ ] **Step 1: Создать минимальную корневую инструкцию**

Использовать `apply_patch` и создать:

```markdown
# Инструкции для агентов

## Источники истины

Перед планированием или изменением кода прочитай `doc/README.md` и применимые документы-владельцы:

- `doc/business.md` определяет пользовательское поведение и продуктовые границы;
- `doc/architecture.md` определяет модули, зависимости, долговечные факты и восстановление;
- `doc/technical.md` определяет платформенные протоколы, форматы, безопасность и эксплуатацию.

При противоречии комментария нормативному документу нормативный документ имеет приоритет.

## Why-комментарии

При создании, изменении, рефакторинге или ревью кода используй Agent Skill `maintain-why-comments`, если он доступен. Если клиент не поддерживает skill, следуй `doc/WHY_COMMENTS.md`.

Фундаментальные документы владеют стратегией и системными инвариантами. Комментарии в коде объясняют только локальную тактику: почему конкретная реализация обязана выглядеть именно так и что нарушит очевидная альтернатива.

Не копируй фундаментальные правила в код. Ссылайся на устойчивый документ или раздел и обновляй либо удаляй комментарий вместе с изменившейся причиной.

## Архитектурные границы

- Модулей ровно четыре: `monitoring`, `synthesis`, `delivery`, `operations`.
- Полным запуском владеет только `operations`.
- Предметные модули не вызывают друг друга и не импортируют внутренние реализации соседей.
- Telegram-типы не проникают в контракт `synthesis`.
- Реализации внешних портов явно связываются в composition root; runtime discovery и plugin registry запрещены.
- Секреты существуют только через `SecretStore` и не попадают в код, конфигурацию, логи или диагностические артефакты.

## Проверка

Кодовая база и канонические команды проверки ещё не созданы. Не выдумывай команды. Добавь их сюда после появления подтверждённого implementation workflow.
```

- [ ] **Step 2: Проверить компактность и отсутствие дублирования**

Run:

```powershell
$lines = (Get-Content -LiteralPath 'D:\projects\feeds\AGENTS.md').Count
if ($lines -gt 50) {
    throw "AGENTS.md is too large for the root entry point: $lines lines"
}
rg -n 'maintain-why-comments|документы владеют|Не выдумывай команды' 'D:\projects\feeds\AGENTS.md'
```

Expected: файл короче 50 строк; найдены три ключевых правила.

### Task 5: Переработать проектное руководство

**Files:**

- Modify: `D:\projects\feeds\doc\WHY_COMMENTS.md`

- [ ] **Step 1: Полностью заменить старую версию**

Использовать `apply_patch`; не сохранять абзацы старого документа. Итоговый файл:

````markdown
# Why-комментарии в `feeds`

**Назначение:** проектные границы и примеры для локальных комментариев  
**Не является:** источником бизнес-, архитектурных или технических инвариантов

Фундаментальные документы описывают стратегию и правила системы. Why-комментарий объясняет тактику: почему конкретный участок реализации устроен именно так и какое разумное на вид изменение нарушит действующее правило.

Если доступен универсальный Agent Skill `maintain-why-comments`, используй его рабочий процесс. Этот документ добавляет только контекст `feeds`.

## Граница ответственности

| Критерий | Фундаментальный документ | Why-комментарий |
|---|---|---|
| Вопрос | Каковы правила и инварианты системы? | Почему эта локальная реализация обязана выглядеть именно так? |
| Жизненный цикл | Меняется при пересмотре продукта, архитектуры или технической политики | Обновляется или удаляется вместе с реализацией |
| Момент использования | Анализ и планирование изменения | Написание, рефакторинг и ревью кода |
| Владелец содержания | `business.md`, `architecture.md`, `technical.md` | Минимальный участок кода, на который действует причина |

`business.md` владеет пользовательским поведением и границами продукта. `architecture.md` владеет модулями, зависимостями, долговечными фактами и восстановлением. `technical.md` владеет платформенными протоколами, форматами, безопасностью и эксплуатацией.

Комментарий не вводит новое системное правило. Если локальная причина следует из фундаментального решения, комментарий кратко формулирует только следствие и указывает устойчивый документ или раздел.

## Когда нужен локальный комментарий

Комментарий оправдан, если код выглядит избыточным, необычным или неоптимальным, но эта форма необходима из-за подтверждённого ограничения. Особенно важны:

- порядок сохранения вокруг внешнего эффекта;
- преобразование между разными системами координат внешнего протокола;
- локальная защита от повторов, частичного результата или неизвестного исхода;
- проверенный workaround конкретной версии библиотеки;
- реализация архитектурной границы, которую легко случайно обойти.

Не добавляй комментарий, если он пересказывает имя, условие, цикл, тип или очевидное действие. Сначала упрости код, если комментарий нужен только для расшифровки запутанной реализации.

## Проектные примеры

Фундаментальное правило: локальная транзакция не удерживается во время сетевого вызова.

Локальное следствие рядом с кодом:

```python
# Освобождаем локальную транзакцию до вызова внешнего клиента: намерение
# и наблюдаемый результат должны сохраняться отдельными атомарными шагами.
# См. architecture.md, раздел «Порядок сохранения».
```

Фундаментальное правило: Telegram entities используют UTF-16 code units.

Локальное следствие рядом с преобразованием:

```python
# Telegram entities используют UTF-16 code units, а индексы Python str —
# Unicode code points. Сохраняем преобразованные offsets один раз, чтобы retry
# повторно использовал то же представление.
# См. technical.md, раздел «Telegram: представление и разбиение».
```

Комментарий о баге библиотеки обязан содержать проверяемый issue или release note и диапазон затронутых версий. Без такого свидетельства агент не объявляет поведение «известным багом».

## Жизненный цикл

При изменении соседнего кода комментарий:

- сохраняется, если причина и локальное следствие остаются истинными;
- обновляется вместе с изменившейся реализацией;
- удаляется, если причина исчезла или правило теперь обеспечивается более подходящим проверяемым механизмом;
- добавляется только для нового неочевидного решения.

Устаревший комментарий является дефектом. Сохранять комментарий ради его истории запрещено.

## Проверка перед завершением изменения

1. Причина локальна и подтверждена нормативным источником, тестом или внешней ссылкой.
2. Комментарий не пересказывает синтаксис и не копирует системное правило.
3. Очевидная альтернатива действительно способна нарушить указанное ограничение.
4. Ссылка указывает на устойчивый документ, раздел, ADR или issue.
5. Соседние комментарии после изменения сохранены, обновлены либо удалены осознанно.
6. Отсутствие нового комментария допустимо, если код уже сообщает достаточно.
````

- [ ] **Step 2: Проверить удаление ошибочных и опасных правил старой версии**

Run:

```powershell
rg -n -i 'Python.*графем|никогда не удаляй|5–6|1–2|каждой функции|каждого класса|микро-промпт' `
  'D:\projects\feeds\doc\WHY_COMMENTS.md'
```

Expected: совпадений нет.

### Task 6: Подключить руководство к индексу документации

**Files:**

- Modify: `D:\projects\feeds\doc\README.md`

- [ ] **Step 1: Добавить документ в карту**

После строки технического дизайна добавить:

```markdown
| [Why-комментарии](WHY_COMMENTS.md) | Где проходит граница между системным инвариантом и локальным объяснением реализации? | действует |
```

- [ ] **Step 2: Уточнить порядок чтения**

Сохранить основной порядок `бизнес → архитектура → техника`, а руководство назвать необязательным для проектирования и обязательным при работе с кодом:

```markdown
Рекомендуемый порядок чтения дизайна: бизнес → архитектура → техника → статус решений ниже. Руководство по Why-комментариям применяется при создании, изменении и ревью кода и не является дополнительным источником системных инвариантов.
```

- [ ] **Step 3: Проверить единственность ссылок**

Run:

```powershell
$matches = rg -n 'WHY_COMMENTS\.md' 'D:\projects\feeds\doc\README.md'
if (($matches | Measure-Object).Count -ne 1) {
    throw 'WHY_COMMENTS.md must appear exactly once in the documentation entry point'
}
$matches
```

Expected: одна строка карты документов.

### Task 7: Провести сквозную проверку и очистить staging

**Files:**

- Verify: `C:\Users\jigal\.agents\skills\maintain-why-comments\SKILL.md`
- Verify: `D:\projects\feeds\AGENTS.md`
- Verify: `D:\projects\feeds\doc\WHY_COMMENTS.md`
- Verify: `D:\projects\feeds\doc\README.md`
- Delete: `D:\projects\feeds\.skill-build`

- [ ] **Step 1: Проверить разделение владельцев**

Run:

```powershell
rg -n -i 'Telegram|Telethon|feeds|CaptureBatch|DeliveryReceipt' `
  'C:\Users\jigal\.agents\skills\maintain-why-comments\SKILL.md'
rg -n 'maintain-why-comments|WHY_COMMENTS\.md' `
  'D:\projects\feeds\AGENTS.md' `
  'D:\projects\feeds\doc\README.md'
```

Expected: универсальный skill не содержит проектных терминов; проектные точки входа содержат ссылки.

- [ ] **Step 2: Проверить Markdown и placeholders**

Run:

```powershell
rg -n -i '\b(TODO|TBD|FIXME)\b' `
  'C:\Users\jigal\.agents\skills\maintain-why-comments\SKILL.md' `
  'D:\projects\feeds\AGENTS.md' `
  'D:\projects\feeds\doc\WHY_COMMENTS.md' `
  'D:\projects\feeds\doc\README.md'
```

Expected: совпадений нет.

- [ ] **Step 3: Удалить только проверенный staging**

Run:

```powershell
$staging = (Resolve-Path -LiteralPath 'D:\projects\feeds\.skill-build').Path
$workspace = (Resolve-Path -LiteralPath 'D:\projects\feeds').Path
if (-not $staging.StartsWith($workspace, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove path outside workspace: $staging"
}

$sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath 'D:\projects\feeds\.skill-build\maintain-why-comments\SKILL.md').Hash
$installedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\Users\jigal\.agents\skills\maintain-why-comments\SKILL.md').Hash
if ($sourceHash -ne $installedHash) {
    throw 'Refusing cleanup: installed skill does not match staging'
}

Remove-Item -LiteralPath $staging -Recurse
```

Expected: staging удалён; установленный skill сохранён.

- [ ] **Step 4: Финально перечитать установленные артефакты**

Run:

```powershell
Get-Content -Raw -LiteralPath 'C:\Users\jigal\.agents\skills\maintain-why-comments\SKILL.md'
Get-Content -Raw -LiteralPath 'D:\projects\feeds\AGENTS.md'
Get-Content -Raw -LiteralPath 'D:\projects\feeds\doc\WHY_COMMENTS.md'
Get-Content -Raw -LiteralPath 'D:\projects\feeds\doc\README.md'
```

Expected:

- skill нейтрален к агентам и проектам;
- `AGENTS.md` остаётся короткой точкой входа;
- проектное руководство содержит только границу и локальные примеры;
- индекс делает руководство обнаруживаемым;
- ни один файл не требует комментария к каждой функции или сохранения устаревшего комментария.
