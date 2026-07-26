from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone

from hypothesis import given, strategies as st
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
CAPTURED_AT = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


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
            semantic_text="Вышла новая версия продукта.",
            metadata=ContentMetadata(
                content_type="text",
                media_count=0,
            ),
        ),
        origin=OriginReference(
            username_snapshot="source_channel",
            title_snapshot="Source Channel",
            message_ids=message_ids,
            public_url=f"https://t.me/source_channel/{message_ids[0]}",
        ),
    )


def _capturing() -> CapturingBatch:
    return CapturingBatch(
        batch_id="batch-1",
        run_id="run-1",
        stream_id="stream-1",
        cursor_before=MessageCursor(message_id=10),
        cursor_after=MessageCursor(message_id=20),
        captured_at=CAPTURED_AT,
    )


def _complete(
    *,
    items: tuple[ContentItem, ...] = (_item(),),
) -> CompleteBatch:
    return CompleteBatch(
        batch_id="batch-1",
        run_id="run-1",
        stream_id="stream-1",
        cursor_before=MessageCursor(message_id=10),
        cursor_after=MessageCursor(message_id=20),
        captured_at=CAPTURED_AT,
        items=items,
    )


def _capturing_payload() -> dict[str, object]:
    return {
        "status": "capturing",
        "batch_id": "batch-1",
        "run_id": "run-1",
        "stream_id": "stream-1",
        "cursor_before": {
            "kind": "message",
            "message_id": 10,
        },
        "cursor_after": {
            "kind": "message",
            "message_id": 20,
        },
        "captured_at": CAPTURED_AT,
    }


def _complete_payload() -> dict[str, object]:
    return {
        "status": "complete",
        "batch_id": "batch-1",
        "run_id": "run-1",
        "stream_id": "stream-1",
        "cursor_before": {
            "kind": "message",
            "message_id": 10,
        },
        "cursor_after": {
            "kind": "message",
            "message_id": 20,
        },
        "captured_at": CAPTURED_AT,
        "items": (
            {
                "item_id": "item-1",
                "batch_id": "batch-1",
                "stream_id": "stream-1",
                "normalized_content": {
                    "mode": "semantic_text",
                    "semantic_text": "Вышла новая версия продукта.",
                    "metadata": {
                        "content_type": "text",
                        "media_count": 0,
                    },
                },
                "origin": {
                    "username_snapshot": "source_channel",
                    "title_snapshot": "Source Channel",
                    "message_ids": (11,),
                    "public_url": "https://t.me/source_channel/11",
                },
            },
        ),
    }


def test_capture_batch_parses_both_states_through_the_public_contract() -> None:
    adapter = TypeAdapter(CaptureBatch)

    capturing = adapter.validate_python(
        {
            "status": "capturing",
            "batch_id": "batch-1",
            "run_id": "run-1",
            "stream_id": "stream-1",
            "cursor_before": {
                "kind": "message",
                "message_id": 10,
            },
            "cursor_after": {
                "kind": "message",
                "message_id": 20,
            },
            "captured_at": CAPTURED_AT,
        },
    )
    complete = adapter.validate_python(
        {
            "status": "complete",
            "batch_id": "batch-1",
            "run_id": "run-1",
            "stream_id": "stream-1",
            "cursor_before": {
                "kind": "time",
                "after": datetime(2026, 7, 26, 12, 0, tzinfo=UTC),
            },
            "cursor_after": {
                "kind": "message",
                "message_id": 20,
            },
            "captured_at": CAPTURED_AT,
            "items": (_item().model_dump(),),
        },
    )

    assert isinstance(capturing, CapturingBatch)
    assert isinstance(complete, CompleteBatch)
    assert complete.items[0].item_id == "item-1"


@pytest.mark.parametrize(
    "payload_factory",
    (_capturing_payload, _complete_payload),
    ids=("capturing", "complete"),
)
@pytest.mark.parametrize("field", ("batch_id", "run_id", "stream_id"))
def test_capture_batch_rejects_empty_opaque_ids(
    payload_factory: Callable[[], dict[str, object]],
    field: str,
) -> None:
    payload = payload_factory()
    if payload["status"] == "complete":
        payload["items"] = ()
    payload[field] = ""

    with pytest.raises(ValidationError):
        TypeAdapter(CaptureBatch).validate_python(payload)


