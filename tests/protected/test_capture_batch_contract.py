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
