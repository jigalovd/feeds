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


def test_batches_are_frozen_and_items_reject_mutable_input() -> None:
    batch = _capturing()

    with pytest.raises(ValidationError):
        batch.batch_id = "changed-batch"

    complete_data = _complete().model_dump()
    complete_data["items"] = [_item()]
    with pytest.raises(ValidationError):
        CompleteBatch.model_validate(complete_data)