def test_complete_batch_rejects_payload_without_items() -> None:
    payload = _complete_payload()
    del payload["items"]

    with pytest.raises(ValidationError):
        TypeAdapter(CaptureBatch).validate_python(payload)


def test_message_cursor_rejects_negative_message_id() -> None:
    with pytest.raises(ValidationError):
        MessageCursor.model_validate(
            {
                "kind": "message",
                "message_id": -1,
            },
        )


@pytest.mark.parametrize(
    "payload_factory",
    (_capturing_payload, _complete_payload),
    ids=("capturing", "complete"),
)
def test_capture_batch_rejects_time_cursor_as_upper_boundary(
    payload_factory: Callable[[], dict[str, object]],
) -> None:
    payload = payload_factory()
    if payload["status"] == "complete":
        payload["items"] = ()
    payload["cursor_after"] = {
        "kind": "time",
        "after": datetime(2026, 7, 26, 12, 0, tzinfo=UTC),
    }

    with pytest.raises(ValidationError):
        TypeAdapter(CaptureBatch).validate_python(payload)


@pytest.mark.parametrize(
    ("validator", "payload"),
    (
        (
            MessageCursor.model_validate,
            {"kind": "message", "message_id": "10"},
        ),
        (
            TimeCursor.model_validate,
            {"kind": "time", "after": "2026-07-26T12:00:00Z"},
        ),
        (
            MessageCursor.model_validate,
            {"kind": "message", "message_id": 10, "unexpected": True},
        ),
        (
            TimeCursor.model_validate,
            {
                "kind": "time",
                "after": datetime(2026, 7, 26, 12, 0, tzinfo=UTC),
                "unexpected": True,
            },
        ),
    ),
    ids=(
        "message-string-id",
        "time-string-timestamp",
        "message-extra",
        "time-extra",
    ),
)
def test_cursor_values_reject_coercion_and_extra_fields(
    validator: Callable[[object], object],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        validator(payload)


@pytest.mark.parametrize(
    "payload_factory",
    (_capturing_payload, _complete_payload),
    ids=("capturing", "complete"),
)
@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("captured_at", "2026-07-27T12:00:00Z"),
        ("unexpected", True),
    ),
    ids=("string-timestamp", "extra-field"),
)
def test_batch_variants_reject_coercion_and_extra_fields(
    payload_factory: Callable[[], dict[str, object]],
    field: str,
    value: object,
) -> None:
    payload = payload_factory()
    payload[field] = value

    with pytest.raises(ValidationError):
        TypeAdapter(CaptureBatch).validate_python(payload)


@pytest.mark.parametrize(
    ("instance", "field", "replacement"),
    (
        (MessageCursor(message_id=10), "message_id", 11),
        (
            TimeCursor(after=datetime(2026, 7, 26, 12, 0, tzinfo=UTC)),
            "after",
            datetime(2026, 7, 26, 13, 0, tzinfo=UTC),
        ),
        (_capturing(), "run_id", "changed-run"),
        (_complete(), "run_id", "changed-run"),
    ),
    ids=("message", "time", "capturing", "complete"),
)
def test_public_capture_models_are_frozen(
    instance: object,
    field: str,
    replacement: object,
) -> None:
    with pytest.raises(ValidationError):
        setattr(instance, field, replacement)


@pytest.mark.parametrize(
    "item",
    (
        _item(batch_id="batch-2"),
        _item(stream_id="stream-2"),
    ),
)
def test_complete_batch_rejects_item_with_mismatched_membership(
    item: ContentItem,
) -> None:
    with pytest.raises(ValidationError):
        _complete(items=(item,))


def test_complete_batch_rejects_duplicate_item_id() -> None:
    items = (
        _item(item_id="duplicate-item", message_ids=(11,)),
        _item(item_id="duplicate-item", message_ids=(12,)),
    )

    with pytest.raises(ValidationError):
        _complete(items=items)


