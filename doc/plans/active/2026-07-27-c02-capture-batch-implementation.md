# C02 CaptureBatch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development`
> or an equivalent task-by-task TDD executor. Do not merge or weaken protected
> oracle while implementing this plan.

**Goal:** реализовать публичный неизменяемый `CaptureBatch`, который типами и
валидацией отличает незавершённый capture от complete-входа следующей фазы.

**Architecture:** новые cursor value objects и оба варианта batch живут рядом с
`ContentItem` в существующей публичной границе `feeds.contracts`.
`CaptureBatch` остаётся закрытым discriminated union Pydantic-моделей.
Persistence, Telegram adapter и переход состояния в C02 не создаются.

**Tech Stack:** Python 3.14, Pydantic 2.x, pytest 9.x, Hypothesis 6.x, uv.

---

## Контракт среза

```text
Slice: C02 — публичный CaptureBatch
Нормативный владелец: doc/architecture/contracts.md; doc/architecture/state.md
Требование: представить capturing и complete batch вместе с зафиксированными cursor-границами
Наблюдаемый результат: потребитель создаёт и валидирует CaptureBatch через feeds.contracts
Запрещённый результат: capturing с items; complete с чужими или вне диапазона ContentItem
Источник oracle: contracts.md#минимальные-публичные-api; state.md#capturebatch; technical/telegram.md#telegram-фиксация-batch
Protected tests: tests/protected/test_capture_batch_contract.py
Дополнительные проверки: полный pytest; Hypothesis для cursor-границ; docs checks; clean-context verify
Documentation impact: статус реализации и активный план; нормативное поведение не меняется
```

## Файлы и ответственность

- `src/feeds/contracts.py` — единственная публичная граница DTO; добавить
  `MessageCursor`, `TimeCursor`, `CapturingBatch`, `CompleteBatch` и
  `CaptureBatch`.
- `tests/protected/test_capture_batch_contract.py` — protected oracle C02 без
  чтения production-реализации.
- `README.md`, `AGENTS.md`, `doc/README.md`,
  `doc/engineering/development-workflow.md` — только фактический статус
  реализации после зелёного кода.
- `doc/plans/active/2026-07-26-wave-1-fake-capture.md` — отметить C02
  завершённым только после clean-context `PASS`.
- Этот план после завершения переместить в `doc/plans/archive/` и обновить
  `doc/plans/README.md`.

### Task 1: Публичные варианты и закрытые discriminators

**Files:**
- Modify: `src/feeds/contracts.py`
- Create: `tests/protected/test_capture_batch_contract.py`

- [ ] **Step 1: создать protected-тест с публичными happy paths и запрещённой формой**