@pytest.mark.parametrize("message_ids", ((9, 11), (10, 11)))
def test_complete_batch_rejects_message_id_not_after_message_cursor_before(
    message_ids: tuple[int, ...],
) -> None:
    with pytest.raises(ValidationError):
        _complete(items=(_item(message_ids=message_ids),))


@pytest.mark.parametrize(
    "cursor_before",
    (
        MessageCursor(message_id=10),
        TimeCursor(after=datetime(2026, 7, 26, 12, 0, tzinfo=UTC)),
    ),
)
def test_complete_batch_rejects_message_id_after_upper_cursor(
    cursor_before: MessageCursor | TimeCursor,
) -> None:
    with pytest.raises(ValidationError):
        CompleteBatch(
            batch_id="batch-1",
            run_id="run-1",
            stream_id="stream-1",
            cursor_before=cursor_before,
            cursor_after=MessageCursor(message_id=20),
            captured_at=CAPTURED_AT,
            items=(_item(message_ids=(11, 21)),),
        )


def test_upper_cursor_is_inclusive() -> None:
    batch = _complete(items=(_item(message_ids=(20,)),))

    assert batch.items[0].origin.message_ids == (20,)


def test_complete_batch_rejects_items_when_upper_cursor_is_zero() -> None:
    with pytest.raises(ValidationError):
        CompleteBatch(
            batch_id="batch-1",
            run_id="run-1",
            stream_id="stream-1",
            cursor_before=TimeCursor(
                after=datetime(2026, 7, 26, 12, 0, tzinfo=UTC),
            ),
            cursor_after=MessageCursor(message_id=0),
            captured_at=CAPTURED_AT,
            items=(_item(message_ids=(1,)),),
        )


def test_complete_batch_rejects_overlapping_message_ids_between_items() -> None:
    items = (
        _item(item_id="item-1", message_ids=(11, 12)),
        _item(item_id="item-2", message_ids=(12, 13)),
    )

    with pytest.raises(ValidationError):
        _complete(items=items)


def test_complete_batch_preserves_capture_order() -> None:
    items = (
        _item(item_id="item-z", message_ids=(19,)),
        _item(item_id="item-a", message_ids=(11,)),
        _item(item_id="item-m", message_ids=(15,)),
    )

    batch = _complete(items=items)

    assert batch.items == items


def test_empty_bootstrap_batch_normalizes_timestamps_to_utc() -> None:
    plus_two = timezone(timedelta(hours=2))

    batch = CompleteBatch(
        batch_id="batch-1",
        run_id="run-1",
        stream_id="stream-1",
        cursor_before=TimeCursor(
            after=datetime(2026, 7, 27, 11, 0, tzinfo=plus_two),
        ),
        cursor_after=MessageCursor(message_id=0),
        captured_at=datetime(2026, 7, 27, 12, 0, tzinfo=plus_two),
        items=(),
    )

    assert batch.cursor_before.after == datetime(
        2026,
        7,
        27,
        9,
        0,
        tzinfo=UTC,
    )
    assert batch.cursor_before.after.tzinfo is UTC
    assert batch.captured_at == datetime(2026, 7, 27, 10, 0, tzinfo=UTC)
    assert batch.captured_at.tzinfo is UTC
    assert batch.cursor_after == MessageCursor(message_id=0)
    assert batch.items == ()


@pytest.mark.parametrize("message_id", (0, 10))
def test_complete_batch_accepts_equal_message_cursor_boundaries(
    message_id: int,
) -> None:
    batch = CompleteBatch(
        batch_id="batch-1",
        run_id="run-1",
        stream_id="stream-1",
        cursor_before=MessageCursor(message_id=message_id),
        cursor_after=MessageCursor(message_id=message_id),
        captured_at=CAPTURED_AT,
        items=(),
    )

    assert batch.cursor_before == MessageCursor(message_id=message_id)
    assert batch.cursor_after == MessageCursor(message_id=message_id)
    assert batch.items == ()