```python
from datetime import UTC, datetime

from pydantic import TypeAdapter, ValidationError
import pytest

from feeds.contracts import (
    CaptureBatch,
    CapturingBatch,
    CompleteBatch,
    ContentItem,
    ContentMetadata,
    MessageCursor,
    OriginReference,
    SemanticTextContent,
    TimeCursor,
)


pytestmark = pytest.mark.protected
CAPTURED_AT = datetime(2026, 7, 27, 12, tzinfo=UTC)


def _item(
    *,
    item_id: str = "item-1",
    batch_id: str = "batch-1",
    stream_id: str = "stream-1",
    message_ids: tuple[int, ...] = (11,),
) -> ContentItem:
    return ContentItem(
        item_id=item_id,
        batch_id=batch_id,
        stream_id=stream_id,
        normalized_content=SemanticTextContent(
            semantic_text=f"Item {item_id}",
            metadata=ContentMetadata(content_type="text", media_count=0),
        ),
        origin=OriginReference(
            username_snapshot="source",
            title_snapshot="Source",
            message_ids=message_ids,
            public_url=f"https://t.me/source/{message_ids[0]}",
        ),
    )


def _capturing(**updates: object) -> CapturingBatch:
    values: dict[str, object] = {
        "batch_id": "batch-1",
        "run_id": "run-1",
        "stream_id": "stream-1",
        "cursor_before": MessageCursor(message_id=10),
        "cursor_after": MessageCursor(message_id=20),
        "captured_at": CAPTURED_AT,
    }
    values.update(updates)
    return CapturingBatch(**values)


def _complete(**updates: object) -> CompleteBatch:
    values: dict[str, object] = {
        "batch_id": "batch-1",
        "run_id": "run-1",
        "stream_id": "stream-1",
        "cursor_before": MessageCursor(message_id=10),
        "cursor_after": MessageCursor(message_id=20),
        "captured_at": CAPTURED_AT,
        "items": (_item(),),
    }
    values.update(updates)
    return CompleteBatch(**values)


def test_public_union_parses_both_batch_states() -> None:
    adapter = TypeAdapter(CaptureBatch)

    capturing = adapter.validate_python(_capturing().model_dump())
    complete = adapter.validate_python(_complete().model_dump())

    assert isinstance(capturing, CapturingBatch)
    assert isinstance(complete, CompleteBatch)
    assert complete.items[0].item_id == "item-1"


def test_capturing_batch_has_no_items_field() -> None:
    assert tuple(CapturingBatch.model_fields) == (
        "status",
        "batch_id",
        "run_id",
        "stream_id",
        "cursor_before",
        "cursor_after",
        "captured_at",
    )

    with pytest.raises(ValidationError):
        CapturingBatch(
            **_capturing().model_dump(),
            items=(),
        )


def test_complete_batch_exposes_only_normative_fields() -> None:
    assert tuple(CompleteBatch.model_fields) == (
        "status",
        "batch_id",
        "run_id",
        "stream_id",
        "cursor_before",
        "cursor_after",
        "captured_at",
        "items",
    )


def test_batch_values_and_items_are_immutable() -> None:
    batch = _complete()

    with pytest.raises(ValidationError):
        batch.run_id = "changed"

    with pytest.raises(ValidationError):
        CompleteBatch(
            **{
                **batch.model_dump(exclude={"items"}),
                "items": [_item()],
            },
        )
```

- [ ] **Step 2: выполнить исходный RED**

Run:

```console
uv run pytest tests/protected/test_capture_batch_contract.py -q
```

Expected: collection `ERROR` с `ImportError` для отсутствующих публичных типов
batch.

- [ ] **Step 3: добавить минимальные модели без cross-field validators**

В `src/feeds/contracts.py` добавить импорт:

```python
from datetime import datetime
```

В список импортов Pydantic добавить `AwareDatetime`, затем после `ContentItem`
добавить:

```python
class MessageCursor(ContractModel):
    kind: Literal["message"] = "message"
    message_id: NonNegativeInt


class TimeCursor(ContractModel):
    kind: Literal["time"] = "time"
    after: AwareDatetime


CursorBefore = Annotated[
    MessageCursor | TimeCursor,
    Field(discriminator="kind"),
]


class _BatchContract(ContractModel):
    status: str
    batch_id: OpaqueId
    run_id: OpaqueId
    stream_id: OpaqueId
    cursor_before: CursorBefore
    cursor_after: MessageCursor
    captured_at: AwareDatetime


class CapturingBatch(_BatchContract):
    status: Literal["capturing"] = "capturing"


class CompleteBatch(_BatchContract):
    status: Literal["complete"] = "complete"
    items: tuple[ContentItem, ...]


CaptureBatch = Annotated[
    CapturingBatch | CompleteBatch,
    Field(discriminator="status"),
]
```

- [ ] **Step 4: подтвердить GREEN базовой публичной формы**

Run:

```console
uv run pytest tests/protected/test_capture_batch_contract.py -q
```

Expected: все тесты Task 1 проходят.

- [ ] **Step 5: зафиксировать первый TDD-инкремент**

```console
git add src/feeds/contracts.py tests/protected/test_capture_batch_contract.py
git commit -m "Add CaptureBatch public variants"
```

### Task 2: UTC и cursor-границы