@given(
    lower=st.integers(min_value=1),
    upper_source=st.integers(min_value=0),
)
def test_capture_batch_rejects_every_reversed_message_cursor_range(
    lower: int,
    upper_source: int,
) -> None:
    upper = upper_source % lower

    with pytest.raises(ValidationError):
        CapturingBatch(
            batch_id="batch-1",
            run_id="run-1",
            stream_id="stream-1",
            cursor_before=MessageCursor(message_id=lower),
            cursor_after=MessageCursor(message_id=upper),
            captured_at=CAPTURED_AT,
        )


def test_capture_batch_rejects_invalid_temporal_boundaries() -> None:
    with pytest.raises(ValidationError):
        CapturingBatch(
            batch_id="batch-1",
            run_id="run-1",
            stream_id="stream-1",
            cursor_before=MessageCursor(message_id=10),
            cursor_after=MessageCursor(message_id=20),
            captured_at=datetime(2026, 7, 27, 12, 0),
        )

    with pytest.raises(ValidationError):
        TimeCursor(after=datetime(2026, 7, 27, 11, 0))

    for after in (CAPTURED_AT, CAPTURED_AT + timedelta(microseconds=1)):
        with pytest.raises(ValidationError):
            CapturingBatch(
                batch_id="batch-1",
                run_id="run-1",
                stream_id="stream-1",
                cursor_before=TimeCursor(after=after),
                cursor_after=MessageCursor(message_id=20),
                captured_at=CAPTURED_AT,
            )


def test_capture_batch_rejects_unknown_discriminators() -> None:
    adapter = TypeAdapter(CaptureBatch)

    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "status": "unknown",
                "batch_id": "batch-1",
                "run_id": "run-1",
                "stream_id": "stream-1",
                "cursor_before": {
                    "kind": "message",
                    "message_id": 10,
                },
                "cursor_after": {
                    "kind": "message",
                    "message_id": 20,
                },
                "captured_at": CAPTURED_AT,
            },
        )

    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "status": "capturing",
                "batch_id": "batch-1",
                "run_id": "run-1",
                "stream_id": "stream-1",
                "cursor_before": {
                    "kind": "unknown",
                    "message_id": 10,
                },
                "cursor_after": {
                    "kind": "message",
                    "message_id": 20,
                },
                "captured_at": CAPTURED_AT,
            },
        )


def test_capture_batch_rejects_payload_without_status() -> None:
    adapter = TypeAdapter(CaptureBatch)

    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "batch_id": "batch-1",
                "run_id": "run-1",
                "stream_id": "stream-1",
                "cursor_before": {
                    "kind": "message",
                    "message_id": 10,
                },
                "cursor_after": {
                    "kind": "message",
                    "message_id": 20,
                },
                "captured_at": CAPTURED_AT,
            },
        )


def test_capture_batch_rejects_cursor_before_without_kind() -> None:
    adapter = TypeAdapter(CaptureBatch)

    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "status": "capturing",
                "batch_id": "batch-1",
                "run_id": "run-1",
                "stream_id": "stream-1",
                "cursor_before": {
                    "message_id": 10,
                },
                "cursor_after": {
                    "kind": "message",
                    "message_id": 20,
                },
                "captured_at": CAPTURED_AT,
            },
        )


def test_capturing_batch_exposes_only_the_normative_fields() -> None:
    assert tuple(CapturingBatch.model_fields) == (
        "status",
        "batch_id",
        "run_id",
        "stream_id",
        "cursor_before",
        "cursor_after",
        "captured_at",
    )


def test_complete_batch_exposes_only_the_normative_fields() -> None:
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


def test_capturing_batch_rejects_items() -> None:
    with pytest.raises(ValidationError):
        CapturingBatch(
            batch_id="batch-1",
            run_id="run-1",
            stream_id="stream-1",
            cursor_before=TimeCursor(
                after=datetime(2026, 7, 26, 12, 0, tzinfo=UTC),
            ),
            cursor_after=MessageCursor(message_id=20),
            captured_at=CAPTURED_AT,
            items=(),
        )


def test_complete_batch_rejects_mutable_items_input() -> None:
    complete_data = _complete().model_dump()
    complete_data["items"] = [_item()]
    with pytest.raises(ValidationError):
        CompleteBatch.model_validate(complete_data)