**Files:**
- Modify: `src/feeds/contracts.py`
- Modify: `tests/protected/test_capture_batch_contract.py`

- [ ] **Step 1: добавить failing-примеры времени и диапазонов**

```python
from datetime import timedelta, timezone

from hypothesis import given
from hypothesis import strategies as st


def test_normalizes_aware_timestamps_to_utc() -> None:
    plus_two = timezone(timedelta(hours=2))
    batch = _capturing(
        cursor_before=TimeCursor(
            after=datetime(2026, 7, 27, 8, tzinfo=plus_two),
        ),
        captured_at=datetime(2026, 7, 27, 14, tzinfo=plus_two),
    )

    assert batch.cursor_before.after == datetime(2026, 7, 27, 6, tzinfo=UTC)
    assert batch.captured_at == datetime(2026, 7, 27, 12, tzinfo=UTC)
    assert batch.cursor_before.after.tzinfo is UTC
    assert batch.captured_at.tzinfo is UTC


@pytest.mark.parametrize(
    "updates",
    (
        {"captured_at": datetime(2026, 7, 27, 12)},
        {
            "cursor_before": TimeCursor(
                after=datetime(2026, 7, 27, 12, tzinfo=UTC),
            ),
        },
        {
            "cursor_before": MessageCursor(message_id=20),
            "cursor_after": MessageCursor(message_id=19),
        },
    ),
)
def test_rejects_invalid_time_or_reversed_boundaries(
    updates: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _capturing(**updates)


def test_rejects_naive_bootstrap_boundary() -> None:
    with pytest.raises(ValidationError):
        TimeCursor(after=datetime(2026, 7, 27, 8))


def test_zero_upper_cursor_represents_an_empty_history() -> None:
    batch = _complete(
        cursor_before=TimeCursor(
            after=datetime(2026, 7, 27, 11, tzinfo=UTC),
        ),
        cursor_after=MessageCursor(message_id=0),
        items=(),
    )

    assert batch.cursor_after.message_id == 0
    assert batch.items == ()


@given(
    lower=st.integers(min_value=1, max_value=2_000_000_000),
    distance=st.integers(min_value=1, max_value=100_000),
)
def test_rejects_every_reversed_message_range(
    lower: int,
    distance: int,
) -> None:
    with pytest.raises(ValidationError):
        _capturing(
            cursor_before=MessageCursor(message_id=lower),
            cursor_after=MessageCursor(message_id=lower - min(lower, distance)),
        )
```

- [ ] **Step 2: подтвердить RED на отсутствующей нормализации и проверках**

Run:

```console
uv run pytest tests/protected/test_capture_batch_contract.py -q
```

Expected: FAIL у UTC-нормализации, временного порядка или обратного числового
диапазона; naive datetime уже может отклоняться типом Pydantic.

- [ ] **Step 3: реализовать UTC и общий validator batch**

Изменить импорт времени:

```python
from datetime import UTC, datetime
```

Добавить в `TimeCursor`:

```python
    @field_validator("after")
    @classmethod
    def normalize_after_to_utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)
```

Добавить в `_BatchContract`:

```python
    @field_validator("captured_at")
    @classmethod
    def normalize_captured_at_to_utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_valid_boundaries(self) -> Self:
        if isinstance(self.cursor_before, TimeCursor):
            if self.cursor_before.after >= self.captured_at:
                raise ValueError("bootstrap boundary must precede capture")
        elif (
            self.cursor_after.message_id
            < self.cursor_before.message_id
        ):
            raise ValueError("upper cursor must not precede lower cursor")
        return self
```

- [ ] **Step 4: подтвердить GREEN и отсутствие регрессии C01**

Run:

```console
uv run pytest tests/protected/test_capture_batch_contract.py tests/protected/test_content_item_contract.py -q
```

Expected: оба protected-файла проходят.

- [ ] **Step 5: зафиксировать cursor-инварианты**

```console
git add src/feeds/contracts.py tests/protected/test_capture_batch_contract.py
git commit -m "Validate CaptureBatch cursor boundaries"
```

### Task 3: Принадлежность complete-элементов

**Files:**
- Modify: `src/feeds/contracts.py`
- Modify: `tests/protected/test_capture_batch_contract.py`

- [ ] **Step 1: добавить контрпримеры membership и диапазона**

```python
@pytest.mark.parametrize(
    "items",
    (
        (_item(batch_id="other-batch"),),
        (_item(stream_id="other-stream"),),
        (
            _item(item_id="same", message_ids=(11,)),
            _item(item_id="same", message_ids=(12,)),
        ),
        (_item(message_ids=(10,)),),
        (_item(message_ids=(21,)),),
        (
            _item(item_id="first", message_ids=(11, 12)),
            _item(item_id="second", message_ids=(12, 13)),
        ),
    ),
)
def test_rejects_items_outside_complete_batch_contract(
    items: tuple[ContentItem, ...],
) -> None:
    with pytest.raises(ValidationError):
        _complete(items=items)


def test_zero_upper_cursor_rejects_nonempty_batch() -> None:
    with pytest.raises(ValidationError):
        _complete(
            cursor_before=TimeCursor(
                after=datetime(2026, 7, 27, 11, tzinfo=UTC),
            ),
            cursor_after=MessageCursor(message_id=0),
            items=(_item(message_ids=(1,)),),
        )


def test_upper_cursor_is_inclusive() -> None:
    item = _item(message_ids=(20,))

    assert _complete(items=(item,)).items == (item,)


def test_complete_batch_preserves_capture_order() -> None:
    items = (
        _item(item_id="later", message_ids=(19,)),
        _item(item_id="earlier", message_ids=(11,)),
    )

    batch = _complete(items=items)

    assert tuple(item.item_id for item in batch.items) == (
        "later",
        "earlier",
    )


def test_empty_complete_batch_is_valid() -> None:
    assert _complete(items=()).items == ()
```

- [ ] **Step 2: подтвердить RED на неконсистентных элементах**

Run:

```console
uv run pytest tests/protected/test_capture_batch_contract.py -q
```

Expected: контрпримеры с чужой принадлежностью, повторениями и выходом за
границы ошибочно принимаются до validator.

- [ ] **Step 3: реализовать единый validator `CompleteBatch`**

Добавить в `CompleteBatch`:

```python
    @model_validator(mode="after")
    def require_consistent_items(self) -> Self:
        if self.cursor_after.message_id == 0 and self.items:
            raise ValueError("zero upper cursor requires an empty batch")

        item_ids: set[str] = set()
        message_ids: set[int] = set()
        lower_message_id = (
            self.cursor_before.message_id
            if isinstance(self.cursor_before, MessageCursor)
            else None
        )

        for item in self.items:
            if item.batch_id != self.batch_id:
                raise ValueError("item belongs to another batch")
            if item.stream_id != self.stream_id:
                raise ValueError("item belongs to another stream")
            if item.item_id in item_ids:
                raise ValueError("item IDs must be unique within a batch")
            item_ids.add(item.item_id)

            for message_id in item.origin.message_ids:
                if (
                    lower_message_id is not None
                    and message_id <= lower_message_id
                ):
                    raise ValueError("item is not after the lower cursor")
                if message_id > self.cursor_after.message_id:
                    raise ValueError("item exceeds the upper cursor")
                if message_id in message_ids:
                    raise ValueError("item message IDs must not overlap")
                message_ids.add(message_id)

        return self
```

- [ ] **Step 4: подтвердить GREEN полного protected oracle C02**

Run:

```console
uv run pytest tests/protected/test_capture_batch_contract.py -q
```

Expected: все happy paths, properties и контрпримеры проходят.

- [ ] **Step 5: проверить силу oracle целевой мутацией**

Временно заменить проверку верхней границы
`message_id > self.cursor_after.message_id` на
`message_id >= self.cursor_after.message_id`, запустить:

```console
uv run pytest tests/protected/test_capture_batch_contract.py -q
```

Expected: хотя бы happy path с элементом на включительной верхней границе
должен упасть. После доказанного FAIL вернуть нормативное условие `>` и
повторить тест до GREEN.

- [ ] **Step 6: зафиксировать membership-инварианты**

```console
git add src/feeds/contracts.py tests/protected/test_capture_batch_contract.py
git commit -m "Enforce complete batch membership"
```

### Task 4: Статус документации и полный verify

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `doc/README.md`
- Modify: `doc/engineering/development-workflow.md`
- Modify: `doc/plans/active/2026-07-26-wave-1-fake-capture.md`
- Move: `doc/plans/active/2026-07-27-c02-capture-batch-implementation.md`
  to `doc/plans/archive/2026-07-27-c02-capture-batch-implementation.md`
- Modify: `doc/plans/README.md`

- [ ] **Step 1: выполнить полный implementation-профиль до изменения статусов**

```console
uv sync --locked --group dev
uv lock --check
uv run pytest
uv run pytest --cov=feeds --cov-branch --cov-report=term-missing
```

Expected: все тесты проходят; `src/feeds/contracts.py` имеет 100% statement и
branch coverage либо каждый непокрытый участок получает отдельный
обоснованный тест до продолжения.

- [ ] **Step 2: проверить Why-комментарии и архитектурную границу**

Запустить:

```console
rg -n "from feeds\\.(monitoring|synthesis|delivery|operations)|import feeds\\.(monitoring|synthesis|delivery|operations)" src tests
rg -n '#|"""' src/feeds/contracts.py
```

Expected: импортов предметных модулей нет. Стратегические правила не
дублируются комментариями; локальный Why-комментарий добавляется только если
без него остаётся реальная refactor-ловушка.

- [ ] **Step 3: синхронизировать только фактический статус**

В четырёх статусных документах заменить формулировку «реализован только
`ContentItem`» на «реализованы публичные контракты `ContentItem` и
`CaptureBatch`». В wave-плане отметить C02 `[x]`. Нормативные правила
`contracts.md`, `state.md` и `telegram.md` не менять.

Переместить этот implementation-план в архив и заменить его ссылку в
`doc/plans/README.md` из раздела «Активные» в «Архив».

- [ ] **Step 4: выполнить документационные проверки**

```console
python tools/check_docs.py
python tools/test_check_docs.py
git diff --check
```

Expected: `DOCS_CHECK=PASS`, `CHECK_DOCS_TESTS=PASS`, у `git diff --check`
нет вывода.

- [ ] **Step 5: получить независимый clean-context verdict**

Verifier получает только:

```text
Slice: C02 — публичный CaptureBatch
Oracle sources:
- doc/architecture/contracts.md#минимальные-публичные-api
- doc/architecture/state.md#capturebatch
- doc/technical/telegram.md#telegram-фиксация-batch
Implementation:
- src/feeds/contracts.py
Protected tests:
- tests/protected/test_capture_batch_contract.py
Required checks:
- uv sync --locked --group dev
- uv lock --check
- uv run pytest
- python tools/check_docs.py
- python tools/test_check_docs.py
```

Verifier обязан атаковать discriminator, strict/frozen-поведение, naive
datetime, UTC-нормализацию, `0` sentinel, обратные границы, чужие
batch/stream, повторные item/message IDs, обе границы диапазона и сохранение
порядка. Требуемый итоговый формат:

```text
Findings: none
Verdict: PASS
```

Любой новый commit после `PASS` требует нового clean-context verify.

- [ ] **Step 6: зафиксировать завершённый срез**

```console
git add AGENTS.md README.md doc src tests
git commit -m "Complete the CaptureBatch contract"
```

- [ ] **Step 7: открыть draft PR без merge**

```console
git push -u origin codex/c02-capture-batch
```

PR содержит один публичный результат C02, фактические команды и
clean-context verdict. Merge выполняется только после отдельного принятия
пользователем.
